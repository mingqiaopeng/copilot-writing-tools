<h1 align="center">✍️ 中文文稿写作 Agent 工具集</h1>

<p align="center">
  <strong>专为现代中文非虚构严肃文稿写作设计的 AI 辅助工具链——从头脑风暴到最终校阅，一站式覆盖完整写作流程。</strong><br />
  <em>4 个 Agent · 14 个 Skill · 基于 GitHub Copilot Agent Skills 开放规范 · 本地优先 · 自然语言驱动</em>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow" alt="License: MIT" /></a>
  <a href="https://github.com/mingqiaopeng/copilot-writing-tools/releases"><img src="https://img.shields.io/badge/Release-v0.1.0-2ea44f" alt="Release v0.1.0" /></a>
  <a href="https://agentskills.io/specification"><img src="https://img.shields.io/badge/Spec-Agent_Skills-purple" alt="Agent Skills Spec" /></a>
  <a href="https://code.visualstudio.com/"><img src="https://img.shields.io/badge/Platform-VS_Code-blue" alt="VS Code" /></a>
  <a href="https://github.com/features/copilot"><img src="https://img.shields.io/badge/Runs_on-GitHub_Copilot-24292e" alt="GitHub Copilot" /></a>
  <a href="https://www.deepseek.com/"><img src="https://img.shields.io/badge/推荐模型-DeepSeek_V4-0066cc" alt="DeepSeek V4" /></a>
</p>

<p align="center">
  <img src="assets/Big_4_Agent.png" alt="四大Agent — 点子王 · 批判家 · 分析师 · 档案员" width="800" />
</p>

---

