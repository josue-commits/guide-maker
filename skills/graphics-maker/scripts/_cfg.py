#!/usr/bin/env python3
"""
Config access for graphics-maker scripts.

Tries to import the shared loader from the make-guide sibling skill
(skills/make-guide/scripts/_config.py; the v2 folder name guide-maker is
still looked for after it). If that skill is not installed, or
is an older version without the v2 API, a small standalone loader takes over
so every graphics-maker script still runs on its own.

Both paths expose the same names:

    load_config(path=None) -> dict
    cfg_get(cfg, "graphics.cta_bar.height_pct", default) -> value
    secret(cfg, "kieai") -> str        env var > key file > config, "" if none
    sibling("make-guide") -> Path      raises FileNotFoundError if missing
    skill_dir() -> Path                this skill's directory
    project_dir(cfg=None) -> Path      the folder holding .guide-maker/
    project_file(name, cfg=None)       project_dir()/.guide-maker/<name>
    state_path(cfg, name) -> Path      paths.state or .guide-maker/state/<name>, created
    resource(cfg, key) -> Path         project override or the shipped reference

Config search order for the standalone loader: the explicit path argument,
env GUIDE_MAKER_CONFIG, <dir>/.guide-maker/config.yaml|json walking up from
the working directory, then ~/.config/guide-maker/config.yaml|json. PyYAML is
required for .yaml files; a .json file at any of those locations also works
without PyYAML. Nothing is written under this skill folder at run time.
"""
import json
import os
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve()
_SKILL_DIR = _HERE.parents[1]          # skills/graphics-maker
_SKILLS_ROOT = _HERE.parents[2]        # skills/


# make-guide first (v3 name), then guide-maker (v2 name) for one release.
_CORE_SKILL_NAMES = ("make-guide", "guide-maker")


def _candidate_guide_maker_dirs():
    env_root = os.environ.get("GUIDE_MAKER_SKILLS_DIR", "")
    roots = [_SKILLS_ROOT]
    if env_root:
        roots.append(pathlib.Path(env_root).expanduser())
    return [root / name / "scripts" for root in roots for name in _CORE_SKILL_NAMES]


USING_SHARED_LOADER = False

for _cand in _candidate_guide_maker_dirs():
    if (_cand / "_config.py").exists():
        sys.path.insert(0, str(_cand))
        try:
            from _config import load_config, cfg_get, secret, sibling  # noqa: F401
            from _config import project_dir, project_file, state_path, resource  # noqa: F401
            USING_SHARED_LOADER = True
        except ImportError:
            # Older core skill without the v3 API. Fall through to standalone.
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

    _PROJECT_DIRNAME = ".guide-maker"
    _CONFIG_NAMES = ("config.yaml", "config.json")

    def _walk_up(start):
        cur = pathlib.Path(start).expanduser().resolve()
        yield cur
        for parent in cur.parents:
            yield parent

    def _search_paths(path):
        if path:
            return [pathlib.Path(path).expanduser()]
        out = []
        env_path = os.environ.get("GUIDE_MAKER_CONFIG", "")
        if env_path:
            out.append(pathlib.Path(env_path).expanduser())
        for d in _walk_up(pathlib.Path.cwd()):
            out += [d / _PROJECT_DIRNAME / name for name in _CONFIG_NAMES]
        home = pathlib.Path("~/.config/guide-maker").expanduser()
        out += [home / name for name in _CONFIG_NAMES]
        return out

    def project_dir(cfg=None) -> pathlib.Path:
        """The folder holding .guide-maker/: the config's own project when it was
        loaded from one, else the first ancestor of cwd with .guide-maker/, else cwd."""
        found = (cfg or {}).get("_config_path", "")
        if found:
            parent = pathlib.Path(found).expanduser().resolve().parent
            if parent.name == _PROJECT_DIRNAME:
                return parent.parent
        for d in _walk_up(pathlib.Path.cwd()):
            if (d / _PROJECT_DIRNAME).is_dir():
                return d
        return pathlib.Path.cwd().resolve()

    def project_file(name, cfg=None) -> pathlib.Path:
        return project_dir(cfg) / _PROJECT_DIRNAME / name

    def state_path(cfg, name) -> pathlib.Path:
        """paths.state from the config, else <project>/.guide-maker/state/. Created."""
        base = cfg_get(cfg, "paths.state", "") or ""
        folder = pathlib.Path(base).expanduser() if base else project_file("state", cfg)
        folder.mkdir(parents=True, exist_ok=True)
        return folder / name

    def resource(cfg, key) -> pathlib.Path:
        """Project override in .guide-maker/, else the shipped reference next to make-guide."""
        names = {"voice": ("voice.md", "references/writing/voice.md"),
                 "examples": ("examples.md", "references/linkedin/examples.md"),
                 "top_performers": ("top-performers.md", "references/linkedin/top-performers.md"),
                 "banned_words": ("banned-words.md", "references/writing/humanizer.md")}
        if key not in names:
            raise KeyError("unknown resource %r" % key)
        override = project_file(names[key][0], cfg)
        if override.is_file():
            return override
        for core in _CORE_SKILL_NAMES:
            shipped = skills_root() / core / names[key][1]
            if shipped.exists():
                return shipped
        return skills_root() / _CORE_SKILL_NAMES[0] / names[key][1]

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
           "skills_root", "project_dir", "project_file", "state_path", "resource",
           "USING_SHARED_LOADER"]
