#!/usr/bin/env python3
"""一致性校验器 — 把 CLAUDE.md / MIGRATION-GUIDE.md 里靠人记的约束固化成可执行检查

用法:
    python tools/check.py            # 全量检查
    python tools/check.py --quiet    # 只输出失败项与汇总

退出码: 0 = 全部通过, 1 = 有失败项

背景：本仓库是纯声明式配置，没有测试框架。数量、映射表、包结构、编码、
脚本副本一致性这些约束此前全靠手工维护，已多次腐烂（见 CLAUDE.md
「三个最容易踩的坑」第 3 条）。本脚本把这些约束变成一次跑完的检查。
"""

import os
import re
import json
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COPILOT_SKILLS = os.path.join(ROOT, ".copilot", "skills")
COPILOT_AGENTS = os.path.join(ROOT, ".copilot", "agents")
IMA = os.path.join(ROOT, "ima")
PACKAGES = os.path.join(IMA, "packages")

# 与 ima/MIGRATION-GUIDE.md「更新检查清单」逐条对应
IMA_MAX_LINES = 400
IMA_MIN_EXAMPLES = 2

results = []  # (level, check_name, message)


def ok(name, msg=""):
    results.append(("PASS", name, msg))


def fail(name, msg):
    results.append(("FAIL", name, msg))


def warn(name, msg):
    results.append(("WARN", name, msg))


def read(path, binary=False):
    mode = "rb" if binary else "r"
    kw = {} if binary else {"encoding": "utf-8", "errors": "replace"}
    with open(path, mode, **kw) as f:
        return f.read()


def list_dirs(path):
    if not os.path.isdir(path):
        return []
    return sorted(
        d for d in os.listdir(path)
        if os.path.isdir(os.path.join(path, d)) and not d.startswith(".")
    )


# ============================================================
# 1. Copilot 侧：技能 / Agent 清单与 install 脚本一致
# ============================================================

def check_install_arrays():
    install = read(os.path.join(ROOT, "install"))
    m_agents = re.search(r"\$Agents\s*=\s*@\((.*?)\)", install, re.S)
    m_skills = re.search(r"\$Skills\s*=\s*@\((.*?)\)", install, re.S)

    if not m_agents or not m_skills:
        fail("install 数组", "未能在 install 中解析 $Agents / $Skills 数组")
        return

    listed_agents = set(re.findall(r'"([^"]+)"', m_agents.group(1)))
    listed_skills = set(re.findall(r'"([^"]+)"', m_skills.group(1)))

    disk_agents = {
        f for f in os.listdir(COPILOT_AGENTS) if f.endswith(".agent.md")
    } if os.path.isdir(COPILOT_AGENTS) else set()
    disk_skills = set(list_dirs(COPILOT_SKILLS))

    missing_skills = disk_skills - listed_skills
    missing_agents = disk_agents - listed_agents
    ghost_skills = listed_skills - disk_skills
    ghost_agents = listed_agents - disk_agents

    if missing_skills:
        fail("install $Skills", f"目录存在但未加入 install 数组（会静默漏装）：{sorted(missing_skills)}")
    if missing_agents:
        fail("install $Agents", f"文件存在但未加入 install 数组：{sorted(missing_agents)}")
    if ghost_skills:
        fail("install $Skills", f"数组中的技能目录不存在：{sorted(ghost_skills)}")
    if ghost_agents:
        fail("install $Agents", f"数组中的 Agent 文件不存在：{sorted(ghost_agents)}")
    if not (missing_skills or missing_agents or ghost_skills or ghost_agents):
        ok("install 数组", f"{len(listed_agents)} 个 Agent、{len(listed_skills)} 个 Skill 与磁盘一致")


# ============================================================
# 2. Copilot 侧：SKILL.md 结构约定
# ============================================================

def check_copilot_skills():
    required = ["当前角色", "操作范围规则", "编辑策略（铁律）"]
    for name in list_dirs(COPILOT_SKILLS):
        path = os.path.join(COPILOT_SKILLS, name, "SKILL.md")
        if not os.path.isfile(path):
            fail(f"Copilot Skill/{name}", "目录中缺少 SKILL.md")
            continue

        text = read(path)

        m_name = re.search(r"^name:\s*(.+)$", text, re.M)
        if not m_name:
            fail(f"Copilot Skill/{name}", "frontmatter 缺少 name 字段")
        elif m_name.group(1).strip() != name:
            fail(f"Copilot Skill/{name}", f"name 字段「{m_name.group(1).strip()}」与目录名不一致")

        missing = [s for s in required if f"## {s}" not in text]
        if missing:
            fail(f"Copilot Skill/{name}", f"缺少必含章节：{missing}")

        if not missing and (not m_name or m_name.group(1).strip() == name):
            ok(f"Copilot Skill/{name}")


