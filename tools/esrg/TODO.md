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
| rg.exe (~5 MB) | 独立二进制 | 首次运行时从 .exe 内解压安装到 `%LOCALAPPDATA%\esrg\bin\` |
| es.exe (~1 MB) | Everything CLI | 同上，安装到同一系统目录（Everything 服务仍需用户安装） |

**安装目录设计**：
- Windows: `%LOCALAPPDATA%\esrg\bin\` （`C:\Users\<user>\AppData\Local\esrg\bin\`）
- Linux/macOS: `~/.esrg/bin/`
- 该目录加入 `config.json` 默认路径，持久保留，不受系统临时清理影响
- 用户也可手动将 `rg.exe` / `es.exe` 放入该目录供 esrg 使用

**实施步骤**：

1. **安装 PyInstaller**
   ```bash
   pip install pyinstaller
   ```

2. **下载 rg.exe 和 es.exe 到项目目录**（用于打包时嵌入）
   - rg.exe: https://github.com/BurntSushi/ripgrep/releases（Windows x86_64, `ripgrep-*-x86_64-pc-windows-msvc.zip`）
   - es.exe: 从已安装的 Everything 目录复制，或从 https://www.voidtools.com/downloads/ 下载 ES-1.1.0.x.zip
   - 放入 `tools/esrg/bins/` 目录（gitignore 忽略）

3. **修改 `config.py`**，默认路径指向系统安装目录：
   - Windows 默认: `%LOCALAPPDATA%\esrg\bin\es.exe` / `rg.exe`
   - Linux/macOS 默认: `~/.esrg/bin/es` / `rg`
   - 检测逻辑：系统目录有就用 → 用户配置覆盖 → PATH 回退
   - `DEFAULT_CONFIG` 中 `esPath` / `rgPath` 改为系统目录路径

4. **新增首次运行安装逻辑**（`__main__.py` 或单独模块）：
   - 检测 `%LOCALAPPDATA%\esrg\bin\` 下是否存在 `rg.exe` / `es.exe`
   - 若缺失 → 从 PyInstaller `sys._MEIPASS` 中复制到系统目录
   - 若 `sys._MEIPASS` 不可用（非 PyInstaller 环境）→ 跳过，使用 PATH 回退
   - 安装完成后更新 `config.json` 中的路径

5. **打包命令**（在 `tools/esrg/` 下执行）：
   ```bash
   pyinstaller --onefile \
       --name esrg \
       --add-binary "bins/rg.exe;bins" \
       --add-binary "bins/es.exe;bins" \
       --hidden-import textual \
       --collect-all textual \
       esrg/__main__.py
   ```
   - `--add-binary` 将 rg.exe/es.exe 嵌入 .exe（位于 `sys._MEIPASS/bins/`）
   - 首次运行时复制到 `%LOCALAPPDATA%\esrg\bin\`，之后直接从系统目录调用
   - 不会每次解压到临时目录，持久保留

5. **Everything 未安装时的引导**：
   - 启动时检测 Everything 服务是否可用（`es.exe` 返回码）
   - 若不可用 → 显示安装引导弹窗/终端提示：
     ```
     Everything 搜索服务未安装。
     
     推荐安装 Everything 1.5 Alpha（支持深色模式、属性索引）:
     
     winget 一键安装:
       winget install --id=voidtools.Everything.Alpha -e
     
     手动下载页面:
       https://www.voidtools.com/forum/viewtopic.php?f=12&t=9787
     
     Everything 安装并运行后，系统托盘可见放大镜图标即表示服务正常。
     ```
   - 引导后可降级为纯 rg 模式（仅内容搜索，无文件名索引）

6. **测试与发布**：
   - 在未安装 Python 的 Windows 虚拟机中测试
   - 打包为 `esrg-v1.x.x.zip`，内含 `esrg.exe`
   - 作为 GitHub Release asset 发布

**预期产物**：`esrg.exe` 约 20-30 MB，zip 后约 15-20 MB。
