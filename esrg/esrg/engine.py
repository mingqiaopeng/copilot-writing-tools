"""Search engine: wraps es.exe (Everything) and rg (ripgrep) as async subprocess calls.

Ported from local-search-mcp-server/index.js spawnRun / deduplicate / ensureEverything.
"""

import asyncio
import json
import re
import shlex
import subprocess
import sys

# ---------------------------------------------------------------------------
# spawn_run — run a child process, capture output, decode with given encoding
# ---------------------------------------------------------------------------

MAX_BUF = 10 * 1024 * 1024
CMD_NOT_FOUND_RE = re.compile(
    r"not recognized|not found|command not found|ENOENT", re.IGNORECASE
)


def _spawn_sync(exe: str, args: list[str], encoding: str = "gbk", timeout: int = 30):
    """Synchronous spawn – meant to be called via asyncio.to_thread()."""
    try:
        result = subprocess.run(
            [exe, *args],
            capture_output=True,
            timeout=timeout,
        )
        text = _decode_output(result.stdout, result.stderr, encoding)
        return text, result.returncode
    except FileNotFoundError:
        return f"Command not found: {exe}", 127
    except subprocess.TimeoutExpired:
        return "(Search timed out)", 1


def _decode_output(stdout: bytes, stderr: bytes, preferred: str) -> str:
    """Decode subprocess output. Tries utf-8 first, then preferred (gbk), then utf-8 with replace."""
    for enc in ("utf-8", preferred):
        try:
            out = stdout.decode(enc)
            if stderr:
                err = stderr.decode(enc)
                return (out or err).strip()
            return out.strip()
        except UnicodeDecodeError:
            continue
    # Last resort
    out = stdout.decode("utf-8", errors="replace").strip()
    return out or stderr.decode("utf-8", errors="replace").strip()


async def spawn_run(
    exe: str, args: list[str], encoding: str = "gbk", timeout: int = 30
):
    """Async wrapper around _spawn_sync."""
    return await asyncio.to_thread(_spawn_sync, exe, args, encoding, timeout)


def is_command_not_found(text: str, exit_code: int) -> bool:
    return exit_code == 127 or bool(CMD_NOT_FOUND_RE.search(text))


# ---------------------------------------------------------------------------
# deduplicate — port of MCP server deduplicate()
# ---------------------------------------------------------------------------


def deduplicate(raw_output: str, exclude_paths: list[str]) -> list[str]:
    if not raw_output or not raw_output.strip():
        return []

    lines = [s.strip() for s in raw_output.splitlines() if s.strip()]

    if exclude_paths:
        escaped = [re.escape(p) for p in exclude_paths]
        pattern = "|".join(f"[\\\\/]{p}[\\\\/]" for p in escaped)
        exclude_re = re.compile(pattern)
        filtered = [line for line in lines if not exclude_re.search(line)]
    else:
        filtered = lines[:]

    # Numeric-fingerprint dedup: strip all digits; first path wins
    seen: dict[str, str] = {}
    for path in filtered:
        fingerprint = re.sub(r"\d+", "", path)
        if fingerprint not in seen:
            seen[fingerprint] = path

    return list(seen.values())


# ---------------------------------------------------------------------------
# Everything lifecycle — auto-start Everything.exe if not running
# ---------------------------------------------------------------------------

_everything_ensured = False
_everything_ready = False
_md_count_cache: int | None = None
RG_GLOBAL_LIMIT = 200


async def count_md_files(es_path: str, kb_root: str) -> int:
    """Count total *.md files under kbRoot via es.exe. Cached after first call."""
    global _md_count_cache
    if _md_count_cache is not None:
        return _md_count_cache
    text, code = await spawn_run(
        es_path, ["ext:md", "-path", kb_root], encoding="gbk"
    )
    if code == 0 and text:
        _md_count_cache = len([s for s in text.splitlines() if s.strip()])
    else:
        _md_count_cache = 0
    return _md_count_cache


