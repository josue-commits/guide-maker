#!/usr/bin/env python3
"""
Config access for graphics-maker scripts.

Tries to import the shared loader from the guide-maker sibling skill
(skills/guide-maker/scripts/_config.py). If that skill is not installed, or
is an older version without the v2 API, a small standalone loader takes over
so every graphics-maker script still runs on its own.

Both paths expose the same names:

    load_config(path=None) -> dict
    cfg_get(cfg, "graphics.cta_bar.height_pct", default) -> value
    secret(cfg, "kieai") -> str        env var > key file > config, "" if none
    sibling("guide-maker") -> Path     raises FileNotFoundError if missing
    skill_dir() -> Path                this skill's directory

Config search order for the standalone loader: the explicit path argument,
env GUIDE_MAKER_CONFIG, ./config.yaml, this skill's config.yaml, then
~/.config/guide-maker/config.yaml. PyYAML is required for .yaml files; a
.json file at any of those locations also works without PyYAML.
"""
import json
import os
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve()
_SKILL_DIR = _HERE.parents[1]          # skills/graphics-maker
_SKILLS_ROOT = _HERE.parents[2]        # skills/


def _candidate_guide_maker_dirs():
    env_root = os.environ.get("GUIDE_MAKER_SKILLS_DIR", "")
    cands = [_SKILLS_ROOT / "guide-maker" / "scripts"]
    if env_root:
        cands.append(pathlib.Path(env_root) / "guide-maker" / "scripts")
    return cands


USING_SHARED_LOADER = False

for _cand in _candidate_guide_maker_dirs():
    if (_cand / "_config.py").exists():
        sys.path.insert(0, str(_cand))
        try:
            from _config import load_config, cfg_get, secret, sibling  # noqa: F401
            USING_SHARED_LOADER = True
        except ImportError:
            # Older guide-maker without the v2 API. Fall through to standalone.
            sys.path.remove(str(_cand))
            sys.modules.pop("_config", None)
        break


def skill_dir() -> pathlib.Path:
    """Directory of the graphics-maker skill."""
    return _SKILL_DIR


def skills_root() -> pathlib.Path:
    env_root = os.environ.get("GUIDE_MAKER_SKILLS_DIR", "")
    return pathlib.Path(env_root) if env_root else _SKILLS_ROOT


if not USING_SHARED_LOADER:

    _SECRET_ENV = {
        "notion": "NOTION_API_KEY",
        "kieai": "KIEAI_API_KEY",
        "openai": "OPENAI_API_KEY",
        "apify": "APIFY_TOKEN",
        "leadshark": "LEADSHARK_API_KEY",
    }
    _SECRET_FILE = {
        "notion": "~/.config/notion/api_key",
        "kieai": "~/.config/kieai/api_key",
        "openai": "~/.config/openai/api_key",
        "apify": "~/.config/apify/api_key",
        "leadshark": "~/.config/leadshark/api_key",
    }

    def _search_paths(path):
        if path:
            return [pathlib.Path(path).expanduser()]
        out = []
        env_path = os.environ.get("GUIDE_MAKER_CONFIG", "")
        if env_path:
            out.append(pathlib.Path(env_path).expanduser())
        cwd = pathlib.Path.cwd()
        out += [cwd / "config.yaml", cwd / "config.json",
                _SKILL_DIR / "config.yaml", _SKILL_DIR / "config.json",
                pathlib.Path("~/.config/guide-maker/config.yaml").expanduser(),
                pathlib.Path("~/.config/guide-maker/config.json").expanduser()]
        return out

    def _read(path):
        text = path.read_text(encoding="utf-8")
        if path.suffix.lower() == ".json":
            return json.loads(text) or {}
        try:
            import yaml
        except ImportError:
            raise ImportError(
                "PyYAML is required to read %s. Install it with: pip install pyyaml "
                "(or write the same config as config.json)" % path)
        return yaml.safe_load(text) or {}

    def load_config(path=None) -> dict:
        """Load the config dict. Returns {} when no file is found and no path
        was given, so zero-cost commands (card, finalize) still run with defaults."""
        for cand in _search_paths(path):
            if cand.exists():
                cfg = _read(cand)
                if not isinstance(cfg, dict):
                    raise ValueError("%s did not parse to a mapping" % cand)
                cfg.setdefault("_config_path", str(cand))
                return cfg
        if path:
            raise FileNotFoundError("Config not found: %s" % path)
        return {}

    def cfg_get(cfg: dict, dotted: str, default=None):
        """Dotted-path accessor: cfg_get(cfg, "graphics.cta_bar.bg", "")."""
        node = cfg
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return default if node is None else node

    def secret(cfg: dict, name: str) -> str:
        """Env var wins, then key file, then providers.<name>.api_key in config."""
        env = _SECRET_ENV.get(name)
        if env and os.environ.get(env):
            return os.environ[env].strip()
        key_file = _SECRET_FILE.get(name)
        if key_file:
            p = pathlib.Path(key_file).expanduser()
            if p.exists():
                val = p.read_text(encoding="utf-8").strip()
                if val:
                    return val
        return str(cfg_get(cfg, "providers.%s.api_key" % name, "") or "").strip()

    def sibling(name: str) -> pathlib.Path:
        p = skills_root() / name
        if not p.exists():
            raise FileNotFoundError(
                "Sibling skill '%s' not found at %s. Install it next to graphics-maker "
                "or set GUIDE_MAKER_SKILLS_DIR to the folder that contains it." % (name, p))
        return p


__all__ = ["load_config", "cfg_get", "secret", "sibling", "skill_dir",
           "skills_root", "USING_SHARED_LOADER"]
