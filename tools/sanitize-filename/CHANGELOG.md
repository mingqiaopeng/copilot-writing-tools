# Changelog

## [1.5.2] - 2026-06-08

### Fixed
- 修复状态栏点击多次后失效的 bug：`processedFiles` 缓存不再拦截手动触发（`manual`）和保存触发（`save`），仅对自动触发（打开/新建）生效

## [1.5.1] - 2026-06-08

### Changed
- 默认模式从 `prompt`（弹窗询问）改为 `warn`（仅提醒），配合状态栏一键规范化，不打断工作流

## [1.5.0] - 2026-06-08

### Added
- **状态栏智能感知**：根据当前活动文件名实时显示状态
  - 含特殊字符 → $(error) 红色 X 图标 + "规范文件名"，点击一键规范化
  - 文件名规范 → $(pass) 绿色对勾 + "文件名规范"
  - 切换编辑器标签时自动刷新
- **中英文菜单适配**：右键菜单/命令面板标题支持 VS Code 界面语言自动切换
  - 新增 `package.nls.json`（英文）和 `package.nls.zh-cn.json`（中文）
  - 中文环境显示"规范化当前文件名"，英文环境显示"Sanitize Current Filename"

### Changed
- 状态栏不再显示模式切换按钮（Auto/Prompt/Warn），改为显示当前文件状态
- 模式切换（`toggleAutoMode`）仅在命令面板中可用

## [1.4.1] - 2026-06-07

### Added
- 诊断日志：`sanitizeFilename` 和 `handleFile` 中添加 `console.log`，可在 VS Code Developer Tools 中查看检测过程

### Fixed
- 降级 fallback 正则补全中文弯引号 `""''`

## [1.4.0] - 2026-06-07

### Added
- **重命名后自动切换标签页**：重命名成功后，自动关闭指向旧文件名的标签页，并打开新文件。解决"文件改了但编辑器还开着旧路径"的混乱体验
- 仅在文件原本已在编辑器中打开时才切换（从资源管理器右键触发的重命名不会额外打开文件）

## [1.3.2] - 2026-06-07

### Fixed
- 文件资源管理器右键菜单不显示：修正 `when` 条件为 `resourceScheme == file`
- 保存后检测不再受 `processedFiles` 缓存限制（每次保存都检查）
- 新增编辑器内右键菜单（`editor/context`）

## [1.3.0] - 2026-06-07

### Changed
- **简化保存检测逻辑**：不再在保存前（`onWillSaveTextDocument`）拦截检测，改为保存后（`onDidSaveTextDocument`）检测文件名——用户正常保存，保存完成后若文件名含特殊字符则提示规范化，流程更自然不打断
- 默认识别字符增加中文弯引号 `""`（U+201C/D）和 `''`（U+2018/9）

## [1.2.1] - 2026-06-07

### Changed
- 默认替换规则增加中文弯引号 `""`（U+201C/D）和 `''`（U+2018/9），这些字符同样导致 Copilot 编辑工具路径问题

## [1.2.0] - 2026-06-07

### Added
- `sanitizeOnCreate` 配置项：新建文件时通过 FileSystemWatcher 自动检测
- 状态栏显示当前模式（Auto/Warn/Prompt）
- 批量处理支持取消操作

### Fixed
- 修复 `warn` 模式下重命名操作未被正确等待的异步 bug
- 改进 `scanWorkspace` 排除模式，直接传递给 `findFiles` 提升性能
- 重命名失败时区分权限错误 (EPERM/EACCES) 和文件占用 (EBUSY)，给出针对性提示
- 添加 `pendingChecks` 防止并发重复检测
- 停用时清理全局缓存

## [1.1.0] - 2026-06-07

### Changed
- `checkOnSave` 默认值改为 `true`，保存文件时自动检测
- 添加 `.vscodeignore` 优化打包体积
- 添加 `build.sh` 一键打包脚本

## [1.0.0] - 2026-06-07

### Added
- 初始版本发布
- 自动检测文件名中的特殊字符
- 三种处理模式：自动/提示/警告
- 右键菜单支持
- 批量扫描和规范化
- 状态栏快捷按钮
- 可配置的正则替换规则
