#!/usr/bin/env python3
"""Shared configuration loader for guide-maker and its sibling skills.

This is the contract graphics-maker, dm-automation and topic-finder import.
Keep the public surface stable:

    skill_dir() -> Path            directory of skills/make-guide
    skills_root() -> Path          parent of skill_dir(); env GUIDE_MAKER_SKILLS_DIR overrides
    sibling(name) -> Path          skills_root()/name, FileNotFoundError with install hint;
                                   "guide-maker" is accepted as an alias of "make-guide"
                                   for one release (the v2 folder name)
    load_config(path=None) -> dict v2 nested dict; v1 flat keys are mapped in with ONE
                                   printed deprecation line. cfg["_path"] is the file,
                                   cfg["_source"] is which search step found it
    project_dir(cfg=None) -> Path  the folder that holds .guide-maker/: the config's own
                                   project when it was loaded from one, else the first
                                   ancestor of cwd holding .guide-maker/, else cwd
    project_file(name, cfg=None)   project_dir(cfg)/.guide-maker/<name>
    resource(cfg, key) -> Path     key in {voice, examples, top_performers, banned_words};
                                   the project override when it exists, else the shipped file
    state_path(cfg, name) -> Path  cfg paths.state, else project_file("state")/<name>;
                                   the parent folder is created on demand
    cfg_get(cfg, "a.b.c", default) dotted accessor with schema defaults as the last fallback
    secret(cfg, name) -> str       name in {notion, kieai, openai, apify, leadshark};
                                   env var > key file > config; "" if none
    validate(cfg) -> [(level, message)]   level in OK | WARN | FAIL, used by doctor.py

Config search order for load_config(None), first hit wins (cfg["_source"]):
    1. explicit path argument                                   "arg"
    2. env GUIDE_MAKER_CONFIG                                   "env"
    3. <dir>/.guide-maker/config.yaml|json, for dir in cwd,
       cwd.parent, ... up to the filesystem root                "project"
    4. ~/.config/guide-maker/config.yaml|json                   "home"
    5. skill_dir()/config.yaml|json  (the v2 location; loads with one stderr
       deprecation line, removed in 4.0)                        "legacy"

Nothing under skill_dir() is written at run time. State (closer log, format
usage log), user format cards and reference overrides live in .guide-maker/.

Python 3.9+, stdlib + PyYAML (optional: JSON works without it).
"""

import copy
import json
import os
import re
import sys
from pathlib import Path

SCHEMA_VERSION = 2

SECRET_ENV = {
    "notion": "NOTION_API_KEY",
    "kieai": "KIEAI_API_KEY",
    "openai": "OPENAI_API_KEY",
    "apify": "APIFY_TOKEN",
    "leadshark": "LEADSHARK_API_KEY",
}
SECRET_FILES = {
    "notion": "~/.config/notion/api_key",
    "kieai": "~/.config/kieai/api_key",
    "openai": "~/.config/openai/api_key",
    "apify": "~/.config/apify/api_key",
    "leadshark": "~/.config/leadshark/api_key",
}

