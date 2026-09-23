# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

中文文稿写作 Agent 工具集 — 覆盖「构思 → 起草 → 审核 → 润色」全流程的中文非虚构文稿写作辅助工具链。

**一个仓库，两个交付面**。两边不共享运行时配置，必须分别维护：

| 交付面 | 目标平台 | 配置位置 | 形态 |
|---|---|---|---|
| VS Code Copilot | GitHub Copilot Chat | `.copilot/` | 4 Agent + 19 Skill |
| IMA 适配层 | ima.copilot（腾讯） | `ima/` | 23 Skill（4 个 Agent 也落为 Skill） |

仓库主体是纯声明式配置——**无构建系统、无测试框架、无 lint**。唯一例外是 `tools/sanitize-filename/`（独立 VS Code 扩展，有 TypeScript 编译）。

> 本项目**不包含"从零生成"功能**：定位是构思、分析、评判、重构、优化、润色，生成环节交由外部知识库（腾讯 IMA）承担。新增功能时应维持这个边界。

## Architecture

### 交付面一：`.copilot/` → VS Code Copilot

- `.copilot/agents/*.agent.md` — 4 个 Agent（点子王 / 批判家 / 分析师 / 档案员）。有独立人格，多轮对话，**绝不修改文件**。
- `.copilot/skills/<技能名>/SKILL.md` — 19 个 Skill。单次任务，**直接或确认后修改文件**。
- 部署链：`install`（PowerShell，从 GitHub raw 拉取）或 `local_install.bat`（本地）→ `%USERPROFILE%\.copilot\`，对所有项目全局生效。

**⚠️ 三个最容易踩的坑：**

1. **改仓库文件不会生效。** Skill 内部以**安装后的绝对路径**调用脚本与资源——例如 `.copilot/skills/量化分析/SKILL.md` 里写的是 `python "~/.copilot/tools/scripts/analyze.py" "<文件>"`。改完 `.copilot/` 下的文件必须**重新部署 + 重启 VS Code**（Agent/Skill 仅在启动时扫描加载）。直接改仓库文件不会影响已安装的副本。
2. **新增 Skill 必须手工同步 `install` 脚本。** `install`（PowerShell）中的 `$Agents` / `$Skills` 是**硬编码数组**；`local_install.bat` 遍历目录，会自动跟上。只加目录不改 `install`，一键安装会静默漏装。
3. **README 与本文件中的数量、目录清单属于手工维护的冗余信息**，改动 Skill/Agent 时需一并核对，否则会腐烂（历史上已多次发生）。

### 交付面二：`ima/` → ima.copilot（腾讯）

`ima/` 是本工具集在腾讯 ima.copilot 上的**适配层**：把 `.copilot/` 的 4 Agent + 19 Skill 按功能**一一对应**改造为 23 个 IMA Skill（IMA 无 Agent/Skill 之分，故 4 个 Agent 同样落为 Skill——**在 IMA 侧它们同样可以修改文件**，「不修改文件」只是 Copilot 侧 Agent 的约束）。

功能映射（IMA 侧为 kebab-case，目录名与 `name` 字段一致）：

| Copilot 侧 | IMA 侧 | Copilot 侧 | IMA 侧 |
|---|---|---|---|
| 点子王（Agent） | `brainstorm` | 神来之笔 | `golden-phrase` |
| 批判家（Agent） | `review` | 增加修辞 | `rhetoric` |
| 分析师（Agent） | `structure` | 简化修辞 | `simplify` |
| 档案员（Agent） | `doc-search` | 去除标签 | `plain-text` |
| 写中心句 | `topic` | 校对勘误 | `errata` |
| 摘要生成 | `summary` | 统一风格 | `style` |
| 标题优化 | `title` | 传达提纲 | `extract` |
| 段落重组 | `reorder` | 优化句式 | `polish` |
| 大纲生成 | `outline` | 量化分析 | `stats` |
| 增加过渡 | `transition` | | |
| 缩减篇幅 | `shorten` | | |
| 扩充篇幅 | `expand` | | |
| 合并段落 | `merge` | | |
| 拆分段落 | `split` | | |

**IMA 侧的平台差异（改造时必须遵守）：**

1. **frontmatter 只有 `name` + `description` 两个字段**（无 `tools` / `target`）。`name` 必须 kebab-case、≤64 字符、不能以 `-` 开头结尾或有连续 `--`。`description` 是**单行中文**，固定格式为「做什么 → 触发条件 → 不适用边界」——与 Copilot 侧带 YAML 列表的多行 `description` 写法完全不同。
2. **正文节名与结构不同**：IMA 侧 23 个 Skill **全部**以 `技能概述` + `操作范围` 开头（对应 Copilot 侧的 `当前角色` + `操作范围规则`），且**不保留 `编辑策略（铁律）` 一节**——那一节针对的是 Copilot 原生编辑工具的限制，IMA 侧编辑走平台自己的工具约定。
3. **脚本路径铁律**：IMA **不支持跨技能共享脚本**。脚本必须写成绝对路径 `/sandbox/workspace/skills/<skill-name>/scripts/`，共用的脚本要在每个用到的技能目录下**各存一份副本**。这就是 `expand/` `polish/` `shorten/` `stats/` `style/` 各自带一份 `analyze.py` 的原因——**不要"优化"成共享**。
4. **资源组织不同**：IMA 侧有 `stats/references/scoring-rubric.md`（Copilot 侧没有），并把修辞句子库落为 `golden-phrase/assets/good-sentences.jsonl`、用 `scripts/search_rhetoric.py` 替代 Copilot 侧的 MCP 工具 `search_rhetoric`。脚本在**本地 Linux 沙盒**（`/sandbox/workspace/`）中由 `shell` 工具调用。
5. SKILL.md 建议 ≤400 行，超出部分拆入 `references/`；至少 2 个覆盖典型场景的工作流示例；长流程设用户确认门。
6. 注册/更新：`ima_skill_create -d /sandbox/workspace/skills/<skill-name>/`，新对话中生效。
7. **打包要求**：ZIP 文件名 = `name` 字段 = 包内目录名，三者必须一致；包内换行符必须为 **LF**，frontmatter 前**不得有 UTF-8 BOM**（Windows 下打包前务必存为 UTF-8 without BOM）。

**同步铁律**：`ima/` 是**派生层**。修改 `.copilot/skills/<技能名>/SKILL.md` 或 `.copilot/agents/<Agent>.agent.md` 后，**必须**同步改写对应的 `ima/<skill-name>/SKILL.md`。两边的「操作范围 / 执行方式 / 输出格式」逻辑应保持一致，差异只体现在 frontmatter 格式、正文节名、脚本路径写法与资源组织方式上（即上述平台差异）。

`ima/packages/` 存放按技能打包的 ZIP（每个技能一个）与整合包 `IMA中文写作技能包.rar`（内含 23 个 ZIP + `中文写作技能包使用说明.md`，全部为裸文件名）。**改动任一 SKILL.md 后，须重打对应的 per-skill ZIP 并重建整合包**——具体命令与校验要点见 `MIGRATION-GUIDE.md` 的「4. 打包注册」。

`ima/` 下另有四份人读文档：`ima-skill开发指南.md`（平台规范权威来源）、`MIGRATION-GUIDE.md`（**同步流程与检查清单的权威来源**——逐条列出哪些 Copilot 特有内容要删除、脚本路径怎么改、打包编码要求）、`ima-skill-Python脚本使用指南.md`（沙盒与脚本调用）、`packages/中文写作技能包使用说明.md`（面向使用者）。

> **注意：IMA 侧不内置风格档案。** `.copilot/skills/统一风格/*.json` **不需要也刻意不迁移**到 IMA——IMA 的风格来源是用户上传的参考文件、知识库文章或文本样本（见 `ima/style/SKILL.md`）。因此 `ima/style/` 下没有、也不应新建 `references/`。这是设计决策，不是漏迁，不要"补全"它。

### 其他目录

- `local-search-mcp-server/` — Node.js MCP 服务器，为 Copilot 侧的档案员与「神来之笔」提供搜索后端。提供 4 个工具：`search_files`（es.exe）、`search_content_rg`（ripgrep）、`search_content_ps`（Select-String，rg 缺失时兜底）、`search_rhetoric`（修辞句子库）。**所有路径由服务器自身的 `config.json` 提供，代码不做任何路径推测**；`config.json` 不入库，模板为 `config.example.json`。前置依赖 Everything（`es.exe` 在 PATH）与 ripgrep。
- `tools/sanitize-filename/` — **独立的 VS Code 扩展**（TypeScript）。自动检测并规范化含特殊字符的文件名，解决 Copilot 因文件名特殊字符而失效的问题。有自己的 `package.json` / `CHANGELOG.md` / `package.nls*.json`（中英文菜单适配）。
- `tools/esrg/` — Python Textual 编写的独立 TUI 知识库搜索工具（Everything 文件名搜索 + ripgrep 内容搜索），不依赖 VS Code。构建脚本会自动下载 `es.exe` / `ripgrep` 到 `bins/`。
- `tools/scripts/analyze.py` — 中文文本定量分析引擎（jieba），被 Copilot 侧「量化分析」Skill 调用。仓库内仅此一份，但 **Skill 调用的是安装后的副本**。
- `prompt/` — 给人看的提示词参考（`风格提取.md` / `输出规范.md` / `任务分解.md`）。**不被任何平台加载**，改动不影响运行。
- `assets/` — 示意图与演示文稿。

## Common Commands

```bash
# 部署到 Copilot 全局（~/.copilot/）
#   local_install.bat 末尾有 pause，供双击交互执行；同时完成 npm install 与 mcp.json 合并
cmd /c local_install.bat
#   手动部署：把 .copilot/agents/ 与 .copilot/skills/ 复制到 %USERPROFILE%\.copilot\

# MCP 服务器
cd local-search-mcp-server && npm install
node index.js                     # stdio 传输，通常由 VS Code 拉起

# 定量分析（Skill 实际调用的是 ~/.copilot/tools/scripts/analyze.py）
python tools/scripts/analyze.py <文件路径> [--section]

# esrg 独立 TUI
cd tools/esrg && python -m esrg   # 运行（依赖 textual；或先 pip install -e . 后用 esrg 命令）
python tools/esrg/build.py        # PyInstaller 打包 esrg.exe，自动下载依赖二进制
python tools/esrg/build.py --dir         # onedir 构建（启动更快，便于调试）
python tools/esrg/build.py --download    # 仅下载 es.exe / ripgrep 到 bins/

# Sanitize Filename 扩展
cd tools/sanitize-filename
npm install && npm run compile    # tsc -p ./ → out/extension.js
npm run package                   # vsce package --no-dependencies → *.vsix
bash build.sh                     # 上述步骤的封装
```

无测试与 lint 命令可跑——本仓库没有测试框架，也没有 lint 配置。

## Key Conventions

### 操作范围规则（所有 Skill / Agent 一致）

**选中了文本则只操作选中部分，否则操作全文。**

### 修改前确认

- 等待确认：**标题优化 / 段落重组 / 大纲生成**——先出方案，用户确认后才改文件
- 直接修改：其余所有 Skill

### 文件结构约定

两者都以 YAML frontmatter 开头，后接 Markdown 正文。`name` 字段、正文首级标题与目录名（Agent 为文件名）三者一致。

- **Agent**（`.agent.md`）：frontmatter 含 `name` / `description` / `tools` / `target`。首节 `角色设定`、末节 `注意事项`，中间必含 `核心原则`（"不修改文件"）与 `输出格式`，其余为各自专属节——如批判家的 `审查维度` / `问题分级标准`、分析师的 `分析维度` / `工作模式`。
- **Skill**（`SKILL.md`）：frontmatter 含 `name` / `description`（含触发条件关键词）。19 个 Skill **全部**必含 `当前角色` / `操作范围规则` / `编辑策略（铁律）` 三节，通常还有 `执行方式`（或等价的 `工作流程`）与 `输出格式`（量化分析为 `输出 JSON 结构` + `对话展示格式`）。中间可按需增设专属节（`目标设定方式`、`上下文理解`、`风格档案说明` 等）。

### 编辑策略（铁律）— 所有 Skill 必含

这是贯穿全部 19 个 Skill 的核心约定，每个 Skill 都有一节 `## 编辑策略（铁律）`，内容一致，规定**修改文件前必须完成的检查**：

1. **前置检查目标是否已保存**：若编辑对象是未保存的 buffer（`Untitled-*`、无文件路径）→ 立即告知用户"请先保存文件后再执行此操作"，停止执行
2. **检查文件名**：文件名含特殊字符（`"'(){}[]#&!@$%^*+=~\`<>?|` 或空格）会导致 Copilot 编辑工具失效 → 告知用户先用 **Sanitize Filename** 规范化文件名（界面提示为从 VSIX 安装，即 `tools/sanitize-filename/`）
3. **用 Copilot 原生编辑能力修改**（`replace_string_in_file` / `multi_replace_string_in_file`）
4. **失败即停**：编辑工具调用失败时**必须停止**并如实告知用户，**严禁迂回**——不得新建文件替换原文件、不得编写并执行 PowerShell / Python / Shell 脚本、不得用 sed / awk 间接修改。原因：这些迂回方式与原生编辑工具走同一套文件系统 API，原生工具因路径问题失效时它们同样会失败，只会引入额外风险与不一致。

> 这条铁律是本项目与 `tools/sanitize-filename/` 扩展之间的纽带——该扩展正是为解决第 2 条的失效场景而存在。

### 触发词设计原则

- **避免高频通用词**：如"修改""检查"在日常对话中出现频率过高会误触发。触发词应精准、特化，与 Skill 核心行为强关联（如"按勘误表修改"而非"帮我改"）
- **宁缺毋滥**：6 个左右即可，不做关键词堆砌

### Skill↔Agent 解耦

SKILL.md 中引用 Agent 时统一写「其他 Agent」，**不点名**具体 Agent 名称，避免形成"是不是有个叫 X 的 Agent"的歧义。

### Agent↔Skill 互推机制

- 每个 Agent 的「注意事项」末尾应包含 Skill 推荐逻辑：根据诊断结果主动推荐可用 Skill，形成「诊断 → 推荐 → 修改」闭环
- 新增 Agent 或 Skill 时，需同步检查相关 Agent 的推荐列表是否需要更新

### 勘误表规范（批判家 → 校对勘误）

- 勘误表位于审核报告末尾（总体结论之后），是「校对勘误」Skill 的**唯一输入源**
- 格式：`| # | 行号 | 原表述 | 更正表述 | 等级 |`，四列缺一不可
- **强制铁律**：输出勘误表前必须逐条核实行号与原文完全一致，不得有偏差
- 批判家输出末尾附带触发提示语：「按勘误表修改」

### 校对勘误 Skill 的上下文回溯机制

- 不通过参数接收勘误表，而是回溯对话历史，定位最近的一张勘误表
- 按行号升序排列后逐条执行，避免行号偏移
- 若对话中无勘误表，告知用户而非自行发挥

### README 表格规范

- 表格统一使用 HTML `<table width="100%">` + 百分比列宽，保持视觉一致性
- 提示区块使用 GitHub Alerts 格式（`[!NOTE]` / `[!TIP]` / `[!WARNING]`）

## Common Development Tasks

### 新增 Skill

1. 创建 `.copilot/skills/<技能名>/SKILL.md`，按上述「文件结构约定」编写（`当前角色` / `操作范围规则` / `编辑策略（铁律）` 三节必含）
2. **把技能名加进 `install` 的 `$Skills` 数组**（否则一键安装漏装）
3. 在 `ima/` 建立对应 Skill，按上述 IMA 平台差异改写，并重新打包 ZIP
4. 检查是否有 Agent 应在诊断后推荐该 Skill，更新其「注意事项」推荐列表
5. 核对 README 与本文件中的 Skill 数量与清单

### 新增 Agent

1. 创建 `.copilot/agents/<名称>.agent.md`，需 `tools` / `target` 字段，遵守"不修改文件"原则
2. **加进 `install` 的 `$Agents` 数组**
3. 在 `ima/` 建立对应的 `brainstorm` 式 Skill（Agent 在 IMA 侧同样是 Skill）
4. 检查其诊断结果能关联哪些现有 Skill，加入推荐逻辑

### 修改触发词

编辑 frontmatter `description` 中的触发条件列表；Copilot 侧为 YAML 列表，IMA 侧需合并为单行中文。

### Sanitize Filename 版本号铁律

修改 `tools/sanitize-filename/src/extension.ts` 或 `package.json` 后重新打包时，**必须**递增 `package.json` 中的 `version`（patch +1），同步更新 `tools/sanitize-filename/CHANGELOG.md`，**绝不**复用同一版本号重新打包。

### MCP 配置

配置位于 `local-search-mcp-server/config.json`（不在 git 中），所有路径由该文件提供，代码不做任何路径推测。首次安装后需填写 `kbRoot` 与 `rhetoricDbPath`。
