#!/usr/bin/env python3
"""Config access for dm-automation.

Prefers the shared loader that ships with the guide-maker sibling skill
(skills/guide-maker/scripts/_config.py). When guide-maker is not installed
next to this skill, a small standalone loader takes over so every command
still runs: it reads GUIDE_MAKER_CONFIG, then ./config.yaml, then
<this skill>/config.yaml.

Both paths expose the same names: load_config, cfg_get, secret, sibling,
skills_root. Import from here, never from _config directly.
"""

from __future__ import annotations

import json
import os
import pathlib
import sys
from typing import Any, Optional

_HERE = pathlib.Path(__file__).resolve()
SKILL_DIR = _HERE.parent.parent  # skills/dm-automation

_ENV_KEYS = {
    "notion": "NOTION_API_KEY",
    "kieai": "KIEAI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "apify": "APIFY_TOKEN",
    "leadshark": "LEADSHARK_API_KEY",
}
_KEY_FILES = {
    "notion": "~/.config/notion/api_key",
    "kieai": "~/.config/kieai/api_key",
    "openai": "~/.config/openai/api_key",
    "apify": "~/.config/apify/api_key",
    "leadshark": "~/.config/leadshark/api_key",
}

SHARED_LOADER = False


def _shared_candidates():
    yield _HERE.parents[2] / "guide-maker" / "scripts"
    env_root = os.environ.get("GUIDE_MAKER_SKILLS_DIR", "")
    if env_root:
        yield pathlib.Path(env_root).expanduser() / "guide-maker" / "scripts"


for _cand in _shared_candidates():
    if (_cand / "_config.py").exists():
        sys.path.insert(0, str(_cand))
        try:
            from _config import cfg_get, load_config, secret, sibling, skills_root  # type: ignore # noqa: F401

            SHARED_LOADER = True
        except ImportError:
            # An older guide-maker (v1) is present but lacks the v2 API.
            # Fall through to the standalone loader below.
            SHARED_LOADER = False
        break


if not SHARED_LOADER:

    def skills_root() -> pathlib.Path:
        env_root = os.environ.get("GUIDE_MAKER_SKILLS_DIR", "")
        if env_root:
            return pathlib.Path(env_root).expanduser().resolve()
        return SKILL_DIR.parent

    def sibling(name: str) -> pathlib.Path:
        path = skills_root() / name
        if not path.is_dir():
            raise FileNotFoundError(
                f"Sibling skill '{name}' not found at {path}. Install it next to "
                f"{SKILL_DIR} or point GUIDE_MAKER_SKILLS_DIR at the folder that holds it."
            )
        return path

    def _read_config_file(path: pathlib.Path) -> dict:
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            return json.loads(text) or {}
        try:
            import yaml  # type: ignore
        except ImportError:
            raise SystemExit(
                "PyYAML is required to read a YAML config. Install it with: "
                "python3 -m pip install pyyaml (or write the config as config.json)."
            )
        return yaml.safe_load(text) or {}

    def load_config(path: Optional[str] = None) -> dict:
        candidates = []
        if path:
            candidates.append(pathlib.Path(path).expanduser())
        env_path = os.environ.get("GUIDE_MAKER_CONFIG", "")
        if env_path:
            candidates.append(pathlib.Path(env_path).expanduser())
        candidates.append(pathlib.Path.cwd() / "config.yaml")
        candidates.append(pathlib.Path.cwd() / "config.json")
        candidates.append(SKILL_DIR / "config.yaml")
        candidates.append(SKILL_DIR / "config.json")
        for cand in candidates:
            if cand.is_file():
                cfg = _read_config_file(cand)
                if not isinstance(cfg, dict):
                    raise SystemExit(f"Config at {cand} is not a mapping.")
                if "schema_version" not in cfg:
                    print(
                        f"Note: {cand} has no schema_version. dm-automation expects the v2 "
                        "nested layout (author:, community:, dm:, dm_tool:).",
                        file=sys.stderr,
                    )
                return cfg
        raise FileNotFoundError(
            "No config found. Pass --config /abs/path/config.yaml, set GUIDE_MAKER_CONFIG, "
            "or put config.yaml in the working directory. guide-maker ships a "
            "config.example.yaml to copy from."
        )

    def cfg_get(cfg: dict, dotted: str, default: Any = None) -> Any:
        node: Any = cfg
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return default if node is None else node

    def secret(cfg: dict, name: str) -> str:
        env_var = _ENV_KEYS.get(name)
        if env_var and os.environ.get(env_var):
            return os.environ[env_var].strip()
        key_file = _KEY_FILES.get(name)
        if key_file:
            fp = pathlib.Path(key_file).expanduser()
            if fp.is_file():
                value = fp.read_text(encoding="utf-8").strip()
                if value:
                    return value
        value = cfg_get(cfg, f"providers.{name}.api_key", "") or ""
        return str(value).strip()


__all__ = ["SKILL_DIR", "SHARED_LOADER", "cfg_get", "load_config", "secret", "sibling", "skills_root"]