# Every key the skill reads, with its default. config.example.yaml documents
# the same tree; keep the two in sync.
DEFAULTS = {
    "schema_version": SCHEMA_VERSION,
    "notion": {
        "api_key": "",
        "guide_database_id": "",
        "content_board_database_id": "",
        "public_domain": "",
        "guide_types": ["Technical Tutorial", "Strategic Framework",
                        "Comparison/Persuasion", "Use-case Stack"],
    },
    "author": {"name": "", "linkedin_url": "", "voice": "founder", "dm_signoff": ""},
    "community": {"platform": "none", "name": "", "url": "", "callout_line": ""},
    "secondary_channel": {"type": "none", "handle": "", "url": "", "credit_line": ""},
    "accounts": [{"name": "", "voice": "founder", "dm_destination": "auto"}],
    "workflow": {
        "gates": "two",
        "work_dir": "/tmp/guide-maker",
        "language": "en",
        "post_days": ["Monday", "Wednesday", "Friday"],
        "one_card_per": "guide",
        "cover_required": True,
    },
    "topic_finder": {
        "path": "",
        "sources": ["youtube", "reddit", "x"],
        "lookback_days": {"youtube": 7, "reddit": 7, "x": 8},
        "youtube_tracks": ["tool", "business"],
        "scan_health": {
            "min_channels_with_videos": 5,
            "min_x_posts": 1,
            "min_reddit_posts": 1,
            "fail_on_missing_config": True,
        },
        "x_bookmark_rate": {"substance": 0.8, "noise": 0.1},
    },
    "excluded_topics": [],
    "research": {
        "depth_gate": {
            "min_authoritative_sources": 3,
            "require_official_docs": True,
            "min_video_minutes": 20,
            "min_written_pages": 10,
            "min_subpages": 4,
            "max_subpages": 7,
        },
        "hard_reject": ["news or drama with no tutorial payoff",
                        "single-feature announcement with no docs",
                        "every source says the same two or three things",
                        "pure opinion or reaction"],
        "auto_accept_patterns": [],
        "check_already_covered": {"guide_db_titles": True, "content_board_keywords": True},
        "gap_analysis": "required",
    },
    "sources": {
        "cite_official_docs": True,
        "cite_institutional_talks": True,
        "cite_creator_videos": False,
        "cross_guide_references": False,
    },
    "copy": {
        "cta_mode": "graphic",
        "structure": "prose",
        "variations": 3,
        "hooks": ["contrarian", "problem_pain", "quantity_build"],
        "words": {"min": 180, "max": 250, "target": 215,
                  "reject_below": 140, "reject_above": 300},
        "closers": [
            "Free Access",
            "Get free access",
            "Get access for free",
            "I'm giving away the complete guide for free",
            "I'm giving away the complete guide. For free.",
            "The guide and the full setup are free",
            "Give me a shout if you want the full setup",
        ],
        "closer_rotation_weeks": 3,
        "banned_in_copy": [
            "comment \"", "comment '", "like this post", "connect with me",
            "repost this", "and i'll send it", "and i will send it", "dm me",
        ],
        "banned_words_file": "references/writing/humanizer.md",
        "extra_banned_words": [],
    },
    "dm": {
        "versions": "auto",
        "merge_tag": "{{firstName}}",
        "max_lines": 7,
        "hard_wrap": False,
        "guide_link_must_be_public": True,
        "vary_opener_weekly": True,
    },
    "dm_tool": {
        "provider": "manual",
        "timezone": "",                    # falls back to leadshark.timezone
        "leadshark": {
            "base_url": "https://apex.leadshark.io",
            "auto_connect": True,
            "comment_replies": ["sent", "sent!", "Sent over!", "Sending", "Sent! Check dms!"],
            "non_first_degree_reply": "Please connect with me so I can send it! :)",
            "attachment_max_bytes": 4194304,
            "create_as": "Paused",
            "timezone": "UTC",
            "post_as": "",
            "organization_id": "",
        },
    },
    "brand": {
        "colors": {"dark": "#1A1A1C", "light": "#F7F7F7",
                   "accent_1": "#A6CB17", "accent_2": "#8033F4"},
        "fonts": {"bold": "", "regular": ""},
        "typography_prompt": "modern geometric sans-serif, bold weight",
        "logo": {"path": "", "on_post_graphic": False, "on_cover": False},
    },
    "cover": {"mode": "simple", "style": "dark", "size": [1500, 600]},
    "graphics": {
        "provider": "none",
        "scene_model": "",
        "text_model": "",
        "aspect_ratio": "4:5",
        "resolution": "2K",
        "cta_bar": {"renderer": "pillow", "string": "primary",
                    "height_pct": 0.11, "bg": "", "fg": ""},
        "strip_c2pa": True,
        "format_rotation_days": 7,
        "negative_prompt_extra": "",
        "usage_log": "",                   # empty = <graphics-maker>/format-usage-log.jsonl
        "upload_endpoint": "",             # empty = anonymous catbox API
        "logo_corner": "top-left",
        "logo_width_pct": 0.12,
        "logo_on_dark": "",
    },
    "providers": {
        "kieai": {"api_key": ""},
        "openai": {"api_key": ""},
        "apify": {"api_key": ""},
        "leadshark": {"api_key": ""},
    },
    "tools": {"ytdlp_path": ""},
    "paths": {"state": ""},                # empty = <project>/.guide-maker/state
}

