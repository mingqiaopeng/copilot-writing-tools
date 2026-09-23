# 迁移指南：Copilot → IMA 同步更新

当仓库中 Copilot 端的 SKILL.md / Agent 有内容更新时，按以下流程同步到 IMA 端。

---

## 映射表

| Copilot 源文件 | IMA name（= 目录名） |
|--------|----------|
| `.copilot/agents/点子王.agent.md` | `brainstorm` |
| `.copilot/agents/批判家.agent.md` | `review` |
| `.copilot/agents/分析师.agent.md` | `structure` |
| `.copilot/agents/档案员.agent.md` | `doc-search` |
| `.copilot/skills/写中心句/SKILL.md` | `topic` |
| `.copilot/skills/摘要生成/SKILL.md` | `summary` |
| `.copilot/skills/标题优化/SKILL.md` | `title` |
| `.copilot/skills/段落重组/SKILL.md` | `reorder` |
| `.copilot/skills/大纲生成/SKILL.md` | `outline` |
| `.copilot/skills/增加过渡/SKILL.md` | `transition` |
| `.copilot/skills/缩减篇幅/SKILL.md` | `shorten` |
| `.copilot/skills/扩充篇幅/SKILL.md` | `expand` |
| `.copilot/skills/合并段落/SKILL.md` | `merge` |
| `.copilot/skills/拆分段落/SKILL.md` | `split` |
| `.copilot/skills/简化修辞/SKILL.md` | `simplify` |
| `.copilot/skills/神来之笔/SKILL.md` | `golden-phrase` |
| `.copilot/skills/增加修辞/SKILL.md` | `rhetoric` |
| `.copilot/skills/去除标签/SKILL.md` | `plain-text` |
| `.copilot/skills/校对勘误/SKILL.md` | `errata` |
| `.copilot/skills/统一风格/SKILL.md` | `style` |
| `.copilot/skills/传达提纲/SKILL.md` | `extract` |
| `.copilot/skills/优化句式/SKILL.md` | `polish` |
| `.copilot/skills/量化分析/SKILL.md` | `stats` |

> IMA 侧技能名一律为 kebab-case 英文，且 `name` 字段、目录名、ZIP 包内目录名三者必须一致。

### 数据文件映射

| 源文件 | IMA 位置 |
|--------|---------|
| `tools/scripts/analyze.py` | 嵌入各技能：`ima/expand/scripts/`、`ima/polish/scripts/`、`ima/shorten/scripts/`、`ima/stats/scripts/`、`ima/style/scripts/` |
| `F:\文档资料库\好词好句.jsonl` | `ima/golden-phrase/assets/good-sentences.jsonl` |
| `.copilot/skills/统一风格/*.json` | **不迁移**——IMA 侧的风格来源是用户上传的参考文件 / 知识库文章 / 文本样本（见 `ima/style/SKILL.md`），不内置风格档案，也不要在 `ima/style/` 下新建 `references/` |

---

## 同步流程

### 1. 同步 SKILL.md 正文逻辑

**需要同步的内容**：
- 操作流程、工作流示例、输出格式等核心逻辑
- 触发条件关键词

**需要删除/替换的内容**（Copilot 特有 → IMA 替代）：

| Copilot 特有内容 | IMA 处理方式 |
|-----------------|-------------|
| "当前角色" 章节 | 改为 "技能概述" |
| "操作范围规则" | 改为 "操作范围"（简化） |
| "编辑策略（铁律）" 整节 | **删除** |
| "检查文件名" + sanitize-filename 引用 | **删除** |
| `replace_string_in_file` / 迂回方式禁止 | **删除** |
| `tools: ['read', 'search', 'web']` 等 frontmatter | **删除** |
| `target: 'vscode'` frontmatter | **删除** |
| 引用 `~/.copilot/tools/scripts/analyze.py` | 改为 `python3 /sandbox/workspace/skills/<name>/scripts/analyze.py` |
| `search_rhetoric` MCP 工具 | 改为 `python3 search_rhetoric.py --query ...` |
| MCP 文件搜索 | 改为 IMA 自带知识库搜索 |

### 2. 同步数据文件