async def ensure_everything(
    es_path: str, kb_root: str, everything_path: str
) -> bool:
    global _everything_ensured, _everything_ready

    if _everything_ensured:
        return _everything_ready
    _everything_ensured = True

    if sys.platform != "win32":
        _everything_ready = True
        return True

    # Try to launch Everything tray app (detached, fire-and-forget)
    try_paths = list(
        dict.fromkeys(
            [
                everything_path,
                "Everything.exe",
                "C:\\Program Files\\Everything\\Everything.exe",
                "C:\\Program Files (x86)\\Everything\\Everything.exe",
            ]
        )
    )

    launched = False
    for ep in try_paths:
        if not ep:
            continue
        try:
            subprocess.Popen(
                [ep, "-startup"],
                creationflags=subprocess.DETACHED_PROCESS
                | subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdin=subprocess.DEVNULL,
            )
            launched = True
            break
        except (FileNotFoundError, OSError):
            continue

    if launched:
        await asyncio.sleep(3)

    # Smoke test: run es.exe with minimal query to verify IPC is alive
    text, code = await spawn_run(
        es_path, ["ext:md", "-n", "1", "-path", kb_root], encoding="gbk"
    )
    if code == 0:
        _everything_ready = True
        return True

    return False


# ---------------------------------------------------------------------------
# Three search modes
# ---------------------------------------------------------------------------


async def search_filenames(
    es_path: str, kb_root: str, keywords: str, exclude_paths: list[str]
) -> list[str]:
    """Mode A: ES filename search. shlex.split preserves quoted phrases.
    Everything search syntax: space=AND, |=OR, !=NOT, < >=grouping, ""=phrase.
    """
    try:
        tokens = shlex.split(keywords, posix=False)
    except ValueError:
        tokens = keywords.split()
    args = [*tokens, "ext:md", "-path", kb_root]
    text, code = await spawn_run(es_path, args, encoding="gbk")
    if code != 0 and not text:
        return []
    return deduplicate(text, exclude_paths)


async def search_content_global(
    es_path: str,
    rg_path: str,
    kb_root: str,
    pattern: str,
    exclude_paths: list[str],
    content_search_enabled: bool = False,
    total_md_count: int = 0,
) -> tuple[list[str], str]:
    """Mode B: Global content search.
    - If ES_ContentSearchEnabled, use es.exe content: (Everything index).
    - Otherwise, use rg -l recursive only if total_md_count < RG_GLOBAL_LIMIT.
    Returns (file_list, method_used). method may be "es", "rg", or "blocked".
    """
    if content_search_enabled:
        args = ["ext:md", f'content:"{pattern}"', "-path", kb_root]
        text, code = await spawn_run(es_path, args, encoding="gbk")
        if code == 0 and text:
            result = deduplicate(text, exclude_paths)
            if result:
                return result, "es"

    if total_md_count >= RG_GLOBAL_LIMIT:
        return [], "blocked"

    # rg recursive -l (list matching files)
    text, code = await spawn_run(
        rg_path,
        ["--glob", "*.md", "-l", pattern, kb_root],
        encoding="utf-8",
        timeout=120,
    )
    if code in (0, 1) and text:
        lines = [s.strip() for s in text.splitlines() if s.strip()]
        if exclude_paths:
            escaped = [re.escape(p) for p in exclude_paths]
            pattern_re = re.compile("|".join(f"[\\\\/]{p}[\\\\/]" for p in escaped))
            lines = [l for l in lines if not pattern_re.search(l)]
        return lines, "rg"

    return [], "none"


async def search_content_in_files_batch(
    rg_path: str, file_list: list[str], pattern: str
) -> dict[str, str]:
    """Mode C: rg content search within a specific set of files.
    Uses rg --json for reliable cross-platform output parsing.
    Returns {filepath: match_text}.
    """
    if not file_list:
        return {}

    BATCH = 50
    MAX_FILES = 200
    results: dict[str, list[str]] = {}

    for i in range(0, min(len(file_list), MAX_FILES), BATCH):
        batch = file_list[i : i + BATCH]
        text, code = await spawn_run(
            rg_path,
            ["--json", pattern, *batch, "-C", "2"],
            encoding="utf-8",
            timeout=60,
        )
        if code not in (0, 1) or not text:
            continue

        current_file = ""
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except (ValueError, LookupError):
                continue
            obj_type = obj.get("type", "")
            data = obj.get("data", {})
            path_data = data.get("path", {})
            fp = path_data.get("text", "")
            if fp:
                current_file = fp
            if obj_type != "match":
                continue
            lines_data = data.get("lines", {})
            line_text = lines_data.get("text", "")
            if line_text and current_file:
                results.setdefault(current_file, []).append(line_text.rstrip("\n"))

    return {k: "\n".join(v) for k, v in results.items()}