# .guide-maker/ file name -> path of the shipped default, relative to skill_dir()
RESOURCES = {
    "voice": ("voice.md", "references/writing/voice.md"),
    "examples": ("examples.md", "references/linkedin/examples.md"),
    "top_performers": ("top-performers.md", "references/linkedin/top-performers.md"),
    "banned_words": ("banned-words.md", "references/writing/humanizer.md"),
}
PROJECT_DIRNAME = ".guide-maker"
CONFIG_NAMES = ("config.yaml", "config.json")
LEGACY_DEPRECATION = ("config inside the skill folder is deprecated; run doctor.py --init "
                      "or /setup-guide-maker")

# v1 flat key -> v2 dotted path
V1_KEYS = {
    "notion_api_key": "notion.api_key",
    "guide_database_id": "notion.guide_database_id",
    "content_board_database_id": "notion.content_board_database_id",
    "author_name": "author.name",
    "linkedin_url": "author.linkedin_url",
    "community_name": "community.name",
    "community_url": "community.url",
    "community_description": "community.callout_line",
    "kieai_api_key": "providers.kieai.api_key",
    "brand_colors": "brand.colors",
    "ytdlp_path": "tools.ytdlp_path",
    "accounts": "accounts",
}

_cache = {}
_deprecation_printed = False
_legacy_printed = False


# --- Paths --------------------------------------------------------------------

def skill_dir():
    """Directory of skills/make-guide (this file lives in scripts/ under it)."""
    return Path(__file__).resolve().parent.parent