- **好词好句.jsonl**：从 `F:\文档资料库\` 复制到 `ima/golden-phrase/assets/good-sentences.jsonl`
- **风格 JSON 不迁移**：`.copilot/skills/统一风格/*.json` 是 Copilot 侧的内置风格档案（用于「指定风格改写」）。IMA 侧不内置风格档案，风格来源改由用户提供——上传的参考文件、知识库文章或文本样本，因此既不复制这些 JSON，也不在 `ima/style/` 下新建 `references/`

### 3. 同步脚本文件

> **重要**：IMA 不支持跨技能共享路径。每个需要脚本的技能必须将脚本嵌入自己的 `scripts/` 目录。

- `tools/scripts/analyze.py` → 复制到以下技能的 `scripts/analyze.py`：
  - `ima/stats/scripts/analyze.py`
  - `ima/style/scripts/analyze.py`
  - `ima/shorten/scripts/analyze.py`
  - `ima/expand/scripts/analyze.py`
  - `ima/polish/scripts/analyze.py`
- 脚本路径引用格式：`/sandbox/workspace/skills/<name>/scripts/analyze.py`

### 4. 打包注册

**① 更新技能 ZIP（产出物存放于 `ima/packages/`）**

ZIP 文件名 = `<name>.zip`，内部目录结构：
```
<name>.zip
  └── <name>/          ← 必须与 name 字段一致
      ├── SKILL.md
      ├── scripts/     (可选)
      └── assets/      (可选)
```

在 IMA 对话中上传 ZIP 即可自动注册。覆盖上传同名的 ZIP 可更新已有技能。

> **注意**：ZIP 包内所有文件的换行符必须为 LF（Unix 格式），YAML frontmatter 前不允许有 UTF-8 BOM（字节序标记）。Windows 系统打包前请确保文件编码为 UTF-8 without BOM。

**② 重建整合包**

`ima/packages/IMA中文写作技能包.rar` 是供一次性上传的整合包，内容为 **23 个 per-skill ZIP + `中文写作技能包使用说明.md`**，且全部为归档根目录下的**裸文件名**（不含任何目录层级）。**任何一个技能更新后都必须重建它**，否则整合包内仍是被替换前的旧版本。

```bash
cd ima/packages
"/c/Program Files/WinRAR/Rar.exe" a -ep1 -y "IMA中文写作技能包.rar" *.zip *.md
```

- `-ep1` 排除基目录名，保持条目为裸文件名（与既有结构一致）
- 就地更新已变更的条目，未变更的条目内容保持原样
- 用通配符 `*.zip` / `*.md` 展开，避免手输中文文件名
- 重建后确认归档条数仍为 **24**（23 个 ZIP + 1 个说明文档）；条数变多通常意味着某条目被按错误文件名重复写入

> 生成 RAR 需要 WinRAR（`7z` 只能解不能生成 RAR）。若本机无 WinRAR，可退而只发布 per-skill ZIP，在 IMA 中逐个注册。

---

## 不可同步的内容

以下内容不需要同步：
- Copilot 的 "编辑策略（铁律）" 相关章节
- Agent 的 "不修改文件" 约束（IMA 中全部为 Skill，可修改文件）
- `sanitize-filename` VSIX 插件推荐
- 平台安装脚本（`install` / `local_install.bat`）
- `.copilot/skills/统一风格/*.json`（Copilot 侧内置风格档案；IMA 侧风格由用户提供）

---

## 更新检查清单

- [ ] 核心逻辑已同步（操作流程、工作流示例、输出格式）
- [ ] 触发条件关键词已同步
- [ ] Copilot 特有字段已删除（tools/target/编辑策略）
- [ ] 脚本路径已修正为 `skills/<name>/scripts/`
- [ ] MCP 工具调用已替换
- [ ] 数据文件已同步
- [ ] ZIP 文件名 = name 字段 = 内部目录名，三者一致
- [ ] 文件编码 UTF-8 without BOM，换行符 LF
- [ ] 无 TODO 占位符残留
- [ ] 变更的技能 ZIP 已重新打包到 `ima/packages/`
- [ ] 整合包 `IMA中文写作技能包.rar` 已重建，且条目数仍为 24
