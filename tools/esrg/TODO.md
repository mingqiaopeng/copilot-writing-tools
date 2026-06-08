# TODO

## 已修复

### 1. Tab 键切换到文件列表首行选中问题 — 已修复

- **原因**：`results.clear()` 不重置 `ListView._index`，导致 `results.index = 0` 为 no-op 不触发 `Highlighted` 事件，手动 `set_highlighted` 被后续 DOM 重绘覆盖。
- **修复**：在 `_populate_results` 中先设 `_index = None` 再设 `index = 0`，确保 `Highlighted` 事件可靠触发。

### 2. 内容匹配截断关键词丢失 — 已修复

- **原因**：`snip[:57] + "..."` 简单截断可能把匹配关键词截掉。
- **修复**：新增 `_truncate_around_match()`，以第一个匹配位置为中心取左右各 20/37 字符，确保关键词始终可见。

---

## 待实现

### 3. 打包为独立 .exe（不依赖 Python / rg.exe）

**目标**：用户无需安装 Python 或 ripgrep，下载单个 .exe（或 zip）即可运行 esrg。

**依赖分析**：

| 组件 | 类型 | 捆绑方案 |
|------|------|---------|
| Python 3.10+ 解释器 | 运行时 | PyInstaller `--onefile` 打包进 .exe |
| textual >= 0.52 | pip 包 | PyInstaller 自动收集 |
| rg.exe (~5 MB) | 独立二进制 | `--add-binary` 嵌入 .exe，运行时解压到临时目录 |
| es.exe (~1 MB) | Everything CLI | `--add-binary` 嵌入 .exe（Everything 服务仍需用户安装） |

**实施步骤**：

1. **安装 PyInstaller**
   ```bash
   pip install pyinstaller
   ```

2. **下载 rg.exe 和 es.exe 到项目目录**
   - rg.exe: https://github.com/BurntSushi/ripgrep/releases（Windows x86_64）
   - es.exe: 从已安装的 Everything 目录复制，或从 https://www.voidtools.com/downloads/ 下载 ES-1.1.0.x.zip

3. **修改 `config.py`**，新增捆绑二进制检测逻辑：
   - `_get_bundled_path(name)` — 检测 PyInstaller `sys._MEIPASS` 临时目录
   - 若捆绑二进制存在 → 自动使用
   - 若不存在 → 回退到用户配置的路径 → 再回退到 PATH 中的命令
   - `esPath` / `rgPath` 默认值改为自动检测结果

4. **打包命令**（在 `tools/esrg/` 下执行）：
   ```bash
   pyinstaller --onefile \
       --name esrg \
       --add-binary "rg.exe;." \
       --add-binary "es.exe;." \
       --hidden-import textual \
       --collect-all textual \
       esrg/__main__.py
   ```

5. **Everything 未安装时的引导**：
   - 启动时检测 Everything 服务是否可用（`es.exe` 返回码）
   - 若不可用 → 显示安装引导弹窗/终端提示：
     ```
     Everything 搜索服务未安装。
     
     下载页面: https://www.voidtools.com/downloads/
     或使用 winget 一键安装:
       winget install voidtools.Everything
     
     安装后请确保 Everything 服务正在运行（系统托盘可见图标）。
     ```
   - 引导后可降级为纯 rg 模式（仅内容搜索，无文件名索引）

6. **测试与发布**：
   - 在未安装 Python 的 Windows 虚拟机中测试
   - 打包为 `esrg-v1.x.x.zip`，内含 `esrg.exe`
   - 作为 GitHub Release asset 发布

**预期产物**：`esrg.exe` 约 20-30 MB，zip 后约 15-20 MB。
