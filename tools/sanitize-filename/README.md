# Sanitize Filename

自动检测并规范化包含特殊字符的文件名，解决 GitHub Copilot 等工具因文件名特殊字符导致的编辑失效问题。

## 功能特性

- ✅ **自动检测**：打开文件时自动检测文件名是否包含特殊字符
- ✅ **保存检测**：保存文件时自动检测（默认开启）
- ✅ **新建检测**：通过 FileSystemWatcher 在文件创建时自动检测（默认开启）
- ✅ **状态栏指示**：状态栏实时显示当前模式（Auto/Warn/Prompt）
- ✅ **多种模式**：支持自动/提示/警告三种处理模式，可一键切换
- ✅ **右键菜单**：在文件资源管理器和编辑器标签右键中一键规范化
- ✅ **批量处理**：一键扫描并规范化整个工作区中的问题文件名
- ✅ **高度可配置**：自定义替换规则、字符、忽略路径等
- ✅ **智能提示**：避免重复弹窗打扰，已忽略的文件不再提示

## 安装

### 方式一：安装 .vsix（推荐）

1. 下载 `sanitize-filename-1.1.0.vsix`
2. VS Code: `Extensions` → `...` → `Install from VSIX...`
3. 选择文件，安装完成

### 方式二：从源码构建

```bash
# 方式 A：使用 build.sh 一键打包
chmod +x build.sh
./build.sh

# 方式 B：手动步骤
cd sanitize-filename
npm install
npm run compile
vsce package --no-dependencies --allow-missing-repository
```

## 使用方法

### 1. 自动检测（打开/保存后/新建文件时）

默认配置下，当你打开文件、保存文件后，或新建文件时，若文件名包含特殊字符，扩展会自动弹出提示：

```
检测到文件名包含特殊字符

当前: "my file(1).txt"
建议: "my_file_1.txt"

[是，重命名] [否，保留原样] [始终自动处理]
```

### 2. 手动触发

- **文件资源管理器**：右键点击文件 → "Sanitize Current Filename"
- **编辑器标签**：右键点击标签 → "Sanitize Current Filename"
- **命令面板**：`Ctrl+Shift+P` → "Sanitize Filename: Sanitize Current Filename"
- **状态栏**：点击右下角 "Sanitize" 按钮

### 3. 批量处理

`Ctrl+Shift+P` → "Sanitize Filename: Sanitize All Filenames in Workspace"

### 4. 切换模式

`Ctrl+Shift+P` → "Sanitize Filename: Toggle Auto Sanitize Mode"

## 配置选项

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `sanitizeFilename.mode` | string | `prompt` | `auto`/`prompt`/`warn` |
| `sanitizeFilename.pattern` | string | `["'(){}[\]#&!@$%^*+=~\`<>?\|\s""'']` | 匹配特殊字符的正则（含中文弯引号） |
| `sanitizeFilename.replacement` | string | `_` | 替换字符 |
| `sanitizeFilename.trimEdges` | boolean | `true` | 去除首尾下划线/连字符 |
| `sanitizeFilename.collapseConsecutive` | boolean | `true` | 合并连续特殊字符 |
| `sanitizeFilename.preserveExtension` | boolean | `true` | 保留文件扩展名 |
| `sanitizeFilename.checkOnOpen` | boolean | `true` | 打开文件时检测 |
| `sanitizeFilename.checkOnSave` | boolean | `true` | 保存后自动检测文件名 |
| `sanitizeFilename.sanitizeOnCreate` | boolean | `true` | 新建文件时检测 |
| `sanitizeFilename.ignoredPatterns` | array | `["node_modules", ".git", ".vscode"]` | 忽略的路径模式 |

## 默认替换规则

以下特殊字符会被替换为 `_`：

| 字符 | 替换后 | 说明 |
|------|--------|------|
| `"` `'` | `_` | 半角引号（导致 Copilot 问题的元凶） |
| `"` `"` `'` `'` | `_` | 中文弯引号（同样导致路径问题） |
| `(` `)` `[` `]` `{` `}` | `_` | 括号 |
| `#` `&` `!` `@` `$` `%` `^` `*` `+` `=` `~` `` ` `` `<` `>` `?` `\|` | `_` | 其他特殊符号 |
| 空格 | `_` | 空格 |

### 示例

| 原始文件名 | 规范化后 |
|-----------|---------|
| `my"file.txt` | `my_file.txt` |
| `test(1).js` | `test_1.js` |
| `data[2024].csv` | `data_2024.csv` |
| `hello world.md` | `hello_world.md` |
| `a___b.txt` | `a_b.txt` |
| `_file_.txt` | `file.txt` |

## 许可证

MIT
