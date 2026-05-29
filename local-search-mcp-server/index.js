#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { spawn } from "child_process";
import iconv from "iconv-lite";
import { readFileSync, existsSync, appendFileSync, writeFileSync } from "fs";
import { resolve, dirname } from "path";
import { fileURLToPath } from "url";
import { homedir } from "os";

const __dirname = dirname(fileURLToPath(import.meta.url));
const LOG_FILE = resolve(__dirname, "debug.log");

writeFileSync(LOG_FILE, `=== local-search-mcp-server 启动 ${new Date().toISOString()} ===\n`);

function log(msg) {
  const line = `[${new Date().toISOString()}] ${msg}\n`;
  try { appendFileSync(LOG_FILE, line); } catch {}
}

// 读取配置文件：优先 ~/.copilot/agents/（生产），回退 __dirname/../agents/（开发）
const prodConfig = resolve(homedir(), ".copilot", "agents", "档案员.config.json");
const devConfig = resolve(__dirname, "..", "agents", "档案员.config.json");
const configPath = existsSync(prodConfig) ? prodConfig : devConfig;
let config = { esPath: "es.exe", kbRoot: resolve(homedir(), "Documents"), excludePaths: ["ByCatalog", "ByDay", "写易"] };

if (existsSync(configPath)) {
  try {
    const raw = readFileSync(configPath, "utf-8");
    const userConfig = JSON.parse(raw);
    if (userConfig.esPath) config.esPath = userConfig.esPath;
    if (userConfig.everythingPath) config.everythingPath = userConfig.everythingPath;
    if (userConfig.excludePaths) config.excludePaths = userConfig.excludePaths;
    if (userConfig.rhetoricDbPath) config.rhetoricDbPath = userConfig.rhetoricDbPath;
    if (userConfig.kbRoot) {
      const kb = userConfig.kbRoot;
      config.kbRoot = kb.startsWith("~/") ? resolve(homedir(), kb.slice(2)) : kb;
    }
  } catch {
    // 配置文件损坏，使用默认值
  }
}

const { esPath, kbRoot } = config;
const rhetoricDb = config.rhetoricDbPath || resolve(__dirname, "好词好句.jsonl");
log(`修辞句子库: ${rhetoricDb}`);
const everythingPath = config.everythingPath || "C:\\Program Files\\Everything\\Everything.exe";
log(`配置: esPath=${esPath}, kbRoot=${kbRoot}, everythingPath=${everythingPath}, excludePaths=[${(config.excludePaths || []).join(", ")}]  (来源: ${configPath})`);

// ——— Everything 进程保活 ———
// es.exe 依赖 Everything 托盘程序（非 Windows Service）提供 IPC 窗口。
// Everything.exe -startup 启动后进程不退出，必须用 detached 模式 fire-and-forget。
// 策略：先启动托盘 → 冒烟测试 es.exe 验证 IPC 就绪。结果缓存。

// 启动进程后不等待退出，立即 resolve
function spawnDetached(exe, args, label) {
  return new Promise((resolve) => {
    log(`[执行|detach] ${label || ""}  ${exe} ${args.join(" ")}`);
    const child = spawn(exe, args, {
      windowsHide: true,
      detached: true,
      stdio: "ignore",
    });
    child.on("error", (err) => {
      log(`[错误|detach] spawn 失败: ${err.message}`);
      resolve(false);
    });
    // unref 后 child 退出与否不影响主进程，不等待 close 事件
    child.unref();
    log(`[执行|detach] 已发射，pid=${child.pid}`);
    resolve(true);
  });
}

let everythingEnsured = false;
let everythingReady = false;

async function ensureEverything() {
  if (everythingEnsured) return everythingReady;
  everythingEnsured = true;

  // 1) 尝试启动 Everything 托盘程序（detached，fire-and-forget）
  log("尝试启动 Everything 托盘程序...");
  const tryPaths = [...new Set([
    everythingPath,
    "Everything.exe",
    "C:\\Program Files\\Everything\\Everything.exe",
    "C:\\Program Files (x86)\\Everything\\Everything.exe",
  ])].filter(Boolean);

  let launched = false;
  for (const ep of tryPaths) {
    const ok = await spawnDetached(ep, ["-startup"], "Everything启动");
    if (ok) {
      log(`Everything.exe 已发射: ${ep}`);
      launched = true;
      break;
    }
  }
  if (!launched) {
    log("⚠ Everything.exe 启动失败");
    return false;
  }

  // 2) 等待索引就绪
  await new Promise(r => setTimeout(r, 3000));

  // 3) 冒烟测试：es.exe 快速搜索验证 IPC 通畅
  const { text, exitCode } = await spawnRun(esPath, ["ext:md", "-n", "1", "-path", kbRoot], "es冒烟", "gbk");
  if (exitCode === 0) {
    log("es.exe 冒烟测试通过，IPC 通畅");
    everythingReady = true;
    return true;
  }

  // exitCode 8 = IPC window not found
  log(`es.exe 冒烟测试失败 exitCode=${exitCode} → ${text}`);
  return false;
}

