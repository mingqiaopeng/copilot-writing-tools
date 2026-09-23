# ima.copilot Skill 中 Python 脚本使用指南

## 一、是否支持 Python 脚本

支持。Skill 的 `scripts/` 目录专门用于放置可执行脚本，Python 和 Bash 均可。以 `ima-knowledge` 技能为例，`scripts/upload_file.py` 是一个 20KB 的 Python 脚本，封装了完整的文件上传逻辑。

Agent 通过 `shell` 工具调用脚本：

```bash
python3 /sandbox/workspace/skills/ima-knowledge/scripts/upload_file.py --file xxx
```

## 二、运行环境：本地沙盒

脚本在**本地 Linux 沙盒**（`/sandbox/workspace/`）中执行，不是云端。

| 项目 | 版本/信息 |
|:---|:---|
| Python | 3.12.13 |
| pip | 26.1.1 |
| OS | Linux |

执行时工作目录为 `/sandbox/workspace/`，可读写 workspace 下的文件，与 Agent 其他操作（`file_read`、`file_write`、`shell`）共享同一个文件系统。

## 三、依赖处理

### 3.1 预装包

沙盒已预装 `requests`、`aiohttp`、`beautifulsoup4`、`bokeh`、`cloudpathlib`、`certifi`、`numpy`、`scipy`、`pandas` 等数十个常用库，大部分需求无需额外安装。

### 3.2 额外依赖的处理方式

| 方式 | 适用场景 | 做法 |
|:---|:---|:---|
| 纯标准库 | 数据处理、文件转换、格式校验等 | 无需操作，直接用。初始化模板本身就是纯标准库实现 |
| 需要第三方包 | 需要特殊库（如 `openpyxl`、`PyPDF2` 等） | 脚本首次被调用前，Agent 执行 `pip3 install <package>` 安装 |

在 SKILL.md 中声明依赖的写法：

```markdown
## 依赖安装

首次使用前，执行：

pip3 install openpyxl PyPDF2 -q
```

### 3.3 pip 可用性

```bash
pip3 install requests  # 正常执行
pip3 install --dry-run requests  # 已安装包可直接确认
```

## 四、scripts/ 与直接 shell 命令的选择

| | `scripts/` 中的脚本 | 让 Agent 直接写 shell 命令 |
|:---|:---|:---|
| 确定性、重复性任务 | ✅ 写一次，反复调用 | ❌ 每次重写 |
| 长逻辑（>50 行） | ✅ 独立文件，清晰可维护 | ❌ 挤在 shell 参数里易出错 |
| 调试和迭代 | ✅ 修改文件后重新注册 | ❌ 每次手动重输 |
| 简单一次性操作（<20 行） | ❌ 过度工程化 | ✅ 直接敲命令即可 |

**建议**：任务逻辑超过 20 行或需要重复使用，放 `scripts/`；临时性、几行的操作，在 SKILL.md 工作流中让 Agent 用 `shell` 执行即可。

## 五、关键路径规则

### 5.1 部署路径

IMA 通过 ZIP 上传注册技能后，技能目录被部署到：
```
/sandbox/workspace/skills/<skill-name>/
```

**不是** `/sandbox/workspace/ima/`，也不是工作区下的任意自定义目录。SKILL.md 中所有脚本路径必须使用此部署路径。

### 5.2 脚本路径写法

SKILL.md 中调用脚本的命令必须为：
```bash
python3 /sandbox/workspace/skills/<skill-name>/scripts/<script>.py [参数]
```

错误示例（会导致"路径不存在"错误）：
```bash
python3 /sandbox/workspace/ima/<skill-name>/scripts/<script>.py  # ❌ ima/ 不存在
python3 /sandbox/workspace/<skill-name>/scripts/<script>.py     # ❌ 缺少 skills/
```

### 5.3 脚本自包含

每个技能的脚本必须放在技能自身的 `scripts/` 目录下，随 ZIP 一起打包。IMA **不支持**跨技能共享脚本路径。多个技能共用同一脚本（如 `analyze.py`）时，必须复制到每个技能的 `scripts/` 目录中。

```bash
# ✅ 正确：每个脚本在自身技能目录下
/sandbox/workspace/skills/quantitative-analysis/scripts/analyze.py
/sandbox/workspace/skills/length-reducer/scripts/analyze.py

# ❌ 错误：试图引用其他技能的路径
/sandbox/workspace/skills/quantitative-analysis/scripts/analyze.py  # length-reducer 不能引用这条路径
/sandbox/workspace/ima/shared/scripts/analyze.py                    # ❌ 共享目录不存在
```

### 5.4 可执行权限

Agent 调用脚本时需确保文件可执行：

```bash
chmod +x /sandbox/workspace/skills/<skill-name>/scripts/<script>.py
```

初始化脚本生成的示例文件默认已设置可执行权限。

### 5.2 路径处理

脚本运行时工作目录为 `/sandbox/workspace/`，建议使用绝对路径或在脚本中基于 `__file__` 定位自身目录：

```python
import os
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
```

### 5.3 参数传递

脚本应支持命令行参数，通过 `argparse` 或 `sys.argv` 接收 Agent 传入的参数：

```bash
python3 /sandbox/workspace/skills/<skill-name>/scripts/<script>.py --input /path/to/file --output /path/to/result
```

### 5.4 返回码和输出

脚本执行结果通过退出码和 stdout/stderr 返回给 Agent。Agent 通过 `shell` 工具获取执行结果判断成功与否，因此脚本应对错误情况设置非零退出码并输出清晰的错误信息。

## 六、完整示例

以 `init_skill.py` 模板生成的 `scripts/example.py` 为起点：

```python
#!/usr/bin/env python3

import sys
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(description="示例脚本")
    parser.add_argument("--input", required=True, help="输入文件路径")
    parser.add_argument("--output", default="result.txt", help="输出文件路径")
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误：输入文件不存在 - {input_path}", file=sys.stderr)
        sys.exit(1)

    # 实际处理逻辑
    content = input_path.read_text(encoding="utf-8")
    result = content.upper()

    output_path = Path(args.output)
    output_path.write_text(result, encoding="utf-8")
    print(f"处理完成：{output_path}")

if __name__ == "__main__":
    main()
```

Agent 调用方式：

```bash
python3 /sandbox/workspace/skills/<skill-name>/scripts/example.py --input /sandbox/workspace/input.txt --output /sandbox/workspace/output.txt
```

---

*基于 ima.copilot 沙盒环境 45.11.26 验证。Python 3.12.13，pip 26.1.1。*
