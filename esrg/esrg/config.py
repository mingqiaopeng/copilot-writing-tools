"""Config loading for esrg. Reads ~/.esrg/config.json, auto-creates with defaults if missing."""

import json
import os
from pathlib import Path


DEFAULT_CONFIG = {
    "esPath": "es.exe",
    "rgPath": "rg",
    "kbRoot": "~/Documents",
    "everythingPath": "C:\\Program Files\\Everything\\Everything.exe",
    "excludePaths": [],
    "ES_ContentSearchEnabled": False,
}

CONFIG_DIR = Path.home() / ".esrg"
CONFIG_PATH = CONFIG_DIR / "config.json"


def _expand_home(path: str) -> str:
    if path.startswith("~/"):
        return str(Path.home() / path[2:])
    if path.startswith("~\\"):
        return str(Path.home() / path[2:])
    return path


def load_config() -> dict:
    config = dict(DEFAULT_CONFIG)

    if CONFIG_PATH.exists():
        try:
            raw = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            for key in DEFAULT_CONFIG:
                if key in raw:
                    config[key] = raw[key]
        except (json.JSONDecodeError, OSError):
            pass
    else:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        CONFIG_PATH.write_text(
            json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    config["kbRoot"] = _expand_home(config["kbRoot"])
    return config