// ——— spawn 执行引擎 ———
// 不经过 shell，直接启动进程。Windows 原生程序输出 GBK，跨平台程序(rg)输出 UTF-8

const MAX_BUF = 10 * 1024 * 1024;

function spawnRun(exe, args, label, decodeEnc = "gbk") {
  return new Promise((resolve) => {
    log(`[执行] ${label || ""}  ${exe} ${args.join(" ")}`);
    const child = spawn(exe, args, {
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    });

    const chunks = { stdout: [], stderr: [], outLen: 0, errLen: 0 };
    let overLimit = false;

    child.stdout.on("data", (buf) => {
      chunks.outLen += buf.length;
      if (chunks.outLen > MAX_BUF) { overLimit = true; child.kill(); }
      else chunks.stdout.push(buf);
    });
    child.stderr.on("data", (buf) => {
      chunks.errLen += buf.length;
      if (chunks.errLen > MAX_BUF) { overLimit = true; child.kill(); }
      else chunks.stderr.push(buf);
    });

    child.on("close", (code) => {
      if (overLimit) {
        log(`[结果] 输出超过限制 ${MAX_BUF} 字节，已截断`);
        resolve({ text: "(输出过大已截断)", exitCode: code || 0 });
        return;
      }
      const stdout = Buffer.concat(chunks.stdout);
      const stderr = Buffer.concat(chunks.stderr);
      const out = stdout.length ? iconv.decode(stdout, decodeEnc).trim() : "";
      const errOut = stderr.length ? iconv.decode(stderr, decodeEnc).trim() : "";
      const exitCode = code !== 0 ? (code || 1) : 0;
      const text = out || errOut;
      log(`[结果] exitCode=${exitCode}  stdout_len=${stdout.length}  stderr_len=${stderr.length}`);
      if (text) log(`[输出] (前500) ${text.substring(0, 500)}`);
      else log(`[输出] (空)`);
      resolve({ text, exitCode });
    });

    child.on("error", (err) => {
      log(`[错误] spawn 失败: ${err.message}`);
      resolve({ text: err.message, exitCode: 127 });
    });
  });
}

// 判断文本是否来自"命令未找到"错误（exec 报错文本 或 spawn ENOENT）
function isCommandNotFound(text, exitCode) {
  return exitCode === 127 || /not recognized|not found|command not found|ENOENT/i.test(text);
}

// 去重：1) 排除 ByCatalog/ByDay 路径  2) 路径去掉数字后相同的视为重复
function deduplicate(rawOutput) {
  if (!rawOutput || !rawOutput.trim()) {
    log(`[去重] 输入为空，返回 []`);
    return [];
  }
  const lines = rawOutput.split(/\r?\n/).map(s => s.trim()).filter(Boolean);
  log(`[去重] 输入 ${lines.length} 行`);
  const excludePattern = config.excludePaths.length > 0 ? new RegExp(config.excludePaths.map(p => `[\\\\/]${p.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}[\\\\/]`).join("|")) : null;
  const filtered = excludePattern ? lines.filter(p => !excludePattern.test(p)) : lines;
  const dropped1 = lines.length - filtered.length;
  if (dropped1 > 0) log(`[去重] 路径排除(${config.excludePaths.join(", ")})过滤掉 ${dropped1} 条`);
  const seen = new Map();
  for (const p of filtered) {
    const fingerprint = p.replace(/\d+/g, '');
    if (!seen.has(fingerprint)) {
      seen.set(fingerprint, p);
    }
  }
  const dropped2 = filtered.length - seen.size;
  if (dropped2 > 0) log(`[去重] 数字指纹去重掉 ${dropped2} 条`);
  const result = Array.from(seen.values());
  log(`[去重] 最终 ${result.length} 条`);
  return result;
}

