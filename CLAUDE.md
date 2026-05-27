# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

中文文稿写作 Agent 工具集 — 一套为 GitHub Copilot 设计的写作辅助工具。包含 15 个 Skill（直接修改文件）和 4 个 Agent（仅提供建议），覆盖从构思到润色的完整写作流程。

## Architecture

### File Structure

```
.copilot/
├── agents/                          # Agent 定义（人格化，多轮对话，不修改文件）
│   ├── 点子王.agent.md              # 创意写作顾问（头脑风暴）
│   ├── 批判家.agent.md              # 严苛文稿审核专家
│   ├── 分析师.agent.md              # 文稿结构与逻辑分析专家
│   ├── 档案员.agent.md              # 知识库检索专家（高级用户）
│   └── 档案员.config.json           # 档案员配置文件
└── skills/                          # Skill 定义（单次任务，直接修改文件）
    ├── 写中心句/                    # 提炼段落中心句
    ├── 摘要生成/                    # 生成文章摘要
    ├── 标题优化/                    # 优化文章标题（确认后修改）
    ├── 段落重组/                    # 调整段落顺序（确认后修改）
    ├── 大纲生成/                    # 生成文章大纲（确认后修改）
    ├── 增加过渡/                    # 添加过渡语句
    ├── 缩减篇幅/                    # 精简文章内容
    ├── 扩充篇幅/                    # 丰富文章内容
    ├── 合并段落/                    # 合并相关段落
    ├── 拆分段落/                    # 拆分过长段落
    ├── 简化修辞/                    # 简化华丽修辞
    ├── 神来之笔/                    # 库驱动的金句嵌入
    ├── 增加修辞/                    # 增加修辞手法
    ├── 去除标签/                    # 去除Markdown标签
    └── 校对勘误/                    # 按勘误表逐条修改
```

### Key Distinctions

- **Agent vs Skill**: Agent 有独立人格设定，支持多轮对话，**绝不修改文件**；Skill 是单次任务，**直接或确认后修改文件**。
- **Frontmatter pattern**: 每个文件以 YAML frontmatter（`name` / `description` / 触发条件）开头，后接 Markdown 正文。
- **Agent frontmatter** 额外包含 `tools` 和 `target` 字段，声明可用工具和目标平台（vscode）。

### Skill Pattern (SKILL.md)

所有 SKILL.md 遵循统一结构：
1. YAML frontmatter `name` / `description`（含触发条件关键词）
2. `当前角色` — 角色定义
3. `操作范围规则` — 选中文本 vs 全文的逻辑
4. `执行方式` — 步骤序列
5. `输出格式` — 固定的汇报格式

### Agent Pattern (.agent.md)

所有 .agent.md 遵循统一结构：
1. YAML frontmatter（含 `tools` 和 `target`）
2. `角色设定` — 人格描述
3. `核心原则` — 行为约束（关键：不修改文件）
4. `工作模式` — 按场景区分的操作流程
5. `输出格式` — 固定的汇报格式
6. `注意事项` — 边界情况处理

## Key Conventions

- **操作范围规则**：选中文本则只操作选中部分，否则操作全文（所有 skill 和 agent 一致）
- **标题优化 / 段落重组 / 大纲生成** 等待用户确认后再修改文件（其他 skill 直接修改）
- 所有文件名和内容均为中文
- Skill 名称即目录名，与 frontmatter `name` 一致
- 大部分为纯声明式配置，无构建系统或测试框架。`local-search-mcp-server/` 为 Node.js 项目，有 `package.json` 依赖（`npm install` 安装）

### Skill 触发词设计原则

- **避免高频通用词**：如"修改"、"检查"在日常对话中出现频率过高，会误触发。触发词应精准、特化，与 Skill 核心行为强关联（如"按勘误表修改"而非"帮我改"）
- **宁缺毋滥**：触发词数量控制在 6 个左右即可，不做关键词堆砌

### Skill↔Agent 解耦

- SKILL.md 中引用 Agent 时，统一用「其他 Agent」，不点名具体 Agent 名称
- 避免产生"是不是有个叫 X 的 Agent"的歧义，保持 Skill 和 Agent 相互独立

### Agent↔Skill 互推机制

- 每个 Agent 的「注意事项」末尾应包含 Skill 推荐逻辑：根据诊断结果，主动推荐可用的 Skill
- 形成「诊断 → 推荐 → 修改」闭环
- 新增 Agent 或 Skill 时，需同步检查相关 Agent 的推荐列表是否需要更新

### 勘误表规范（批判家 → 校对勘误）

- 勘误表位于审核报告末尾（总体结论之后），为「校对勘误」Skill 的唯一输入源
- 格式：`| # | 行号 | 原表述 | 更正表述 | 等级 |`，四列缺一不可
- **强制铁律**：输出勘误表前必须逐条核实行号与原文完全一致，不得有偏差
- 批判家输出末尾附带触发提示语：「按勘误表修改」

### 校对勘误 Skill 的上下文回溯机制

- 不通过参数接收勘误表，而是回溯对话历史，定位最近的勘误表
- 按行号升序排列后逐条执行，避免行号偏移
- 若对话中无勘误表，告知用户而非自行发挥

### README 表格规范

- README 中表格统一使用 HTML `<table width="100%">` + 百分比列宽，保持视觉一致性
- 提示区块使用 GitHub Alerts 格式（`[!NOTE]` / `[!TIP]` / `[!WARNING]`）

## Common Development Tasks

- **新增 Skill**: 在 `skills/` 下创建目录 `技能名/SKILL.md`，参考现有 SKILL.md 的 frontmatter 和章节结构
- **新增 Agent**: 在 `agents/` 下创建 `名称.agent.md`，注意需要 `tools` 和 `target` 字段，且遵循"不修改文件"原则
- **修改触发词**: 编辑 frontmatter `description` 中的 `触发条件` 列表
- **验证格式**: 检查 YAML frontmatter 分隔符 `---` 是否正确，`description` 中的缩进是否一致
- **新增 Agent↔Skill 互推**：新增 Skill 后，检查是否有 Agent 应在诊断后推荐该 Skill，更新对应 Agent 的「注意事项」推荐列表；新增 Agent 后，检查其诊断结果能否关联现有 Skill，加入推荐逻辑