def check_copilot_agents():
    for f in sorted(os.listdir(COPILOT_AGENTS)) if os.path.isdir(COPILOT_AGENTS) else []:
        if not f.endswith(".agent.md"):
            continue
        path = os.path.join(COPILOT_AGENTS, f)
        text = read(path)
        name = f[: -len(".agent.md")]

        m_name = re.search(r"^name:\s*(.+)$", text, re.M)
        if not m_name or m_name.group(1).strip() != name:
            fail(f"Copilot Agent/{name}", "name 字段与文件名不一致")
            continue

        missing = [s for s in ["角色设定", "核心原则", "输出格式", "注意事项"]
                   if f"## {s}" not in text]
        if missing:
            fail(f"Copilot Agent/{name}", f"缺少必含章节：{missing}")
        else:
            ok(f"Copilot Agent/{name}")


# ============================================================
# 3. IMA 侧：平台规范（ima-skill开发指南.md 三/五/六/七 节）
# ============================================================

def frontmatter_of(text):
    """返回 (frontmatter_dict, 正文)。非 frontmatter 文件返回 (None, text)。"""
    if not text.startswith("---"):
        return None, text
    end = text.find("\n---", 3)
    if end == -1:
        return None, text
    raw = text[3:end]
    body = text[end + 4:]
    fm = {}
    for line in raw.splitlines():
        m = re.match(r"^([A-Za-z_-]+):\s*(.*)$", line)
        if m:
            fm[m.group(1)] = m.group(2)
    return fm, body


def check_ima_skills():
    for name in list_dirs(IMA):
        path = os.path.join(IMA, name, "SKILL.md")
        if not os.path.isfile(path):
            continue  # 非技能目录（如 packages）

        raw = read(path, binary=True)
        text = raw.decode("utf-8", errors="replace")
        line_count = text.count("\n") + (0 if text.endswith("\n") else 1)
        problems = []

        # BOM
        if raw.startswith(b"\xef\xbb\xbf"):
            problems.append("frontmatter 前有 UTF-8 BOM（ZIP 打包后 IMA 无法解析）")
        # 换行符
        if b"\r\n" in raw:
            problems.append("存在 CRLF 换行（ZIP 包内必须为 LF）")

        fm, body = frontmatter_of(text)
        if fm is None:
            problems.append("缺少 YAML frontmatter")
        else:
            if fm.get("name") != name:
                problems.append(f"name 字段「{fm.get('name')}」与目录名不一致")
            extra = set(fm) - {"name", "description"}
            if extra:
                problems.append(f"frontmatter 含 IMA 不支持的字段：{sorted(extra)}")
            if not fm.get("description"):
                problems.append("缺少 description")

        for section in ["技能概述", "操作范围"]:
            if f"## {section}" not in text:
                problems.append(f"缺少必含章节「{section}」")
        if "编辑策略" in text:
            problems.append("含 Copilot 侧专属的「编辑策略（铁律）」，IMA 侧应删除")
        if re.search(r"~\/\.copilot|replace_string_in_file|sanitize-filename", text):
            problems.append("含 Copilot 侧专属内容（编辑工具 / sanitize-filename）")

        examples = len(re.findall(r"^\*\*示例\s*\d+", body, re.M))
        if examples < IMA_MIN_EXAMPLES:
            problems.append(
                f"工作流示例仅 {examples} 个，平台要求 ≥{IMA_MIN_EXAMPLES} 个"
            )

        if line_count > IMA_MAX_LINES:
            problems.append(f"{line_count} 行，超过建议上限 {IMA_MAX_LINES} 行，应拆入 references/")

        if problems:
            fail(f"IMA Skill/{name}", "；".join(problems))
        else:
            ok(f"IMA Skill/{name}", f"{line_count} 行，{examples} 个示例")


# ============================================================
# 4. 映射表：MIGRATION-GUIDE ↔ ima/ 目录 ↔ ZIP 产物
# ============================================================