const server = new McpServer({
  name: "local-search-mcp-server",
  version: "1.0.0",
});

// ——— 修辞句子库 ———
// jsonl 格式：每行 {"content": "句子", "tags": ["标签1", "标签2"]}
// 路径由 config.rhetoricDbPath 指定，默认 __dirname/句子库.jsonl

let rhetoricCache = null;

function loadRhetoricDb() {
  if (rhetoricCache) return rhetoricCache;
  const dbPath = config.rhetoricDbPath || resolve(__dirname, "好词好句.jsonl");
  if (!existsSync(dbPath)) {
    log(`句子库不存在: ${dbPath}`);
    rhetoricCache = [];
    return rhetoricCache;
  }
  const raw = readFileSync(dbPath, "utf-8");
  const lines = raw.split(/\r?\n/).filter(Boolean);
  rhetoricCache = [];
  for (const line of lines) {
    try {
      const obj = JSON.parse(line);
      if (obj.content) rhetoricCache.push({ text: obj.content, tags: obj.tags });
    } catch {}
  }
  log(`句子库加载: ${rhetoricCache.length} 条`);
  return rhetoricCache;
}

// ── 工具 1: 文件名搜索 (es.exe, GBK 输出) ──
server.tool(
  "search_files",
  "在知识库中按文件名搜索 Markdown 文档（调用 es.exe，仅搜索 *.md 文件）",
  {
    query: z.string().min(1).describe("文件名搜索关键词，多个词用空格分隔"),
  },
  async ({ query }) => {
    log(`===== search_files  query="${query}" =====`);
    await ensureEverything();
    const args = [...query.split(/\s+/).filter(Boolean), "ext:md", "-path", kbRoot];
    const { text, exitCode } = await spawnRun(esPath, args, "search_files", "gbk");
    if (exitCode !== 0 && !text) {
      return { content: [{ type: "text", text: `es.exe 执行失败（exit code: ${exitCode}）。请确认 Everything 已安装且 es.exe 在 PATH 中。` }] };
    }
    if (!text) return { content: [{ type: "text", text: "(未找到匹配文件)" }] };
    const deduped = deduplicate(text);
    if (deduped.length === 0) return { content: [{ type: "text", text: "(未找到匹配文件)" }] };
    log(`search_files 返回 ${deduped.length} 条`);
    return { content: [{ type: "text", text: deduped.join("\n") + `\n\n(去重后共 ${deduped.length} 篇)` }] };
  }
);

// ── 工具 2: 内容搜索 (es.exe content:, GBK 输出) ──
server.tool(
  "search_content_es",
  "在知识库中按文件内容搜索（调用 es.exe content:，需 Everything 内容索引）",
  {
    keyword: z.string().describe("内容搜索关键词"),
  },
  async ({ keyword }) => {
    log(`===== search_content_es  keyword="${keyword}" =====`);
    await ensureEverything();
    // 关键词含空格时需加引号，否则 es.exe 会将其拆分为文件名搜索
    const contentArg = `content:"${keyword}"`;
    const args = ["ext:md", contentArg, "-path", kbRoot];
    const { text, exitCode } = await spawnRun(esPath, args, "search_content_es", "gbk");
    if (exitCode !== 0 && !text) {
      return { content: [{ type: "text", text: `es.exe content: 搜索失败（exit code: ${exitCode}）。请确认 Everything 已启用内容索引。` }] };
    }
    if (!text) return { content: [{ type: "text", text: "(未找到匹配内容)" }] };
    const deduped = deduplicate(text);
    if (deduped.length === 0) return { content: [{ type: "text", text: "(未找到匹配内容)" }] };
    log(`search_content_es 返回 ${deduped.length} 条`);
    return { content: [{ type: "text", text: deduped.join("\n") + `\n\n(去重后共 ${deduped.length} 篇)` }] };
  }
);

