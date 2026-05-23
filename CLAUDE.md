# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

中文文稿写作 Agent 工具集 — 一套为 GitHub Copilot 设计的写作辅助工具。包含 13 个 Skill（直接修改文件）和 4 个 Agent（仅提供建议），覆盖从构思到润色的完整写作流程。

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
    ├── 中心句/                      # 提炼段落中心句
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
    ├── 增加修辞/                    # 增加修辞手法
    └── convert-md-to-plaintext/     # Markdown 转纯文本
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
- 没有构建系统、测试框架或依赖管理 — 这是纯声明式配置

## Common Development Tasks

- **新增 Skill**: 在 `skills/` 下创建目录 `技能名/SKILL.md`，参考现有 SKILL.md 的 frontmatter 和章节结构
- **新增 Agent**: 在 `agents/` 下创建 `名称.agent.md`，注意需要 `tools` 和 `target` 字段，且遵循"不修改文件"原则
- **修改触发词**: 编辑 frontmatter `description` 中的 `触发条件` 列表
- **验证格式**: 检查 YAML frontmatter 分隔符 `---` 是否正确，`description` 中的缩进是否一致