def check_mapping():
    guide = read(os.path.join(IMA, "MIGRATION-GUIDE.md"))
    rows = re.findall(r"^\|\s*`(\.copilot/[^`]+)`\s*\|\s*`([a-z0-9-]+)`\s*\|", guide, re.M)

    if not rows:
        fail("映射表", "MIGRATION-GUIDE.md 中未解析到任何映射行")
        return

    mapped = {ima for _, ima in rows}
    # 只统计带 SKILL.md 的技能目录，排除 packages 等非技能目录
    disk = {
        d for d in list_dirs(IMA)
        if os.path.isfile(os.path.join(IMA, d, "SKILL.md"))
    }
    zips = {f[:-4] for f in os.listdir(PACKAGES) if f.endswith(".zip")} \
        if os.path.isdir(PACKAGES) else set()

    # Copilot 源文件是否都存在
    for src, _ in rows:
        if not os.path.isfile(os.path.join(ROOT, src.replace("/", os.sep))):
            fail("映射表", f"映射的源文件不存在：{src}")

    # 源覆盖率：每个 Copilot agent/skill 都应出现在映射表里
    copilot_all = {f".copilot/agents/{f}" for f in os.listdir(COPILOT_AGENTS)
                   if f.endswith(".agent.md")} if os.path.isdir(COPILOT_AGENTS) else set()
    copilot_all |= {f".copilot/skills/{d}/SKILL.md" for d in list_dirs(COPILOT_SKILLS)}
    unmapped = copilot_all - {src for src, _ in rows}
    if unmapped:
        fail("映射表", f"Copilot 侧存在但未映射到 IMA：{sorted(unmapped)}")

    # 目录 / ZIP 一致性
    for label, extra in (("目录", disk - mapped), ("ZIP", zips - mapped)):
        if extra:
            fail("映射表", f"IMA {label}存在但映射表未收录：{sorted(extra)}")
    for label, missing in (("目录", mapped - disk), ("ZIP", mapped - zips)):
        if missing:
            fail("映射表", f"映射表列出但 IMA {label}缺失：{sorted(missing)}")

    if not (unmapped or (disk - mapped) or (zips - mapped)):
        ok("映射表", f"{len(rows)} 条映射，Copilot ↔ IMA 目录 ↔ ZIP 三方一致")


# ============================================================
# 5. analyze.py 副本一致性（IMA 不支持跨技能共享，须逐份校验）
# ============================================================

def check_analyze_copies():
    canonical = os.path.join(ROOT, "tools", "scripts", "analyze.py")
    if not os.path.isfile(canonical):
        fail("analyze.py 副本", "正本 tools/scripts/analyze.py 不存在")
        return

    base = read(canonical, binary=True).replace(b"\r\n", b"\n")
    copies = []
    for d in list_dirs(IMA):
        p = os.path.join(IMA, d, "scripts", "analyze.py")
        if os.path.isfile(p):
            copies.append((d, p))

    if not copies:
        warn("analyze.py 副本", "IMA 侧未发现任何 analyze.py 副本")
        return

    drift = []
    for d, p in copies:
        if read(p, binary=True).replace(b"\r\n", b"\n") != base:
            drift.append(d)

    if drift:
        fail("analyze.py 副本",
             f"以下技能的副本与正本内容不一致（IMA 不支持跨技能共享，需逐份同步）：{drift}")
    else:
        ok("analyze.py 副本", f"{len(copies)} 份副本内容与正本一致（已忽略行尾差异）")


# ============================================================
# 6. MCP 工具名：文档中出现的 search_* 必须真实注册
# ============================================================

def check_mcp_tools():
    index = os.path.join(ROOT, "local-search-mcp-server", "index.js")
    if not os.path.isfile(index):
        fail("MCP 工具", "local-search-mcp-server/index.js 不存在")
        return

    js = read(index)
    registered = set(re.findall(r'server\.tool\(\s*"([^"]+)"', js))

    for doc in ("README.md", "CLAUDE.md", os.path.join(".copilot", "agents", "档案员.agent.md")):
        path = os.path.join(ROOT, doc)
        if not os.path.isfile(path):
            continue
        mentioned = set(re.findall(r"`(search_[a-z_]+)`", read(path)))
        phantom = mentioned - registered
        if phantom:
            fail(f"MCP 工具/{doc}",
                 f"文档提到未在 index.js 注册的工具：{sorted(phantom)}（已注册：{sorted(registered)}）")

    ok("MCP 工具", f"index.js 注册 {len(registered)} 个：{sorted(registered)}")


# ============================================================
# 7. 整合包含义：README 中声明的 Skill 数量
# ============================================================

def check_doc_counts():
    n_skills = len(list_dirs(COPILOT_SKILLS))
    n_agents = len([f for f in os.listdir(COPILOT_AGENTS)
                    if f.endswith(".agent.md")]) if os.path.isdir(COPILOT_AGENTS) else 0

    # 合法数量：Copilot 侧实际数，以及 IMA 侧 24（20 Skill + 4 Agent 落为 Skill）。
    # 其余任何数字（如历史的 19 / 23）都是过时计数，必须同步修改。
    valid = {"Skill": {n_skills, n_skills + n_agents}, "Agent": {n_agents}}

    for doc in ("README.md", "CLAUDE.md"):
        path = os.path.join(ROOT, doc)
        if not os.path.isfile(path):
            continue
        text = read(path)
        bad = []
        for m in re.finditer(r"(\d+)\s*(?:个\s*)?(Skill|Agent)", text):
            val, kind = int(m.group(1)), m.group(2)
            if val not in valid[kind]:
                line = text[: m.start()].count("\n") + 1
                bad.append(f"第 {line} 行「{val} {kind}」（应为 {n_skills}，IMA 侧为 {n_skills + n_agents}）")
        if bad:
            fail(f"数量一致性/{doc}", "存在与磁盘不符的数量：" + "；".join(sorted(set(bad))))
        else:
            ok(f"数量一致性/{doc}", f"{n_agents} 个 Agent、{n_skills} 个 Skill")


