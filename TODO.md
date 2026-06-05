# TODO：Continue 端 .prompt 输出语义重构

## 背景

Continue.dev 支持 **Edit 模式**——模型输出特定格式的修改块（search/replace、diff），Continue 自动 Apply 到文件。这个模式不依赖模型的 function calling 能力，千问等本地模型也能用。

当前 `.continue/prompts/` 下的文件是从 Copilot SKILL.md 直译的，指令是"用 edit 工具直接修改文件"——这在 Copilot Chat 里管用（Copilot 提供内置编辑工具），但在 Continue + 本地模型环境下失败了：

- 本地模型没有 tool-calling → 收到"改文件"指令后手足无措，输出"已修改"然后停止，或试图输出全文中途断掉

## 重构目标

把所有 `.prompt` 文件的输出语义从"直接修改文件"改为"输出 Continue Edit 格式的修改块"：

- Continue 识别 `<<<<<<< ORIGINAL` / `=======` / `>>>>>>> UPDATED` 格式的 diff 块
- Continue 识别 ```` ``` ```` 代码块 + 文件路径的替换格式
- 用户点击 **Apply** 按钮，修改自动应用到文件

## 文件分类

### A 类：只输出局部内容（4 个）

模型只输出中心句/金句/摘要/过渡句，标注插入位置，**不输出全文**。

| # | 文件 | 当前问题 | 重构方向 |
|---|------|---------|---------|
| A1 | `xie-zhongxin-ju.prompt` | "已直接修改文件" | 输出各段落中心句列表，标注插入位置（"段X开头：……"），末尾输出一个 diff 块供 Apply |
| A2 | `shenlai-zhibi.prompt` | "用edit工具插入" | 输出选定句子 + 插入位置，末尾输出差异块 |
| A3 | `zhaiyao-shengcheng.prompt` | "用edit工具在文件开头插入" | 输出摘要文本，末尾输出文件开头插入 diff 块 |
| A4 | `zengjia-guodu.prompt` | "直接在文件中插入" | 输出过渡句列表 + 段落间位置标注，末尾输出 diff 块 |

### B 类：输出完整修改后文本（11 个）

模型输出修改后的**完整文本**（放在代码块中），Continue Apply 整个替换。

| # | 文件 | 当前问题 | 重构方向 |
|---|------|---------|---------|
| B1 | `chaifen-duanluo.prompt` | "直接修改文件" | 输出修改后全文，代码块包裹 |
| B2 | `hebing-duanluo.prompt` | "直接修改文件" | 同上 |
| B3 | `kuochong-pianfu.prompt` | "直接修改文件" | 同上 |
| B4 | `suojian-pianfu.prompt` | "直接修改文件" | 同上 |
| B5 | `jianhua-xiuci.prompt` | "直接修改文件" | 同上 |
| B6 | `zengjia-xiuci.prompt` | "已直接修改文件" | 同上 |
| B7 | `youhua-jushi.prompt` | "已直接修改文件" | 同上 |
| B8 | `quchu-biaoqian.prompt` | "直接修改文件，以纯文本覆盖" | 同上 |
| B9 | `tongyi-fengge.prompt` | "直接修改文件" | 同上 |
| B10 | `jiaodui-kanwu.prompt` | "已直接修改文件" | 同上 |
| B11 | `biaoti-youhua.prompt` | 标题建议，原为"确认后修改" | 输出标题建议，用户确认后输出修改块 |

### C 类：无需修改文件（3 个）

纯分析/建议输出，天然兼容 Continue。

| # | 文件 | 说明 |
|---|------|------|
| C1 | `lianghua-fenxi.prompt` | 量化分析报告，只输出分析结果 JSON + 对话展示 |
| C2 | `dagang-shengcheng.prompt` | 大纲生成，原为"确认后修改"，输出大纲供确认 |
| C3 | `duanluo-chongzu.prompt` | 段落重组，原为"确认后修改"，输出方案供确认 |
| C4 | `chuanda-tigang.prompt` | 传达提纲，结构化提取，不修改文件 |

## 重构步骤

### 第一步：确认 Continue Edit 格式

验证 Continue 本地模型环境下支持的 Apply 格式：

1. 在 Continue 中用本地模型做一次简单修改测试
2. 确认它能识别哪种 diff/替换格式（search-replace 块 vs 完整文件替换块）
3. 选定一种格式作为所有 prompt 的统一输出规范

### 第二步：A 类（局部输出）逐个重构

每个文件：
1. 删除"用 edit 工具"、"直接修改文件"等字眼
2. 改为"输出修改块，格式如下：`<<<<<<< ORIGINAL...`（或 Continue 实际支持的格式）"
3. 只输出差异块，不输出全文
4. `{{selectedCode}}` 模板变量保留（Continue 注入选中文本）
5. 测试：用户选中一段文字 → /A1 → 模型输出中心句 + diff 块 → 用户 Apply

### 第三步：B 类（全文输出）逐个重构

每个文件：
1. 删除"直接修改文件"字眼
2. 改为"在代码块中输出修改后的完整文本，Continue 会自动识别为可 Apply 的编辑"
3. 用 ` ``` ` 代码块包裹完整输出
4. 保留 `{{selectedCode}}` 模板变量
5. 测试：用户选中全文 → /B1 → 模型输出完整修改文本 → 用户 Apply

### 第四步：统一模板

所有 `.prompt` 文件末尾统一加一段"输出规范"，明确：
- 修改内容必须放在 Continue 可识别的编辑块中
- 局部修改用差异块
- 全文修改用完整代码块

### 第五步：回归验证

用千问 35B 逐一测试全部 18 个 `/` 命令，确认：
- 模型不再出现"停止输出"现象
- Apply 按钮可正常出现
- Apply 后的内容正确

## 依赖

- Continue.dev 版本需支持 Edit/Apply 功能（当前最新版已支持）
- 模型无需 tool-calling 能力，只需能理解并输出指定格式的文本块