// ── 工具 3: 文件内精确内容搜索 (rg, UTF-8 输出, 直接 spawn 不经过 shell) ──
server.tool(
  "search_content_rg",
  "在指定文件中用 ripgrep 搜索匹配内容（支持正则，返回匹配行及上下文）",
  {
    pattern: z.string().describe("搜索关键词或正则表达式"),
    filePath: z.string().describe("要搜索的文件完整路径"),
  },
  async ({ pattern, filePath }) => {
    log(`===== search_content_rg  pattern="${pattern}"  file="${filePath}" =====`);
    // 防御：路径不以 .md 结尾 → 可能是目录或截断路径，直接报错
    if (!filePath.endsWith(".md")) {
      log(`search_content_rg 拒绝：路径不以 .md 结尾，疑似目录或截断 → ${filePath}`);
      return { content: [{ type: "text", text: `❌ 路径校验失败：「${filePath}」不是一个 .md 文件路径。请直接复制 search_files 返回的完整路径（含文件名），不要截断。` }] };
    }
    // rg 直接 spawn，不经过 shell，Unicode 路径原封不动
    let { text, exitCode } = await spawnRun("rg", [pattern, filePath, "-C", "2"], "rg", "utf-8");

    if (isCommandNotFound(text, exitCode)) {
      log(`rg 未安装，回退到 Select-String`);
      const psPath = filePath.replace(/'/g, "''");
      const psPattern = pattern.replace(/'/g, "''");
      const { text: psText } = await spawnRun(
        "powershell",
        ["-NoProfile", "-Command",
         `$OutputEncoding = [Text.Encoding]::UTF8; [Console]::OutputEncoding = [Text.Encoding]::UTF8; Select-String -Path '${psPath}' -Pattern '${psPattern}' -Context 2 | Out-String -Width 4096`],
        "Select-String",
        "utf-8"
      );
      return { content: [{ type: "text", text: psText || "(未找到匹配内容)" }] };
    }

    log(`rg 完成 exitCode=${exitCode}  text_len=${text.length}`);
    return { content: [{ type: "text", text: text || "(未找到匹配内容)" }] };
  }
);

// ── 工具 4: 修辞句子库搜索 (jsonl 内存搜索) ──
server.tool(
  "search_rhetoric",
  "在优秀修辞句子库中搜索匹配的句子，按主题关键词和标签过滤。返回句子原文和标签，由 AI 决定直接使用或仿写。",
  {
    query: z.string().min(1).describe("搜索关键词，描述要找的主题内容（如"奋斗 青春"，空格分隔多个词）"),
    tags: z.string().optional().describe("过滤标签，多个用逗号分隔（如"比喻,排比,对偶"）"),
    count: z.number().optional().default(5).describe("返回结果数量，默认 5"),
  },
  async ({ query, tags, count = 5 }) => {
    log(`===== search_rhetoric  query="${query}" tags="${tags || ""}" count=${count} =====`);
    const db = loadRhetoricDb();
    if (db.length === 0) {
      return { content: [{ type: "text", text: "(句子库为空，请先准备 好词好句.jsonl)" }] };
    }

    const queryTerms = query.split(/\s+/).filter(Boolean).map(t => t.toLowerCase());
    const tagFilter = tags ? tags.split(/[,，]\s*/).map(t => t.trim().toLowerCase()).filter(Boolean) : [];

    const scored = [];
    for (const item of db) {
      const text = item.text || "";
      const itemTags = (item.tags || []).map(t => t.toLowerCase());

      // Tag filter: if tag filter specified, at least one tag must match
      if (tagFilter.length > 0 && !tagFilter.some(t => itemTags.includes(t))) continue;

      // Text match score: how many query terms appear in the text
      const textLower = text.toLowerCase();
      const matchCount = queryTerms.filter(t => textLower.includes(t)).length;
      const textScore = queryTerms.length > 0 ? matchCount / queryTerms.length : 0;

      // Tag bonus: matching tags add 0.2 each
      const tagBonus = tagFilter.length > 0
        ? tagFilter.filter(t => itemTags.includes(t)).length / tagFilter.length * 0.3
        : 0;

      scored.push({ text: item.text, tags: item.tags, score: textScore + tagBonus });
    }

    scored.sort((a, b) => b.score - a.score);
    const top = scored.slice(0, Math.min(count, 20));

    if (top.length === 0) {
      return { content: [{ type: "text", text: "(未找到匹配的句子)" }] };
    }

    const lines = top.map((s, i) => {
      return `【${i + 1}】${s.text}\n  标签：${(s.tags || []).join("、")}`;
    });
    const footer = `\n\n(共找到 ${scored.length} 条匹配，展示前 ${top.length} 条)`;
    return { content: [{ type: "text", text: lines.join("\n\n") + footer }] };
  }
);

// 启动
log("MCP 服务器启动中...");
const transport = new StdioServerTransport();
await server.connect(transport);
log("MCP 服务器已连接");
