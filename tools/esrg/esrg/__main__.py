import asyncio
import sys

from .config import load_config
from .engine import count_md_files, ensure_everything
from .app import SearchApp


def main():
    config = load_config()
    asyncio.run(_startup(config))


async def _startup(config):
    print(f"esrg v1.0.0  |  kbRoot: {config['kbRoot']}")
    if sys.platform == "win32":
        ready = await ensure_everything(
            config["esPath"],
            config["kbRoot"],
            config["everythingPath"],
        )
        if not ready:
            print("Warning: Everything IPC check failed. ES search may not work.")
            print("Make sure Everything is running (tray icon visible).")

    md_count = await count_md_files(config["esPath"], config["kbRoot"])
    print(f"Indexed {md_count} *.md files in kbRoot")
    await SearchApp(config, total_md_count=md_count).run_async()


if __name__ == "__main__":
    main()