def skills_root():
    """Parent of skill_dir(), or GUIDE_MAKER_SKILLS_DIR when set."""
    override = os.environ.get("GUIDE_MAKER_SKILLS_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return skill_dir().parent


# The v2 folder name. sibling("guide-maker") resolves to make-guide for one
# release so older callers keep working; drop the alias in 4.0.
SIBLING_ALIASES = {"guide-maker": "make-guide"}


def sibling(name):
    """Path of a sibling skill. Raises FileNotFoundError with an install hint.

    "guide-maker" (the v2 name of the core skill) is accepted as an alias of
    "make-guide" for one release. When the folder was installed under the old
    name, that path is returned so a half-upgraded tree still resolves.
    """
    wanted = [SIBLING_ALIASES.get(name, name)]
    if name in SIBLING_ALIASES or name in SIBLING_ALIASES.values():
        for old, new in SIBLING_ALIASES.items():
            if new == wanted[0] and old not in wanted:
                wanted.append(old)
    for candidate in wanted:
        path = skills_root() / candidate
        if path.is_dir():
            return path
    path = skills_root() / wanted[0]
    hints = {
        "topic-finder": (f"run install.sh at the repo root, or copy the topic-finder skill "
                         f"folder into {path}"),
    }
    hint = hints.get(name, f"copy the {wanted[0]} skill folder next to make-guide, or set "
                           "GUIDE_MAKER_SKILLS_DIR to the folder that holds both")
    raise FileNotFoundError(f"sibling skill '{name}' not found at {path}. Install it: {hint}")


# --- Project paths ------------------------------------------------------------

def _walk_up(start):
    """start and every ancestor, nearest first."""
    cur = Path(start).expanduser().resolve()
    yield cur
    for parent in cur.parents:
        yield parent


def project_dir(cfg=None):
    """The folder that holds .guide-maker/.

    When cfg was loaded from <dir>/.guide-maker/config.*, that <dir> wins, so
    a script run with --config from anywhere still finds the right overrides
    and state. Otherwise the first ancestor of cwd holding .guide-maker/, else
    cwd itself (the folder .guide-maker/ would be created in).
    """
    if cfg:
        found = cfg.get("_path", "")
        if found:
            parent = Path(found).expanduser().resolve().parent
            if parent.name == PROJECT_DIRNAME:
                return parent.parent
    for d in _walk_up(Path.cwd()):
        if (d / PROJECT_DIRNAME).is_dir():
            return d
    return Path.cwd().resolve()


def project_file(name, cfg=None):
    """project_dir(cfg)/.guide-maker/<name>. Not created."""
    return project_dir(cfg) / PROJECT_DIRNAME / name


def resource(cfg, key):
    """Path of a reference the writer reads: the project override when the
    user wrote one into .guide-maker/, else the file shipped with the skill.

    banned_words honours copy.banned_words_file: absolute paths are used as
    is; a relative path is resolved against skill_dir() unless the project
    override exists.
    """
    if key not in RESOURCES:
        raise KeyError(f"unknown resource {key!r}; one of {sorted(RESOURCES)}")
    override_name, shipped_rel = RESOURCES[key]
    if key == "banned_words":
        configured = cfg_get(cfg, "copy.banned_words_file") or ""
        if configured and os.path.isabs(os.path.expanduser(configured)):
            return Path(configured).expanduser()
        if configured:
            shipped_rel = configured
    override = project_file(override_name, cfg)
    if override.is_file():
        return override
    return skill_dir() / shipped_rel


def resource_source(cfg, key):
    """"override" when resource() returns a project file, else "shipped". For doctor."""
    path = resource(cfg, key)
    try:
        path.resolve().relative_to(skill_dir().resolve())
        return "shipped"
    except ValueError:
        return "override"


def state_path(cfg, name):
    """Where run-time state goes: paths.state from the config, else
    <project>/.guide-maker/state/. The folder is created on demand. Never
    under skill_dir()."""
    base = cfg_get(cfg, "paths.state") or ""
    folder = Path(base).expanduser() if base else project_file("state", cfg)
    folder.mkdir(parents=True, exist_ok=True)
    return folder / name


# --- Loading ------------------------------------------------------------------

def _candidate_paths():
    """(path, source) in search order; see the module docstring."""
    env = os.environ.get("GUIDE_MAKER_CONFIG", "").strip()
    if env:
        yield Path(env).expanduser(), "env"
    for d in _walk_up(Path.cwd()):
        for name in CONFIG_NAMES:
            yield d / PROJECT_DIRNAME / name, "project"
    home = Path("~/.config/guide-maker").expanduser()
    for name in CONFIG_NAMES:
        yield home / name, "home"
    for name in CONFIG_NAMES:
        yield skill_dir() / name, "legacy"


def _read_file(path):
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    if path.suffix.lower() == ".json":
        return json.loads(text) or {}
    try:
        import yaml
    except ImportError:
        raise ImportError(
            f"PyYAML is required to read {path}. Install it with: pip install pyyaml\n"
            "Or write the same keys as JSON in config.json next to config.yaml; "
            "the loader accepts either file.")
    return yaml.safe_load(text) or {}


def _deep_merge(base, override):
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = copy.deepcopy(value)
    return out


def _set_dotted(tree, dotted, value):
    parts = dotted.split(".")
    node = tree
    for part in parts[:-1]:
        node = node.setdefault(part, {})
    node[parts[-1]] = value


def is_v1(raw):
    """True when the file uses the flat v1 keys and no schema_version."""
    if not isinstance(raw, dict):
        return False
    if raw.get("schema_version"):
        return False
    return any(key in raw for key in V1_KEYS if key != "accounts")


def migrate_v1(raw):
    """Map a v1 flat dict onto the v2 nested shape (no defaults applied)."""
    out = {"schema_version": SCHEMA_VERSION}
    for old, new in V1_KEYS.items():
        if old in raw and raw[old] not in (None, ""):
            _set_dotted(out, new, raw[old])
    accounts = raw.get("accounts") or []
    fixed = []
    for acct in accounts:
        if not isinstance(acct, dict):
            continue
        cta = acct.get("cta_type", "")
        dest = {"community": "community", "direct": "direct"}.get(cta, "auto")
        fixed.append({"name": acct.get("name", ""),
                      "voice": acct.get("voice", "founder"),
                      "dm_destination": dest})
    if fixed:
        out["accounts"] = fixed
    if raw.get("community_url"):
        _set_dotted(out, "community.platform", _guess_platform(raw["community_url"]))
    return out


def _guess_platform(url):
    url = (url or "").lower()
    for name in ("skool", "discord", "circle", "slack"):
        if name in url:
            return name
    return "other"


def load_config(path=None):
    """Return the v2 nested config dict, defaults filled in.

    Raises FileNotFoundError when no config exists. v1 files load through a
    shim that prints one deprecation line to stderr.
    """
    global _deprecation_printed, _legacy_printed
    key = str(path) if path else f"cwd:{Path.cwd()}"
    if key in _cache:
        return _cache[key]

    found, source = None, None
    if path:
        found = Path(path).expanduser()
        source = "arg"
        if not found.exists():
            raise FileNotFoundError(f"Config not found: {found}")
    else:
        for cand, cand_source in _candidate_paths():
            if cand.is_file():
                found, source = cand, cand_source
                break
    if found is None:
        raise FileNotFoundError(
            "Config not found. Looked for $GUIDE_MAKER_CONFIG, "
            f"{PROJECT_DIRNAME}/config.yaml in {Path.cwd()} and every parent folder, "
            f"~/.config/guide-maker/config.yaml and (deprecated) {skill_dir() / 'config.yaml'}.\n"
            "Create it with: python3 scripts/doctor.py --init --project /path/to/your/project "
            "(or run /setup-guide-maker in Claude Code). config.json with the same keys works "
            "without PyYAML.")
    if source == "legacy" and not _legacy_printed:
        print(f"[guide-maker] {found}: {LEGACY_DEPRECATION}", file=sys.stderr)
        _legacy_printed = True

    raw = _read_file(found)
    if is_v1(raw):
        if not _deprecation_printed:
            print(f"[guide-maker] {found} uses the deprecated v1 flat config format; "
                  "loading through the compatibility shim. Run scripts/doctor.py "
                  "--migrate-config to print the v2 file.", file=sys.stderr)
            _deprecation_printed = True
        raw = migrate_v1(raw)

    cfg = _deep_merge(DEFAULTS, raw)
    cfg["_path"] = str(found)
    cfg["_source"] = source
    cfg["_v1"] = is_v1(_read_file(found))
    _cache[key] = cfg
    return cfg


def cfg_get(cfg, dotted, default=None):
    """Dotted accessor: cfg_get(cfg, "copy.words.max", 250)."""
    node = cfg
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            node = _default_for(dotted)
            return default if node is None else node
    return node


def _default_for(dotted):
    node = DEFAULTS
    for part in dotted.split("."):
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return copy.deepcopy(node)


# --- Secrets ------------------------------------------------------------------

def secret(cfg, name):
    """API key for a provider: env var, then key file, then config. "" if none."""
    if name not in SECRET_ENV:
        raise KeyError(f"unknown secret {name!r}; one of {sorted(SECRET_ENV)}")
    value = os.environ.get(SECRET_ENV[name], "").strip()
    if value:
        return value
    key_file = Path(SECRET_FILES[name]).expanduser()
    if key_file.exists():
        value = key_file.read_text(encoding="utf-8").strip()
        if value:
            return value
    if name == "notion":
        return (cfg_get(cfg, "notion.api_key", "") or "").strip()
    return (cfg_get(cfg, f"providers.{name}.api_key", "") or "").strip()


def secret_source(cfg, name):
    """Where secret() found the value: env | file | config | none. For doctor."""
    if os.environ.get(SECRET_ENV[name], "").strip():
        return "env"
    key_file = Path(SECRET_FILES[name]).expanduser()
    if key_file.exists() and key_file.read_text(encoding="utf-8").strip():
        return "file"
    if secret(cfg, name):
        return "config"
    return "none"


# --- Validation ---------------------------------------------------------------

HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def validate(cfg):
    """Static checks that need no network. Returns [(level, message)]."""
    out = []

    def ok(msg):
        out.append(("OK", msg))

    def warn(msg):
        out.append(("WARN", msg))

    def fail(msg):
        out.append(("FAIL", msg))

    if cfg.get("_v1"):
        warn("config uses the v1 flat format; run doctor.py --migrate-config")
    else:
        ok(f"schema_version {cfg_get(cfg, 'schema_version')}")

    if not cfg_get(cfg, "notion.guide_database_id"):
        warn("notion.guide_database_id empty: publishing (Phase 3a) is unavailable until it is set")
    else:
        ok("notion.guide_database_id set")
    if not cfg_get(cfg, "notion.content_board_database_id"):
        warn("notion.content_board_database_id empty: Phase 3d (Content Board card) is skipped")
    if not cfg_get(cfg, "notion.public_domain"):
        warn("notion.public_domain empty: public-URL check for DMs is skipped")

    if not cfg_get(cfg, "author.name"):
        warn("author.name empty: hub byline is omitted")

    gates = cfg_get(cfg, "workflow.gates")
    if gates not in ("one", "two"):
        fail(f"workflow.gates must be one or two, got {gates!r}")
    else:
        ok(f"workflow.gates = {gates}")

    cta = cfg_get(cfg, "copy.cta_mode")
    if cta == "copy":
        warn("copy.cta_mode = copy: the keyword goes in the post copy. LinkedIn suppresses "
             "reach on engagement instructions (same asset: 95 vs 11,432 impressions). "
             "See references/strategy/cta-evidence.md")
    elif cta == "graphic":
        ok("copy.cta_mode = graphic (keyword lives only in the post graphic)")
    else:
        fail(f"copy.cta_mode must be graphic or copy, got {cta!r}")

    words = cfg_get(cfg, "copy.words") or {}
    try:
        lo, hi = int(words.get("min", 0)), int(words.get("max", 0))
        rb, ra = int(words.get("reject_below", 0)), int(words.get("reject_above", 0))
        if not (rb <= lo < hi <= ra):
            fail(f"copy.words must satisfy reject_below <= min < max <= reject_above, got {words}")
        else:
            ok(f"copy.words {lo}-{hi} (reject <{rb} or >{ra})")
    except (TypeError, ValueError):
        fail(f"copy.words has non-integer values: {words}")

    closers = cfg_get(cfg, "copy.closers") or []
    if len(closers) < 3:
        warn(f"copy.closers has {len(closers)} entries; fewer than 3 makes rotation impossible")
    else:
        ok(f"{len(closers)} closers configured")

    for pattern in cfg_get(cfg, "excluded_topics") or []:
        if isinstance(pattern, str) and pattern.startswith("/") and pattern.endswith("/"):
            try:
                re.compile(pattern[1:-1])
            except re.error as exc:
                fail(f"excluded_topics regex {pattern} does not compile: {exc}")

    for name, value in (cfg_get(cfg, "brand.colors") or {}).items():
        if value and not HEX_COLOR.match(str(value)):
            fail(f"brand.colors.{name} = {value!r} is not a #RRGGBB color")

    for name in ("bold", "regular"):
        path = cfg_get(cfg, f"brand.fonts.{name}") or ""
        if path and not Path(path).expanduser().exists():
            fail(f"brand.fonts.{name} = {path} does not exist")

    provider = cfg_get(cfg, "graphics.provider")
    if provider not in ("none", "kieai", "openai"):
        fail(f"graphics.provider must be none, kieai or openai, got {provider!r}")
    dm_provider = cfg_get(cfg, "dm_tool.provider")
    if dm_provider not in ("manual", "leadshark"):
        fail(f"dm_tool.provider must be manual or leadshark, got {dm_provider!r}")
    cover = cfg_get(cfg, "cover.mode")
    if cover not in ("simple", "ai", "upload"):
        fail(f"cover.mode must be simple, ai or upload, got {cover!r}")

    tag = cfg_get(cfg, "dm.merge_tag") or ""
    if not tag:
        warn("dm.merge_tag empty: DMs will carry no first-name personalization")
    return out


# --- CLI helper ---------------------------------------------------------------

def add_config_arg(parser, subparsers=None):
    """Add the shared --config flag to a parser and, optionally, its subparsers.

    argparse lets a subparser's default overwrite the parent's parsed value,
    so subparsers get default=SUPPRESS. Either position then works:
    `script.py --config X sub ...` and `script.py sub --config X ...`.
    Read it with getattr(args, "config", None).
    """
    import argparse
    help_text = ("Config file (default: $GUIDE_MAKER_CONFIG, then .guide-maker/config.yaml "
                 "walking up from the working directory, then ~/.config/guide-maker/)")
    parser.add_argument("--config", default=None, help=help_text)
    for sub in (subparsers or []):
        sub.add_argument("--config", default=argparse.SUPPRESS, help=help_text)
    return parser


if __name__ == "__main__":
    import argparse
    _parser = argparse.ArgumentParser(
        description="Load the guide-maker config and print its static validation")
    _parser.add_argument("path", nargs="?", default=None, help="Config file (optional)")
    add_config_arg(_parser)
    _args = _parser.parse_args()
    cfg = load_config(_args.path or _args.config)
    print(f"config: {cfg.get('_path')} (source: {cfg.get('_source')})")
    print(f"project: {project_dir(cfg)}")
    for level, message in validate(cfg):
        print(f"{level:<4} {message}")