# ============================================================
# 8. 附属数据文件：JSON 必须可解析
# ============================================================

def check_json_assets():
    """风格档案等 JSON 附件必须是合法 JSON。

    历史教训：4 个风格档案因在中文正文里直接用 ASCII 双引号 " " 包裹引文，
    提前终止 JSON 字符串，全部不是合法 JSON。Skill 用 read 工具读文本时
    LLM 能容错，但任何脚本化解析都会硬失败。
    """
    targets = []
    style_dir = os.path.join(COPILOT_SKILLS, "统一风格")
    if os.path.isdir(style_dir):
        targets += [os.path.join(style_dir, f)
                    for f in sorted(os.listdir(style_dir)) if f.endswith(".json")]
    rhetoric = os.path.join(IMA, "golden-phrase", "assets", "good-sentences.jsonl")
    if os.path.isfile(rhetoric):
        targets.append(rhetoric)

    bad = []
    for p in targets:
        rel = os.path.relpath(p, ROOT).replace(os.sep, "/")
        if p.endswith(".jsonl"):
            # JSONL：逐行解析，跳过空行
            errs = []
            for i, line in enumerate(read(p).splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    json.loads(line)
                except json.JSONDecodeError as e:
                    if len(errs) < 3:
                        errs.append(f"第 {i} 行: {e}")
            if errs:
                bad.append(f"{rel} — {len(errs)}+ 行解析失败（{errs[0]}）")
            continue
        try:
            json.loads(read(p))
        except json.JSONDecodeError as e:
            # 给出定位提示：值内误用 ASCII 双引号是本项目的典型成因
            hint = ""
            if e.colno:
                line = read(p).splitlines()[e.lineno - 1] if e.lineno <= len(read(p).splitlines()) else ""
                seg = line[max(0, e.colno - 20): e.colno + 20]
                if '"' in seg.strip():
                    hint = f"（疑似值内误用 ASCII 双引号，位置附近: …{seg}…）"
            bad.append(f"{rel}: {e}{hint}")

    if bad:
        fail("JSON 附件", "；".join(bad))
    elif targets:
        ok("JSON 附件", f"{len(targets)} 个文件均可解析")


# ============================================================
# 9. 整合包：条目数应等于 ZIP 数 + 1
# ============================================================

def check_rar():
    rar = os.path.join(PACKAGES, "IMA中文写作技能包.rar")
    if not os.path.isfile(rar):
        warn("整合包", "IMA中文写作技能包.rar 不存在（打包产物不入库，属正常）")
        return

    # RAR 无法用 stdlib 解析条目数，改为提示手动校验
    n_zips = len([f for f in os.listdir(PACKAGES) if f.endswith(".zip")])
    warn("整合包",
         f"共 {n_zips} 个 ZIP，整合包应为 {n_zips + 1} 个条目；"
         f"条数需用 `Rar.exe l` 人工确认")


# ============================================================

CHECKS = [
    check_install_arrays,
    check_copilot_skills,
    check_copilot_agents,
    check_ima_skills,
    check_mapping,
    check_analyze_copies,
    check_mcp_tools,
    check_doc_counts,
    check_json_assets,
    check_rar,
]


def main():
    quiet = "--quiet" in sys.argv
    for fn in CHECKS:
        try:
            fn()
        except Exception as e:  # 检查器自身出错不应中断其余检查
            fail(fn.__name__, f"检查器异常：{type(e).__name__}: {e}")

    n_fail = sum(1 for r in results if r[0] == "FAIL")
    n_warn = sum(1 for r in results if r[0] == "WARN")
    n_pass = sum(1 for r in results if r[0] == "PASS")

    for level, name, msg in results:
        if level == "PASS" and quiet:
            continue
        mark = {"PASS": "  ok  ", "WARN": " warn ", "FAIL": " FAIL "}[level]
        print(f"[{mark}] {name}" + (f" — {msg}" if msg else ""))

    print()
    print(f"通过 {n_pass}　警告 {n_warn}　失败 {n_fail}")
    if n_fail:
        print("\n修复建议见 CLAUDE.md「Common Commands → 一致性校验」。")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
