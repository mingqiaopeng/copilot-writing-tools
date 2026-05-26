# TODO

## 已修复

### 1. Tab 键切换到文件列表首行选中问题 — 已修复

- **原因**：`results.clear()` 不重置 `ListView._index`，导致 `results.index = 0` 为 no-op 不触发 `Highlighted` 事件，手动 `set_highlighted` 被后续 DOM 重绘覆盖。
- **修复**：在 `_populate_results` 中先设 `_index = None` 再设 `index = 0`，确保 `Highlighted` 事件可靠触发。

### 2. 内容匹配截断关键词丢失 — 已修复

- **原因**：`snip[:57] + "..."` 简单截断可能把匹配关键词截掉。
- **修复**：新增 `_truncate_around_match()`，以第一个匹配位置为中心取左右各 20/37 字符，确保关键词始终可见。
