#!/usr/bin/env python3
"""Config access for dm-automation.

Prefers the shared loader that ships with the make-guide sibling skill
(skills/make-guide/scripts/_config.py; the v2 folder name guide-maker is
looked for after it). When neither is installed next to this skill, a small
standalone loader takes over so every command
still runs: it reads --config, then GUIDE_MAKER_CONFIG, then
<dir>/.guide-maker/config.yaml|json walking up from the working directory,
then ~/.config/guide-maker/config.yaml|json.

Both paths expose the same names: load_config, cfg_get, secret, sibling,
skills_root, project_dir, project_file, state_path, resource. Import from
here, never from _config directly. Nothing is written under this skill
folder at run time.
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


# make-guide first (v3 name), then guide-maker (v2 name) for one release.
_CORE_SKILL_NAMES = ("make-guide", "guide-maker")


def _shared_candidates():
    roots = [_HERE.parents[2]]
    env_root = os.environ.get("GUIDE_MAKER_SKILLS_DIR", "")
    if env_root:
        roots.append(pathlib.Path(env_root).expanduser())
    for root in roots:
        for name in _CORE_SKILL_NAMES:
            yield root / name / "scripts"


for _cand in _shared_candidates():
    if (_cand / "_config.py").exists():
        sys.path.insert(0, str(_cand))
        try:
            from _config import cfg_get, load_config, secret, sibling, skills_root  # type: ignore # noqa: F401
            from _config import project_dir, project_file, state_path, resource  # type: ignore # noqa: F401

            SHARED_LOADER = True
        except ImportError:
            # An older core skill is present but lacks the v3 API.
            # Fall through to the standalone loader below.
            SHARED_LOADER = False
            sys.modules.pop("_config", None)
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

    _PROJECT_DIRNAME = ".guide-maker"
    _CONFIG_NAMES = ("config.yaml", "config.json")

    def _walk_up(start: pathlib.Path):
        cur = pathlib.Path(start).expanduser().resolve()
        yield cur
        for parent in cur.parents:
            yield parent

    def load_config(path: Optional[str] = None) -> dict:
        candidates = []
        if path:
            candidates.append(pathlib.Path(path).expanduser())
        env_path = os.environ.get("GUIDE_MAKER_CONFIG", "")
        if env_path:
            candidates.append(pathlib.Path(env_path).expanduser())
        for d in _walk_up(pathlib.Path.cwd()):
            candidates += [d / _PROJECT_DIRNAME / name for name in _CONFIG_NAMES]
        home = pathlib.Path("~/.config/guide-maker").expanduser()
        candidates += [home / name for name in _CONFIG_NAMES]
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
                cfg.setdefault("_path", str(cand))
                return cfg
        raise FileNotFoundError(
            "No config found. Pass --config /abs/path/config.yaml, set GUIDE_MAKER_CONFIG, "
            "or create <project>/.guide-maker/config.yaml (doctor.py --init in make-guide, "
            "or /setup-guide-maker)."
        )

    def project_dir(cfg: Optional[dict] = None) -> pathlib.Path:
        """The folder holding .guide-maker/: the config's own project when it was
        loaded from one, else the first ancestor of cwd with .guide-maker/, else cwd."""
        found = (cfg or {}).get("_path", "")
        if found:
            parent = pathlib.Path(found).expanduser().resolve().parent
            if parent.name == _PROJECT_DIRNAME:
                return parent.parent
        for d in _walk_up(pathlib.Path.cwd()):
            if (d / _PROJECT_DIRNAME).is_dir():
                return d
        return pathlib.Path.cwd().resolve()

    def project_file(name: str, cfg: Optional[dict] = None) -> pathlib.Path:
        return project_dir(cfg) / _PROJECT_DIRNAME / name

    def state_path(cfg: dict, name: str) -> pathlib.Path:
        """paths.state from the config, else <project>/.guide-maker/state/. Created."""
        base = cfg_get(cfg, "paths.state", "") or ""
        folder = pathlib.Path(base).expanduser() if base else project_file("state", cfg)
        folder.mkdir(parents=True, exist_ok=True)
        return folder / name

    def resource(cfg: dict, key: str) -> pathlib.Path:
        """Project override in .guide-maker/, else the shipped reference next to make-guide."""
        names = {"voice": ("voice.md", "references/writing/voice.md"),
                 "examples": ("examples.md", "references/linkedin/examples.md"),
                 "top_performers": ("top-performers.md", "references/linkedin/top-performers.md"),
                 "banned_words": ("banned-words.md", "references/writing/humanizer.md")}
        if key not in names:
            raise KeyError(f"unknown resource {key!r}")
        override = project_file(names[key][0], cfg)
        if override.is_file():
            return override
        for core in _CORE_SKILL_NAMES:
            shipped = skills_root() / core / names[key][1]
            if shipped.exists():
                return shipped
        return skills_root() / _CORE_SKILL_NAMES[0] / names[key][1]

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


__all__ = ["SKILL_DIR", "SHARED_LOADER", "cfg_get", "load_config", "secret", "sibling", "skills_root",
           "project_dir", "project_file", "state_path", "resource"]
