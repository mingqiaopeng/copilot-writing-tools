"""Textual TUI app for esrg — Claude Code-like search interface."""

import base64
import re
import subprocess
from pathlib import Path

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal
from textual.screen import Screen
from textual.widgets import Input, Label, ListItem, ListView, Static

MAX_DISPLAY = 50
MODE_C_FILE_LIMIT = 200
DEBOUNCE_S = 0.25


# ---------------------------------------------------------------------------
# Result item
# ---------------------------------------------------------------------------


class ResultItem(ListItem):
    """A single file result in the list."""

    def __init__(self, filepath: str, match_count: int = 0, snippet: str = "", pattern: str = "") -> None:
        self.filepath = filepath
        self.match_count = match_count
        self.snippet = snippet
        self.pattern = pattern
        self._highlighted = False
        self._label: Label | None = None
        super().__init__()

    def compose(self) -> ComposeResult:
        self._label = Label(self._build_text())
        yield self._label

    def set_highlighted(self, highlighted: bool) -> None:
        if self._highlighted == highlighted:
            return
        self._highlighted = highlighted
        if self._label is not None:
            self._label.update(self._build_text())

    def _build_text(self) -> str:
        fname = Path(self.filepath).name
        dname = str(Path(self.filepath).parent)
        if self._highlighted:
            g1 = g2 = g3 = "red"
        else:
            g1 = g2 = g3 = "dim"
        text = f"[{g1}]│[/] [cyan]{fname}[/]"
        if self.match_count > 0:
            text += f" [dim]({self.match_count} 处匹配)[/]"
        text += f"\n[{g2}]│[/] [dim]{dname}[/]"
        if self.snippet:
            raw = self.snippet.strip()
            if len(raw) > 60:
                if self.pattern:
                    raw = self._truncate_around_match(raw, self.pattern, 60)
                else:
                    raw = raw[:57] + "..."
            text += f"\n[{g3}]│[/] {self._highlight_snippet(raw, self.pattern)}"
        return text

    @staticmethod
    def _escape_markup(text: str) -> str:
        return text.replace("[", "\\[")

    @staticmethod
    def _highlight_snippet(snippet: str, pattern: str) -> str:
        """Wrap regex matches in [bold red], non-matches in [dim]."""
        if not pattern:
            return f"[dim]{ResultItem._escape_markup(snippet)}[/]"
        try:
            regex = re.compile(pattern, re.IGNORECASE)
        except re.error:
            return f"[dim]{ResultItem._escape_markup(snippet)}[/]"
        parts = []
        last_end = 0
        for m in regex.finditer(snippet):
            if m.start() > last_end:
                parts.append(f"[dim]{ResultItem._escape_markup(snippet[last_end:m.start()])}[/]")
            parts.append(f"[bold red]{ResultItem._escape_markup(snippet[m.start():m.end()])}[/]")
            last_end = m.end()
        if last_end < len(snippet):
            parts.append(f"[dim]{ResultItem._escape_markup(snippet[last_end:])}[/]")
        return "".join(parts)

    @staticmethod
    def _truncate_around_match(text: str, pattern: str, max_len: int = 60) -> str:
        """截断到 max_len，但确保第一个匹配关键词完整可见。"""
        if len(text) <= max_len:
            return text
        try:
            m = re.search(pattern, text, re.IGNORECASE)
        except re.error:
            return text[: max_len - 3] + "..."
        if not m:
            return text[: max_len - 3] + "..."
        CONTEXT = 20
        avail = max_len - 3  # 留给 "…" 标记
        start = max(0, m.start() - CONTEXT)
        end = min(len(text), start + avail)
        if end < m.end():
            end = min(len(text), m.end() + (avail // 4))
            start = max(0, end - avail)
        result = ""
        if start > 0:
            result += "…"
        result += text[start:end]
        if end < len(text):
            result += "…"
        return result


# ---------------------------------------------------------------------------
# Help screen
# ---------------------------------------------------------------------------


HELP_TEXT = """\
ES (Everything) 搜索语法
───────────────────────────────────────────
  [cyan]反腐 廉政[/]       AND —— 同时匹配所有词
  [cyan]反腐 | 廉政[/]     OR —— 匹配任一词
  [cyan]!2019[/]           NOT —— 排除含 "2019" 的文件
  [cyan]<a | b> c[/]       分组 —— (a OR b) AND c
  [cyan]\"精确短语\"[/]       精确短语匹配

RG (ripgrep) 搜索语法
───────────────────────────────────────────
  [cyan]反腐[/]             字面文本搜索
  [cyan]反腐|廉政[/]        正则 OR
  [cyan]\\b词边界\\b[/]       单词边界
  [cyan]^开头[/]            行首匹配
  [cyan]结尾$[/]            行尾匹配

快捷键
───────────────────────────────────────────
  [cyan]Tab[/]              切换焦点：ES → RG → 结果列表
  [cyan]↑ ↓ j k[/]          浏览结果
  [cyan]Enter[/]            复制文件路径到剪贴板
  [cyan]Esc[/]              回到输入框 / 退出
  [cyan]Ctrl+Q[/]           退出
  [cyan]Ctrl+H[/]           帮助（本屏）

[dim]按 Esc 关闭[/]"""


class HelpScreen(Screen):
    """Help overlay showing search syntax and keyboard shortcuts."""

    BINDINGS = [Binding("escape", "dismiss", "关闭", show=True)]

    def compose(self) -> ComposeResult:
        yield Static(HELP_TEXT, id="help-content")

    def action_dismiss(self) -> None:
        self.app.pop_screen()

    CSS = """
    HelpScreen {
        align: center middle;
    }
    #help-content {
        padding: 2 4;
        border: solid $accent;
        max-width: 60;
    }
    """


# ---------------------------------------------------------------------------
# Main search screen
# ---------------------------------------------------------------------------


class SearchScreen(Screen):
    """Main search interface — Claude Code-like layout."""

    CSS = """
    Screen, Container, Horizontal, Static, Label, ListView, ListItem, Input {
        background: transparent;
        text-style: none;
    }

    Screen {
        layout: grid;
        grid-rows: auto auto 1fr;
    }

    #input-row {
        height: 1;
        padding: 0 1;
    }

    #es-label {
        width: auto;
        height: 1;
        padding: 0 1 0 0;
        content-align: left middle;
        color: $text-muted;
    }

    #rg-label {
        width: auto;
        height: 1;
        padding: 0 1;
        content-align: left middle;
        color: $text-muted;
    }

    #es-input {
        width: 6fr;
        height: 1;
        border: none;
        padding: 0;
    }

    #es-input:focus {
        border: none;
    }

    #rg-input {
        width: 4fr;
        height: 1;
        border: none;
        padding: 0;
    }

    #rg-input:focus {
        border: none;
    }

    #status {
        height: 1;
        padding: 0 1;
    }

    #results-area {
        height: 1fr;
        scrollbar-size: 0 0;
    }

    #results {
        height: 1fr;
        scrollbar-size: 0 0;
    }

    #results > ListItem {
        padding: 0 1;
    }

    #results ListItem.--highlight {
        text-style: bold;
    }

    #placeholder {
        height: 1fr;
    }
    """

    BINDINGS = [
        Binding("escape", "escape_action", "返回/退出", show=True),
        Binding("tab", "focus_next_field", "下一栏", show=True),
        Binding("ctrl+h", "show_help", "帮助", show=True),
        Binding("ctrl+q", "quit", "退出", show=True),
    ]

    _debounce_timer = None
    _last_highlighted: ResultItem | None = None

    def __init__(self, config: dict, total_md_count: int = 0) -> None:
        super().__init__()
        self.cfg = config
        self.total_md_count = total_md_count

    def compose(self) -> ComposeResult:
        with Horizontal(id="input-row"):
            yield Label("❯ File:", id="es-label")
            yield Input(
                placeholder="文件名关键词...",
                id="es-input",
            )
            yield Label("│ Content:", id="rg-label")
            yield Input(
                placeholder="内容关键词...",
                id="rg-input",
            )
        yield Static("就绪", id="status")
        with Container(id="results-area"):
            yield Static("", id="placeholder")
            yield ListView(id="results")

    def on_mount(self) -> None:
        self.query_one("#es-input", Input).focus()
        self.query_one("#results", ListView).display = False

    # ------------------------------------------------------------------
    # Focus cycling
    # ------------------------------------------------------------------

    def action_focus_next_field(self) -> None:
        focused = self.focused
        if focused is None:
            self.set_focus(self.query_one("#es-input", Input))
            return
        fid = focused.id if hasattr(focused, "id") else ""
        if fid == "es-input":
            self.set_focus(self.query_one("#rg-input", Input))
        elif fid == "rg-input":
            results = self.query_one("#results", ListView)
            if results.display and results.children:
                results.index = 0
                self.set_focus(results)
            else:
                self.set_focus(self.query_one("#es-input", Input))
        elif isinstance(focused, (ListView, ListItem)):
            self.set_focus(self.query_one("#es-input", Input))
        else:
            self.set_focus(self.query_one("#es-input", Input))

    def action_escape_action(self) -> None:
        focused = self.focused
        if focused is not None and isinstance(focused, (ListView, ListItem)):
            self.query_one("#es-input", Input).focus()
        else:
            self.app.exit()

    def action_show_help(self) -> None:
        self.app.push_screen(HelpScreen())

    # ------------------------------------------------------------------
    # Debounce + search dispatch
    # ------------------------------------------------------------------

    def on_input_changed(self, event: Input.Changed) -> None:
        if self._debounce_timer is not None:
            self._debounce_timer.reset()
        else:
            self._debounce_timer = self.set_timer(DEBOUNCE_S, self._trigger_search)

    def _trigger_search(self) -> None:
        self._debounce_timer = None
        self._do_search()

    @work(exclusive=True)
    async def _do_search(self) -> None:
        from .engine import (
            search_filenames,
            search_content_global,
            search_content_in_files_batch,
            search_combined_es,
        )

        es_path = self.cfg["esPath"]
        rg_path = self.cfg["rgPath"]
        kb_root = self.cfg["kbRoot"]
        exclude = self.cfg.get("excludePaths", [])

        es_text = self.query_one("#es-input", Input).value.strip()
        rg_text = self.query_one("#rg-input", Input).value.strip()

        results = self.query_one("#results", ListView)
        placeholder = self.query_one("#placeholder", Static)
        status = self.query_one("#status", Static)

        if not es_text and not rg_text:
            results.clear()
            placeholder.display = True
            results.display = False
            status.update("就绪")
            return

        placeholder.display = False
        results.display = True
        status.update("搜索中...")

        if es_text and not rg_text:
            # Mode A: filename search only
            files = await search_filenames(es_path, kb_root, es_text, exclude)
            self._populate_results(results, files, pattern=rg_text)
            if not files:
                status.update("[red]未找到匹配文件，换个关键词试试[/]")
            elif len(files) > MAX_DISPLAY:
                status.update(
                    f"[yellow]显示前 {MAX_DISPLAY} 条（共 {len(files)} 条）"
                    f"—— 请增加关键词缩小范围[/]"
                )
            else:
                status.update(f"[green]找到 {len(files)} 个文件[/]")

        elif rg_text and not es_text:
            # Mode B: global content search
            files, method = await search_content_global(
                es_path,
                rg_path,
                kb_root,
                rg_text,
                exclude,
                content_search_enabled=self.cfg.get(
                    "ES_ContentSearchEnabled", False
                ),
                total_md_count=self.total_md_count,
            )
            if method == "blocked":
                self._populate_results(results, [], pattern=rg_text)
                status.update(
                    f"[yellow]ES_ContentSearchEnabled 未开启且知识库有 "
                    f"{self.total_md_count} 个 md 文件（上限 200），"
                    f"请先输入文件名关键词缩小范围[/]"
                )
                return
            if method == "es_no_match":
                self._populate_results(results, [], pattern=rg_text)
                status.update(
                    "[yellow]Everything 内容搜索无匹配结果。"
                    "若期望有匹配，请检查 Everything 中是否已启用内容索引"
                    "（工具 → 选项 → 内容）[/]"
                )
                return
            self._populate_results(results, files, pattern=rg_text)
            method_label = (
                "Everything 内容索引" if method == "es" else "rg 递归"
            )
            if not files:
                status.update("[red]未找到匹配文件，换个关键词试试[/]")
            elif len(files) > MAX_DISPLAY:
                status.update(
                    f"[yellow]显示前 {MAX_DISPLAY} 条（共 {len(files)} 条，"
                    f"通过 {method_label}）—— 请缩小范围[/]"
                )
            else:
                status.update(
                    f"[green]找到 {len(files)} 个文件[/]（通过 {method_label}）"
                )

        else:
            # Mode C: both — ES narrows, RG filters within
            content_search_enabled = self.cfg.get("ES_ContentSearchEnabled", False)

            if content_search_enabled:
                # ES 内容索引已启用：一次 ES 查询搞定文件名+内容条件
                files, method = await search_combined_es(
                    es_path, kb_root, es_text, rg_text, exclude
                )
                if method == "es_no_match":
                    self._populate_results(results, [], pattern=rg_text)
                    status.update(
                        "[yellow]合并搜索无匹配结果，换一组关键词试试[/]"
                    )
                    return
                self._populate_results(results, files, pattern=rg_text)
                if not files:
                    status.update("[red]未找到匹配文件，换个关键词试试[/]")
                elif len(files) > MAX_DISPLAY:
                    status.update(
                        f"[yellow]显示前 {MAX_DISPLAY} 条（共 {len(files)} 条）—— 请缩小范围[/]"
                    )
                else:
                    status.update(f"[green]找到 {len(files)} 个文件[/]（通过 Everything 内容索引）")
                return

            # ES 内容索引未开启：两步走（ES 文件名缩小范围 → rg 内容过滤）
            files = await search_filenames(es_path, kb_root, es_text, exclude)

            if not files:
                self._populate_results(results, [], pattern=rg_text)
                status.update(
                    "[red]文件名未匹配到文件，换一组关键词试试[/]"
                )
                return

            if len(files) > MODE_C_FILE_LIMIT:
                self._populate_results(results, [], pattern=rg_text)
                status.update(
                    f"[yellow]文件名命中 {len(files)} 个文件，太多，"
                    f"请先增加文件名关键词缩小范围[/]"
                )
                return

            status.update(f"文件名匹配到 {len(files)} 个文件，正在搜索内容...")
            matches = await search_content_in_files_batch(rg_path, files, rg_text)

            if not matches:
                self._populate_results(results, [], pattern=rg_text)
                status.update(
                    f"[red]{len(files)} 个文件中均不包含「{rg_text}」，"
                    f"换个内容关键词试试[/]"
                )
                return

            match_list = list(matches.keys())
            self._populate_results(results, match_list, matches, pattern=rg_text)
            total = len(files)
            hit = len(matches)
            if len(match_list) > MAX_DISPLAY:
                status.update(
                    f"[yellow]显示前 {MAX_DISPLAY} 条匹配"
                    f"（共 {total} 个文件中 {hit} 个命中）—— 请缩小范围[/]"
                )
            else:
                status.update(
                    f"[green]{total} 个文件中 {hit} 个匹配[/]"
                )

    # ------------------------------------------------------------------
    # Populate ListView
    # ------------------------------------------------------------------

    @staticmethod
    def _first_snippet(match_text: str) -> str:
        """Extract the first match line."""
        for line in match_text.splitlines():
            stripped = line.strip()
            if stripped:
                return stripped
        return ""

    def _populate_results(
        self,
        results: ListView,
        files: list[str],
        matches: dict[str, str] | None = None,
        pattern: str = "",
    ) -> None:
        self._last_highlighted = None
        results.clear()
        capped = files[:MAX_DISPLAY]
        for fp in capped:
            mc = 0
            snippet = ""
            if matches and fp in matches:
                match_text = matches[fp]
                mc = len(match_text.splitlines())
                snippet = self._first_snippet(match_text)
            results.mount(ResultItem(fp, match_count=mc, snippet=snippet, pattern=pattern))
        if capped:
            # 延迟到 mount 渲染完成后设置高亮，避免 @work 协程中的时序冲突
            self.set_timer(0, self._highlight_first_result)

    def _highlight_first_result(self) -> None:
        """DOM 就绪后将高亮设到第一个结果。"""
        results = self.query_one("#results", ListView)
        if not results.children:
            return
        # 复位 _index 以确保 index=0 触发 Highlighted 事件
        results._index = None
        results.index = 0
        # 单条目时 ListView 可能不触发 Highlighted，手动确保视觉高亮
        first = results.children[0]
        if isinstance(first, ResultItem):
            if self._last_highlighted is not None and self._last_highlighted is not first:
                self._last_highlighted.set_highlighted(False)
            first.set_highlighted(True)
            self._last_highlighted = first

    # ------------------------------------------------------------------
    # Enter on result → copy path to clipboard
    # ------------------------------------------------------------------

    def on_list_view_highlighted(self, event: ListView.Highlighted) -> None:
        if self._last_highlighted is not None:
            self._last_highlighted.set_highlighted(False)
        if isinstance(event.item, ResultItem):
            event.item.set_highlighted(True)
            self._last_highlighted = event.item

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if isinstance(event.item, ResultItem):
            self._copy_to_clipboard(event.item.filepath)
            self.query_one("#status", Static).update(
                f"[green]已复制：[/] {event.item.filepath}"
            )

    @staticmethod
    def _copy_to_clipboard(text: str) -> None:
        """Copy text to Windows clipboard via PowerShell (UTF-16 native)."""
        try:
            b64 = base64.b64encode(text.encode("utf-16-le")).decode("ascii")
            cmd = (
                "$d=[System.Convert]::FromBase64String('"
                + b64
                + "');Set-Clipboard -Value ([System.Text.Encoding]::Unicode.GetString($d))"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                check=False,
                timeout=5,
            )
        except Exception:
            pass


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------


class SearchApp(App):
    """esrg — knowledge base search TUI."""

    def __init__(self, config: dict, total_md_count: int = 0) -> None:
        super().__init__()
        self._config = config
        self._total_md_count = total_md_count
        self.ansi_color = True

    def on_mount(self) -> None:
        self.push_screen(SearchScreen(self._config, self._total_md_count))
