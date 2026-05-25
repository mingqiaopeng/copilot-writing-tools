# TODO

## 已知问题

### 1. Tab 键切换到文件列表首行选中仍有问题

- **现象**：Tab 从 RG 输入框切到结果列表时，首行未自动高亮（红色竖条不显示）。需要按 ↓ 再按 ↑ 才能选中第一项。列表仅有一项时完全无法选中。
- **原因**：`_populate_results` 中手动 `set_highlighted(True)` 与 `results.index = 0` 触发的 `ListView.Highlighted` 事件存在时序冲突，`@work` 线程中 reactive 消息可能延后处理，导致高亮被覆盖。

### 2. 内容匹配的截断显示仍有问题

- **现象**：命中文段截断到 60 字符后，加上 `[bold red]` 等 Rich markup 标签会使实际渲染长度超出终端一行。
- **原因**：截断在 `_build_text()` 中对原始 snippet 执行，后续 `_highlight_snippet` 插入 markup 标签导致渲染宽度增加。
- **方向**：在 `_highlight_snippet` 内部截断，或截断时预留 markup 标签空间。
