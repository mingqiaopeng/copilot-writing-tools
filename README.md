# ✍️ 中文文稿写作 Agent 工具集

一套专为中文写作设计的 **GitHub Copilot 自定义 Agent 与 Skill 工具集**，覆盖从头脑风暴、大纲规划、起草撰写到严格审核的完整写作流程。包含 **4 个自定义 Agent** 和 **13 个 Skill**。

> **前置条件**：安装 [VS Code](https://code.visualstudio.com/) 并启用 [GitHub Copilot](https://github.com/features/copilot) 订阅。安装后，在 Copilot Chat 对话或编辑器内联对话中，Agent 与 Skill 将通过语义匹配自动触发调用。
>
> 💡 **推荐配置**：强烈建议将 GitHub Copilot 连接至 **DeepSeek V4** 模型使用，体验更佳。具体配置方法参见 [DeepSeek 官方文档](https://www.deepseek.com/)。

---

### ⚡ 一行命令安装

```powershell
irm https://raw.githubusercontent.com/mingqiaopeng/copilot-writing-tools/master/install | iex
```

无需 clone，无需下载，打开 PowerShell 粘贴回车即可。Agent 与 Skill 将自动部署到 `~/.copilot/`，**对所有项目全局生效**。重启 VS Code 后即可使用。

> 📦 用户亦可手动将仓库中的 `agents/` 和 `skills/` 目录复制到项目根目录的 `.copilot/` 下，或复制到 `~/.copilot/` 实现全局安装。GitHub Copilot 在 VS Code 启动时自动扫描加载。

---

## 🧠 工作机制：Copilot 如何发现 Agent 和 Skill

GitHub Copilot Custom Extensions 通过扫描项目目录中的特定文件夹来发现自定义 Agent 和 Skill。下面是其工作机制：

### Agent 与 Skill 的区别

| 维度 | 🤖 Custom Agent | 🔧 Skill |
|------|----------------|----------|
| 文件格式 | `.agent.md` | `SKILL.md` |
| 交互方式 | 多轮对话，有独立人格 | 单次任务，即用即走 |
| 修改文件 | ❌ 从不修改 | ✅ 直接或确认后修改 |
| 加载机制 | 在 Agent 选择器中可见 | 通过语义匹配触发 |
| 适用场景 | 头脑风暴、审核等需要来回讨论的场景 | 提炼中心句、生成摘要等明确操作 |

### 📂 目录扫描机制

VS Code + GitHub Copilot 在启动时扫描以下目录加载 Agent 和 Skill：

**Agent 位置：**
```
.github/agents/<名称>.agent.md    # 标准位置（VS Code 2026 新版）
.copilot/agents/<名称>.agent.md   # 兼容位置（本项目使用）
```

**Skill 位置：**
```
.github/skills/<名称>/SKILL.md    # 标准位置
.copilot/skills/<名称>/SKILL.md   # 兼容位置（本项目使用）
~/.copilot/skills/<名称>/SKILL.md # 用户个人全局位置
```

### 🔄 三层渐进加载（Progressive Disclosure）

Agent Skills 规范的核心设计是**三层渐进加载**，极大降低上下文占用：

| 层级 | 加载内容 | 时机 | Token 开销 |
|------|---------|------|-----------|
| **L1 — 目录** | `name` + `description` 元数据 | 会话启动 | ~50-100 每个 Skill |
| **L2 — 指令** | 完整 `SKILL.md` 正文 | Skill 被激活时（用户的提示词与 description 语义匹配） | 建议 <5000 |
| **L3 — 资源** | `scripts/`、`references/` 等附属文件 | Skill 显式引用时 | 按需加载 |

> 即使安装 50 个 Skill，启动开销也仅约 2500-5000 token，比传统 system prompt 节省约 **90%** 上下文。

### ⚡ 触发机制

Agent 通过用户在 Agent 选择器中主动选择触发；Skill 通过**语义匹配**自动激活——模型的 `description` 字段写得越精准，Skill 的触发就越可靠。本项目每个 Skill 的 `description` 中都详细列出了数十个中文触发关键词。

---

## 📁 文件结构

```
copilot-writing-tools/
├── agents/                                    # 🤖 自定义 Agent
│   ├── 点子王.agent.md                        #   创意写作顾问
│   ├── 批判家.agent.md                        #   严苛文稿审核专家
│   ├── 分析师.agent.md                        #   文稿结构与逻辑分析专家
│   ├── 档案员.agent.md                        #   知识库检索专家（高级用户）
│   └── 档案员.config.json                     #   档案员配置文件
│
├── skills/                                    # 🔧 Skill 包
│   ├── 中心句/           中心句提炼           ├── 摘要生成/         文章摘要生成
│   ├── 标题优化/         标题创作优化          ├── 段落重组/         段落顺序调整
│   ├── 大纲生成/         文章大纲规划          ├── 增加过渡/         过渡语句添加
│   ├── 缩减篇幅/         内容精简              ├── 扩充篇幅/         内容扩充丰富
│   ├── 合并段落/         相关段落合并          ├── 拆分段落/         长段落拆分
│   ├── 简化修辞/         修辞简化平实化        ├── 增加修辞/         修辞手法增强
│   └── convert-md-to-plaintext/   Markdown 转纯文本
│
├── local-search-mcp-server/                   # 🔌 MCP 搜索服务器（档案员依赖）
│   ├── index.js                               #   主程序（es.exe + rg 桥接）
│   └── package.json                           #   依赖配置
│
├── install                                    # 📦 一键安装脚本
├── README.md                                  # 📖 项目说明
└── CLAUDE.md                                  # 🤖 Claude Code 配置
```

---

## 🚀 快速开始

### 手动安装

用户亦可手动部署（无需网络、离线环境适用）：

- **按项目安装**：将 `agents/` 和 `skills/` 复制到项目根目录的 `.copilot/` 下，仅对当前项目生效。
- **全局安装**：将 `agents/` 和 `skills/` 复制到 `~/.copilot/` 下，对所有项目生效。

### 激活

完全重启 VS Code 窗口（或执行 **Developer: Reload Window**），Copilot 会自动扫描加载。在 Copilot Chat 中使用自然语言即可触发。

> ⚠️ Agent 和 Skill 不会在会话中自动刷新。修改了 `.agent.md` 或 `SKILL.md` 后，需要重启 VS Code / 重载窗口才能生效。

---

## 🤖 Agent 功能说明

Agent 具有独立的"人格"设定和交互风格，适合多轮对话场景，**绝不直接修改文件**。

### 💡 点子王 — 创意写作顾问

| 属性 | 说明 |
|------|------|
| 触发词 | 头脑风暴、想点子、写作思路、灵感、卡壳了 |
| 角色 | 天马行空的创意伙伴，擅长发散思维 |
| 模式 | 从零开始（无素材）/ 基于已有内容（有素材） |
| 输出 | 至少 3-5 个方向 + 灵感素材清单 |

### 🔍 批判家 — 严苛文稿审核专家

| 属性 | 说明 |
|------|------|
| 触发词 | 挑毛病、严格审核、审稿、鸡蛋里挑骨头 |
| 标准 | 出版级标准，四维度审查 |
| 维度 | 🔴 逻辑 → 🟠 文法 → 🟡 风格 → 🔵 内容 |
| 分级 | 🔴致命 / 🟠严重 / 🟡一般 / 🔵建议 |

### 📊 分析师 — 文稿结构与逻辑分析专家

| 属性 | 说明 |
|------|------|
| 触发词 | 分析结构、分析逻辑、梳理一下、结构诊断、逻辑脉络 |
| 角色 | 冷静缜密的结构解剖师，像剥洋葱一样拆解文稿层次 |
| 维度 | 语义层次拆解 → 逻辑关系梳理 → 结构诊断 → 缺失分析 |
| 输出 | 层次结构图 + 逻辑关系表 + 诊断报告 + 重构方案 |

### 📁 档案员 — 知识库检索专家

| 属性 | 说明 |
|------|------|
| 触发词 | 找资料、帮我找、查一下、库里有没有、搜文档、帮我核实 |
| 角色 | 沉稳严谨的档案管理员，自主拆词渐进搜索，锁定 3-5 篇最相关资料 |
| 工具 | es.exe（文件名搜索）+ rg/Select-String（内容搜索） |
| 输出 | 匹配段落原文 + 可点击文件链接 |
| ⚠️ 注意 | **不建议普通用户安装**，需额外配置 Everything + MCP 终端服务器，详见下方档案员配置说明 |

---

## 🔧 Skill 功能速查

所有 Skill 遵循统一的操作范围规则：**选中文本则只处理选中部分，否则处理全文**。

### ✂️ 直接修改类（确认即改）

| Skill | 触发词 | 功能 |
|-------|--------|------|
| **中心句** | 提炼中心句、归纳中心句 | 为每个段落提炼中心句并插入段首 |
| **摘要生成** | 生成摘要、写个摘要 | 在文件开头插入 100-200 字摘要 |
| **增加过渡** | 增加过渡、添加过渡句 | 在段落间添加顺承/转折/递进等过渡 |
| **缩减篇幅** | 缩减篇幅、精简内容 | 支持目标字数或比例，默认缩减 30% |
| **扩充篇幅** | 扩充篇幅、丰富内容 | 支持目标字数或比例，默认扩充 50%，可搜索素材 |
| **合并段落** | 合并段落、整合段落 | 合并主题相近的段落 |
| **拆分段落** | 拆分段落、分段 | 拆分过长或主题混杂的段落 |
| **简化修辞** | 简化修辞、平实一点 | 简化华丽修辞，更通俗易懂 |
| **增加修辞** | 增加修辞、更有文采 | 增加比喻、排比等修辞手法 |
| **Markdown转纯文本** | 转换成纯文本、去掉格式 | 移除 Markdown 标记，保留纯文本 |

### ✅ 确认后修改类（先建议，确认后改）

| Skill | 触发词 | 功能 |
|-------|--------|------|
| **标题优化** | 优化标题、改个标题 | 提供 3-5 个备选标题供选择 |
| **段落重组** | 调整段落顺序、重组段落 | 分析逻辑后提出重组方案 |
| **大纲生成** | 生成大纲、写个大纲 | 提供 2-3 种结构方案供选择 |

---

## 🔄 推荐工作流程

### 写作前（构思阶段）

```
💡 头脑风暴（点子王） → 📋 生成大纲 → ✏️ 优化标题
```

### 写作中（起草阶段）

```
💡 想点子（点子王） → 🔗 增加过渡 → 🔀 调整段落顺序 → 📎 合并段落 / ✂️ 拆分段落
```

### 写作后（审核阶段）

```
📊 结构分析（分析师） → 🔍 挑毛病（批判家） → 根据意见修改 → 🎯 提炼中心句 → 📝 生成摘要
```

### 特殊需求

```
📏 缩减篇幅 / 扩充篇幅
🎨 简化修辞 / 增加修辞
📄 转换成纯文本
```

---

## 📝 文件格式规范

本项目遵循 [Agent Skills 开放规范](https://agentskills.io/specification)。以下是本项目使用的格式子集：

### Agent 文件格式（`.agent.md`）

```yaml
---
name: agent-name
description: |
  功能描述

  **触发条件**：当用户说以下类似话语时触发：
  - "触发词1"
  - "触发词2"
tools: ['read', 'search', 'web']    # 可用工具
target: 'vscode'                      # 目标平台
---

# Agent 标题 — 副标题

## 角色设定
## 核心原则
## 工作模式
## 输出格式
## 注意事项
```

### Skill 文件格式（`SKILL.md`）

```yaml
---
name: skill-name
description: |
  功能描述

  **触发条件**：当用户说以下类似话语时触发：
  - "触发词1"
  - "触发词2"
---

# Skill 标题

## 当前角色
## 操作范围规则
## 执行方式
## 输出格式
```

---

## 💡 编写技巧

- **`description` 字段是触发关键**：多用用户可能说的实际词汇，语义越丰富触发越精准
- **善用否定触发词**：在 description 末尾加"不要用于 X 场景"可减少误触发
- **操作范围规则**：统一使用"选中了文本 VS 未选中文本"逻辑，对所有 Skill 一致
- **确认后修改**：如果操作不可逆（如重组段落），应先展示方案让用户确认
- **`tools` 声明**：Agent 如需搜索或读取文件，必须在 frontmatter 中声明 `tools`

---

## 📚 参考资源

- [GitHub Awesome Copilot](https://github.com/github/awesome-copilot) — Copilot Custom Extensions 官方资源库
- [Agent Skills 规范](https://agentskills.io/specification) — 由 Anthropic 发起的开放标准（2025.12）
- [VS Code 自定义 Agent 文档](https://code.visualstudio.com/docs/copilot/custom-agents) — 官方使用指南
- [skills.sh](https://skills.sh) — 社区 Skill 市场

---

## 🎯 使用建议

1. **自然语言优先**：直接描述需求，无需记住命令
2. **灵活选择范围**：选中部分文本可仅对特定部分操作
3. **先构思后审核**：写作前用点子王发散思维，写作后用批判家严格把关
4. **按需组合**：根据文章类型选择合适的 Skill 组合
5. **人工审核不可少**：AI 生成的修改建议应经过人工确认

---

## 📁 档案员配置说明（高级用户）

> ⚠️ **不建议普通用户安装**。档案员 Agent 需要额外的本地工具和 MCP 服务器配置，仅推荐有命令行经验且已搭建本地 Markdown 知识库的用户使用。

### 前置条件

档案员依赖以下本地工具：

| 工具 | 用途 | 安装方式 |
|------|------|---------|
| [Everything](https://www.voidtools.com/) | 文件名极速搜索（内存索引） | `winget install voidtools.Everything` 或从 [voidtools.com](https://www.voidtools.com/) 下载安装。确保 `es.exe` 在系统 PATH 中（es.exe 随 Everything 安装包提供，CLI 用法详见 Everything 主页） |
| [ripgrep](https://github.com/BurntSushi/ripgrep) | 文件内容精确搜索 | `winget install BurntSushi.ripgrep.MSVC` 或 `scoop install rg` |

可选：如未安装 rg，档案员将自动退回到 PowerShell 内置的 `Select-String`。

### MCP 服务器配置

档案员通过自定义 MCP 服务器 `local-search-mcp-server` 执行搜索命令。该服务器随本仓库提供，位于 `local-search-mcp-server/` 目录下。

**1. 安装 MCP 服务器依赖：**

```powershell
cd local-search-mcp-server
npm install
```

**2. 在 VS Code 中启用 MCP：**

打开 VS Code 设置（`Ctrl+,`），确保以下选项已开启：

```json
{
  "chat.mcp.access": true,
  "chat.mcp.autostart": true
}
```

**3. 注册 MCP 服务器：**

编辑 VS Code 用户级 MCP 配置文件 `%APPDATA%\Code\User\mcp.json`（全局生效）：

```json
{
  "servers": {
    "local-search-mcp-server": {
      "command": "node",
      "type": "stdio",
      "args": [
        "C:\\Users\\<你的用户名>\\.copilot\\local-search-mcp-server\\index.js"
      ]
    }
  }
}
```

> 如使用一键安装脚本，MCP 服务器会自动下载到 `~/.copilot/local-search-mcp-server/`，配置会自动合并到 `%APPDATA%\Code\User\mcp.json`（已有配置不丢失，原文件自动备份）。

**4. 配置知识库路径：**

编辑 `~/.copilot/agents/档案员.config.json`，将 `kbRoot` 设为你的 Markdown 文档库根目录：

```json
{
  "esPath": "es.exe",
  "kbRoot": "D:/我的知识库",
  "everythingPath": "C:\\Program Files\\Everything\\Everything.exe",
  "excludePaths": ["ByCatalog", "ByDay", "写易"]
}
```

**5. 重启 VS Code**，在 Agent 选择器中切换到「档案员」即可使用。

### 一键安装（含档案员）

安装脚本支持可选安装档案员，运行时会询问：

```powershell
irm https://raw.githubusercontent.com/mingqiaopeng/copilot-writing-tools/master/install | iex
```

根据提示选择 `y` 安装档案员，脚本将自动下载 Agent 文件、MCP 服务器及依赖，并生成 `mcp-config.json`。

---

## 📄 License

MIT License — 自由使用和修改