> [!NOTE]
> **前置条件**：安装 [VS Code](https://code.visualstudio.com/) 并启用 [GitHub Copilot](https://github.com/features/copilot) 订阅。Agent 与 Skill 通过语义匹配自动触发。
>
> 💡 **推荐配置**：建议将 GitHub Copilot 连接至 **DeepSeek V4** 模型，中文写作体验更佳。

### ⚡ 一行命令安装

```powershell
irm https://raw.githubusercontent.com/mingqiaopeng/copilot-writing-tools/master/install | iex
```

打开 PowerShell 粘贴回车即可。Agent 与 Skill 自动部署到 `~/.copilot/`，**对所有项目全局生效**。重启 VS Code 后即可使用。

> [!TIP]
> 亦可手动将仓库中的 `agents/` 和 `skills/` 目录复制到项目根目录的 `.copilot/` 下（仅当前项目），或复制到 `~/.copilot/`（全局生效）。

---

## 🌏 行业背景与设计理念

### 中文 AI 辅助写作：探索与尝试

2024-2026 年，中文 AI 写作工具进入爆发期。秘塔写作猫、通义千问、火山写作、笔灵 AI 等产品相继涌现，大模型中文生成能力持续提升。

本项目聚焦于一个特定领域：**现代中文非虚构严肃文稿的 AI 辅助写作**——包括但不限于学术论文、技术文档、商业报告、政策分析、深度评论、知识科普等以逻辑论证和信息传递为核心的长文类型。这类文稿以逻辑严密、论据可靠、结构清晰为首要标准，与网文小说、营销文案、社交媒体内容有本质区别。

在此领域，深入使用后暴露出的不是"写得不够快"，而是更深层的质量问题。概括起来，六大痛点尤为突出：

**1. "AI 味儿"挥之不去**

AI 生成的文字有一种难以忽视的"腔调"：过度使用"在……的背景下""随着……的发展""不仅……而且……"等句式；形容词堆砌（"深刻而全面的""积极有效的"）；每段结尾习惯性升华。读者几段就能闻出"AI 味"——这不是语法问题，是一种渗透在遣词造句中的不自然感。对于追求严谨克制的非虚构严肃写作，这种腔调是致命的。

**2. "新八股"文风泛滥**

AI 生成的文本高度趋同——排比起手 → "首先/其次/最后" → "综上所述"收尾，结构可预测、修辞空洞。大量用户遭遇此类问题，媒体称之为"新八股"体。

**3. 长文章逻辑断裂**

篇幅突破 2000 字后，段落间逻辑一致性急剧下降。论据跳跃、前后矛盾的频率随篇幅线性增长，长篇非虚构写作仍需大量人工干预。

**4. 结构化诊断缺失**

现有工具擅长"续写"和"改写"——给定一段文字，生成更多文字。但它们无法回答：文章的层次结构是否合理？论证是否严密？分类是否互斥？用户只能凭感觉判断"好不好"，没有工具能系统性地诊断文稿结构。

**5. 知识库利用不足**

写作者通常积累了大量的本地笔记、参考材料和历史文稿，但现有 AI 工具无法利用这些私有知识库——要么需要手动上传，要么只能依赖模型训练数据中的通用知识。写作者自己的积累派不上用场。

**6. 工作流割裂分散**

构思用 A 工具，起草用 B 工具，审核用 C 工具——每个环节切换平台，上下文丢失。市面上没有一个工具覆盖从头脑风暴到最终定稿的完整链路。

### 现有方案对比

| 类型 | 代表产品 | 优势 | 短板 |
|------|---------|------|------|
| Web 写作助手 | 秘塔写作猫、笔灵 AI | 模板丰富、开箱即用 | 独立网页，无法嵌入编辑器；擅长改写而非原创 |
| 大模型对话 | 通义千问、文心一言 | 通用能力强、超长上下文 | 无结构化写作流程；输出质量依赖 prompt 技巧 |
| 办公插件 | 火龙果 Pitaya、火山写作 | 嵌入 Word/WPS，校对便捷 | 聚焦润色和校阅，缺乏构思和结构分析能力 |
| AI 小说工具 | novel-writer、InkOS | 长文本管线成熟，多 Agent 协作 | 面向网文小说，非虚构文稿场景不适用 |
| Copilot 扩展 | awesome-copilot 社区 | Agent Skills 开放规范，175+ Agent | **尚无任何中文写作 Agent/Skill** |

### 本项目的设计思路

**"不造新平台，打造写作 IDE。"**

软件开发者有 IDE——编码、调试、测试、部署一站式完成。写作者却没有类似的一体化平台：构思在浏览器里，起草在 Word 里，审核靠人工来回批注。本项目选择 VS Code + GitHub Copilot 这个组合，正是要填补这个空缺——为严肃写作者提供一个"写作 IDE"。核心考量：

1. **一体化平台**：VS Code 的文件管理、编辑器、终端、扩展市场、Git 集成，加上 Copilot Chat 的 AI 对话面板，天然构成了写作工作台的全部要素。构思、起草、修改、审核、版本管理，不切换软件。

2. **最流行的文本编辑器**：全球市场占有率第一，中文支持完善，启动快、性能优良，社区活跃、插件生态丰富。

3. **零费用可用**：GitHub Copilot 免费额度足以覆盖轻度到中度使用，无需额外订阅任何付费 AI 服务。

4. **支持本地模型与离线部署**：可接入本地大模型和私有算力，在内网环境中不联网运行，满足对数据安全有严格要求的写作场景。

**技术栈选择：**

| 层面 | 选择 | 理由 |
|------|------|------|
| 平台 | VS Code + GitHub Copilot Chat | 全球最大的代码/文本编辑器，Copilot Chat 作为 AI 交互入口 |
| 规范 | Agent Skills 开放规范（`SKILL.md` + `.agent.md`） | 三层渐进加载，14 个 Skill 启动仅需约 1400-2800 token |
| 触发 | 语义匹配 | 用户说人话，模型自动匹配 Skill，无需记命令 |
| 搜索 | Everything (es.exe) + ripgrep | 纯本地、零延迟的文件名与内容搜索，无需向量数据库 |

**Agent↔Skill 分离设计：**

- **Agent**（4 个）：有独立人格，多轮对话，**只诊断不修改**——负责头脑风暴、结构分析、文稿审核、知识库检索
- **Skill**（14 个）：单次任务，**确认或直接修改文件**——负责中心句提炼、段落重组、校对勘误等具体操作
- **互推机制**：Agent 完成诊断后主动推荐可用 Skill，形成"诊断→修改"闭环

**核心优势：**

1. **全流程覆盖**：从头脑风暴到最终校对，14 个 Skill 覆盖写作每个环节，无需切换工具
2. **结构化诊断**：分析师 Agent 对中文文稿做分层结构诊断和逻辑关系梳理——市面上独一无二的能力
3. **出版级审核**：批判家 Agent 按 🔴致命/🟠严重/🟡一般/🔵建议 四级标准审核，输出可直接执行的勘误表
4. **本地优先**：所有操作在你的文件中完成，数据不出本地。档案员搜索基于本地 Everything 索引和 ripgrep，无需上传文档
5. **极低上下文开销**：基于三层渐进加载，14 个 Skill 的启动开销约 1400-2800 token，比传统方案节省约 90%
6. **自然语言驱动**：无需学习命令——"帮我审一下""想几个方向""段落太多了拆一下"——说人话就能触发

---

## 🚀 快速开始

### 安装

**一键安装（推荐）：**

```powershell
irm https://raw.githubusercontent.com/mingqiaopeng/copilot-writing-tools/master/install | iex
```

**手动安装（离线环境适用）：**

- **按项目安装**：将仓库中的 `agents/` 和 `skills/` 目录复制到项目根目录的 `.copilot/` 下，仅对当前项目生效。
- **全局安装**：复制到 `~/.copilot/` 下，对所有项目生效。

### 激活

完全重启 VS Code（或执行 **Developer: Reload Window**），Copilot 自动扫描加载。

### 首次使用

1. 打开任意 Markdown 文件
2. 在 Copilot Chat 中用自然语言描述需求，例如：
   - 「帮我生成一份关于 XXX 的大纲」
   - 「帮我审一下这篇文章，挑挑毛病」
   - 「帮我想几个写作方向」
3. 对应的 Skill 或 Agent 自动触发

> [!WARNING]
> 修改 `.agent.md` 或 `SKILL.md` 后需重启 VS Code 才能生效。

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
| 特色 | 输出结构化勘误表，可由「校对勘误」Skill 一键批量执行 |

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

### 🔗 Agent↔Skill 互推

每个 Agent 在完成分析或审核后，会根据诊断结果**主动推荐**可用的 Skill。Agent 负责诊断、Skill 负责修改——各司其职又无缝衔接：

| Agent | 诊断场景 | 推荐 Skill |
|-------|---------|-----------|
| 批判家 | 输出勘误表 | 校对勘误（一键批量修改） |
| 批判家 | 段落顺序问题 | 段落重组 |
| 批判家 | 段落衔接生硬 | 增加过渡 |
| 分析师 | 段落顺序不合理 | 段落重组 |
| 分析师 | 结构缺失需重建 | 大纲生成 |
| 分析师 | 段落过长或主题混杂 | 拆分段落 |
| 点子王 | 确定写作方向后 | 大纲生成 |
| 点子王 | 草稿需丰富 | 扩充篇幅 |

---

## 🔧 Skill 功能速查

所有 Skill 遵循统一的操作范围规则：**选中文本则只处理选中部分，否则处理全文**。

### ✂️ 直接修改（无需确认）

| Skill | 触发词 | 功能 |
|-------|--------|------|
| **写中心句** | 写中心句、提炼中心句、归纳中心句 | 为每个段落提炼中心句并插入段首 |
| **摘要生成** | 生成摘要、写个摘要 | 在文件开头插入 100-200 字摘要 |
| **增加过渡** | 增加过渡、添加过渡句 | 在段落间添加顺承/转折/递进等过渡 |
| **缩减篇幅** | 缩减篇幅、精简内容 | 支持目标字数或比例，默认缩减 30% |
| **扩充篇幅** | 扩充篇幅、丰富内容 | 支持目标字数或比例，默认扩充 50%，可搜索素材 |
| **合并段落** | 合并段落、整合段落 | 合并主题相近的段落 |
| **拆分段落** | 拆分段落、分段 | 拆分过长或主题混杂的段落 |
| **简化修辞** | 简化修辞、平实一点 | 简化华丽修辞，更通俗易懂 |
| **增加修辞** | 增加修辞、更有文采 | 增加比喻、排比等修辞手法 |
| **去除标签** | 去除标签、转换成纯文本、去掉格式 | 移除 Markdown 标记，保留纯文本 |
| **校对勘误** | 按勘误表修改、执行勘误、应用勘误 | 从上下文回溯勘误表，逐条定位替换错字错词 |

### ✅ 确认后修改（先建议，确认后改）

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
✏️ 扩充篇幅 / 增加修辞 → 🔗 增加过渡 → 📎 合并段落 / ✂️ 拆分段落 → 🔀 调整段落顺序
```

### 写作后（审核阶段）

```
📊 结构分析（分析师） → 🔍 挑毛病（批判家） → 📋 校对勘误 → 🎯 写中心句 → 📝 生成摘要
```

### 专项调整

```
📏 缩减篇幅 / 扩充篇幅
🎨 简化修辞 / 增加修辞
📄 转换成纯文本（去除标签）
```

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
│   ├── 写中心句/                              #   提炼段落中心句
│   ├── 摘要生成/                              #   文章摘要生成
│   ├── 标题优化/                              #   标题创作优化
│   ├── 段落重组/                              #   段落顺序调整
│   ├── 大纲生成/                              #   文章大纲规划
│   ├── 增加过渡/                              #   过渡语句添加
│   ├── 缩减篇幅/                              #   内容精简
│   ├── 扩充篇幅/                              #   内容扩充丰富
│   ├── 合并段落/                              #   相关段落合并
│   ├── 拆分段落/                              #   长段落拆分
│   ├── 简化修辞/                              #   修辞简化平实化
│   ├── 增加修辞/                              #   修辞手法增强
│   ├── 去除标签/                              #   去除Markdown标签
│   └── 校对勘误/                              #   按勘误表逐条修改
│
├── local-search-mcp-server/                   # 🔌 MCP 搜索服务器（档案员依赖）
│   ├── index.js                               #   主程序（es.exe + rg 桥接）
│   └── package.json                           #   依赖配置
│
├── install                                    # 📦 一键安装脚本
├── README.md                                  # 📖 项目说明
└── CLAUDE.md                                  # 🤖 Claude Code 配置
```

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
4. **善用互推机制**：Agent 完成分析后会推荐合适的 Skill，顺着推荐走即可
5. **人工审核不可少**：AI 生成的修改建议应经过人工确认

---

## 📁 档案员配置说明（高级用户）

> [!WARNING]
> **不建议普通用户安装**。档案员 Agent 需要额外的本地工具和 MCP 服务器配置，仅推荐有命令行经验且已搭建本地 Markdown 知识库的用户使用。

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

根据提示选择 `y` 安装档案员，脚本将自动下载 Agent 文件、MCP 服务器及依赖，并自动配置 MCP。

---

## 📚 技术参考

### 🧠 工作机制：Copilot 如何发现 Agent 和 Skill

GitHub Copilot Custom Extensions 通过扫描项目目录中的特定文件夹来发现自定义 Agent 和 Skill。

#### Agent 与 Skill 的区别

| 维度 | 🤖 Custom Agent | 🔧 Skill |
|------|----------------|----------|
| 文件格式 | `.agent.md` | `SKILL.md` |
| 交互方式 | 多轮对话，有独立人格 | 单次任务，即用即走 |
| 修改文件 | ❌ 从不修改 | ✅ 直接或确认后修改 |
| 加载机制 | 在 Agent 选择器中可见 | 通过语义匹配触发 |
| 适用场景 | 头脑风暴、审核等需要来回讨论的场景 | 写中心句、生成摘要等明确操作 |

#### 📂 目录扫描机制

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

#### 🔄 三层渐进加载（Progressive Disclosure）

Agent Skills 规范的核心设计是**三层渐进加载**，极大降低上下文占用：

| 层级 | 加载内容 | 时机 | Token 开销 |
|------|---------|------|-----------|
| **L1 — 目录** | `name` + `description` 元数据 | 会话启动 | ~50-100 每个 Skill |
| **L2 — 指令** | 完整 `SKILL.md` 正文 | Skill 被激活时（用户的提示词与 description 语义匹配） | 建议 <5000 |
| **L3 — 资源** | `scripts/`、`references/` 等附属文件 | Skill 显式引用时 | 按需加载 |

> 即使安装 50 个 Skill，启动开销也仅约 2500-5000 token，比传统 system prompt 节省约 **90%** 上下文。

#### ⚡ 触发机制

Agent 通过用户在 Agent 选择器中主动选择触发；Skill 通过**语义匹配**自动激活——`description` 字段写得越精准，Skill 的触发就越可靠。本项目每个 Skill 的 `description` 中都详细列出了数十个中文触发关键词。

### 📝 文件格式规范

本项目遵循 [Agent Skills 开放规范](https://agentskills.io/specification)。以下是本项目使用的格式子集：

#### Agent 文件格式（`.agent.md`）

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

#### Skill 文件格式（`SKILL.md`）

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

### 💡 编写技巧

- **`description` 字段是触发关键**：多用用户可能说的实际词汇，语义越丰富触发越精准
- **善用否定触发词**：在 description 末尾加"不要用于 X 场景"可减少误触发
- **操作范围规则**：统一使用"选中了文本 VS 未选中文本"逻辑，对所有 Skill 一致
- **确认后修改**：如果操作不可逆（如重组段落），应先展示方案让用户确认
- **`tools` 声明**：Agent 如需搜索或读取文件，必须在 frontmatter 中声明 `tools`

---

## 📄 License

MIT License — 自由使用和修改
