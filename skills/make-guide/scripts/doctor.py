#!/usr/bin/env python3
"""Health check for the guide-maker install. Run it before every session.

Usage:
    doctor.py [--config PATH] [--offline] [--json]
    doctor.py --print-paths [--json]
    doctor.py --init [--project DIR | --home] [--from OLD_CONFIG] [--force]
    doctor.py --list-databases [--json] [--offline]
    doctor.py --migrate-config

Thirteen checks, each OK | WARN | FAIL | SKIP:
     1. config file found, schema version, static validation
     2. Python >= 3.9, PyYAML, Pillow
     3. Notion token (env NOTION_API_KEY, ~/.config/notion/api_key, config)
     4. Notion databases reachable, required properties present (incl. Graphic)
     5. notion.public_domain set (public-URL check for DMs)
     6. yt-dlp on PATH or tools.ytdlp_path, version >= 2026.07.04
     7. sibling skills (topic-finder, graphics-maker, dm-automation) and their configs
     8. provider keys for the providers the config selects
     9. fonts resolve and render the CTA string
    10. copy.cta_mode (warns with the impression numbers when it is copy)
    11. workflow.work_dir writable
    12. config.yaml holds no inline secret, or is ignored by git in its project
    13. which voice / examples / top-performers / banned-words file is in use
        (project override in .guide-maker/, or the shipped one)

--offline skips 4 and the network part of 3 (SKIP, never FAIL).
--json prints {"checks": [...], "config": {...}, "paths": {...}}.
--print-paths prints what was resolved: skill dir, skills root, project dir,
    config path and config_source (arg | env | project | home | legacy | none),
    siblings (make-guide, topic-finder, graphics-maker, dm-automation). --json
    for the machine-readable form.
--init writes the .guide-maker/ skeleton: config.yaml (from config.example.yaml,
    or a copy of --from OLD), topic-finder/ with the example source lists renamed
    for real use, formats/, state/, and a .gitignore. --project DIR picks the
    project (default: the first ancestor of cwd holding .guide-maker/, else cwd);
    --home writes ~/.config/guide-maker/ instead. --from OLD also moves an old
    format-usage-log.jsonl into state/, copies non-example topic-finder configs,
    and copies any voice / examples / top-performers file you edited under the
    old skill's references/. Refuses to overwrite config.yaml without --force.
--list-databases prints the Notion databases shared with the integration
    (id, title, property count) so you can pick ids instead of pasting them.
--migrate-config prints the current config as a v2 YAML file and exits.

Exit 1 when any check is FAIL, else 0.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import (load_config, cfg_get, secret, secret_source, validate,  # noqa: E402
                     skill_dir, skills_root, sibling, migrate_v1, add_config_arg,
                     resource, resource_source, project_dir, is_v1,
                     RESOURCES, PROJECT_DIRNAME, SCHEMA_VERSION, DEFAULTS, _read_file,
                     _deep_merge)

MIN_YTDLP = (2026, 7, 4)
CTA_STRING = 'COMMENT "SAMPLE" TO GET IT FOR FREE'
GUIDE_DB_PROPS = {"Guide Title": "title", "Keyword": "rich_text", "Type": "select",
                  "Week": "date", "Status": "select"}
BOARD_PROPS = {"Title": "title", "Post Date": "date", "Type": "select", "Status": "select",
               "Keyword": "rich_text", "Guide Link": "url", "Graphic": "files"}
BOARD_OPTIONAL = {"Account": "select", "Day": "select", "Notes": "rich_text"}


class Checks:
    def __init__(self):
        self.rows = []

    def add(self, level, name, message):
        self.rows.append({"level": level, "name": name, "message": message})

    def ok(self, name, msg):
        self.add("OK", name, msg)

    def warn(self, name, msg):
        self.add("WARN", name, msg)

    def fail(self, name, msg):
        self.add("FAIL", name, msg)

    def skip(self, name, msg):
        self.add("SKIP", name, msg)

    @property
    def failed(self):
        return any(r["level"] == "FAIL" for r in self.rows)


def _sibling_path(name):
    try:
        return sibling(name), None
    except FileNotFoundError as exc:
        return None, str(exc)


SIBLINGS = ("make-guide", "topic-finder", "graphics-maker", "dm-automation")
TOPIC_FINDER_FILES = ("youtube-channels", "subreddits", "x-accounts", "topics")


def resolved_paths(cfg=None):
    """What the loader resolved. cfg is None when no config was found."""
    cfg = cfg or {}
    config_path = cfg.get("_path", "") or ""
    paths = {
        "skill_dir": str(skill_dir()),
        "skills_root": str(skills_root()),
        "repo_root": str(skills_root().parent),
        "project_dir": str(project_dir(cfg)),
        "config": config_path,
        "config_path": config_path,
        "config_source": cfg.get("_source") or "none",
        "siblings": {},
    }
    for name in SIBLINGS:
        p, _ = _sibling_path(name)
        paths["siblings"][name] = str(p) if p else None
        if name != "make-guide":
            paths[name] = str(p) if p else ""    # flat keys kept from v2
    paths["ytdlp"] = shutil.which("yt-dlp") or ""
    return paths


def _print_paths_text(paths):
    for key, value in paths.items():
        if key == "siblings":
            for name, path in value.items():
                print(f"{'sibling ' + name:<24} {path or '(not found)'}")
        elif key in ("topic-finder", "graphics-maker", "dm-automation"):
            continue
        else:
            print(f"{key:<24} {value or '(not found)'}")
    if paths["config_source"] == "legacy":
        print("note: the config sits inside the skill folder (deprecated); "
              "run doctor.py --init --from <that file>")
    elif paths["config_source"] == "none":
        print("note: no config found; run doctor.py --init --project /path/to/project "
              "or /setup-guide-maker")


# --- secrets in the file itself ---------------------------------------------

def inline_secrets(raw):
    """Dotted keys whose value in the config FILE is a non-empty key."""
    out = []
    if not isinstance(raw, dict):
        return out
    if is_v1(raw):
        for key in ("notion_api_key", "kieai_api_key"):
            if str(raw.get(key) or "").strip():
                out.append(key)
        return out
    if str((raw.get("notion") or {}).get("api_key") or "").strip():
        out.append("notion.api_key")
    for name, block in (raw.get("providers") or {}).items():
        if isinstance(block, dict) and str(block.get("api_key") or "").strip():
            out.append(f"providers.{name}.api_key")
    return out


def git_ignores(path):
    """True | False | None (not a git checkout, or git missing)."""
    path = Path(path)
    try:
        proc = subprocess.run(["git", "-C", str(path.parent), "check-ignore", "-q", str(path)],
                              capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if proc.returncode == 0:
        return True
    if proc.returncode == 1:
        return False
    return None


def _ytdlp_version(binary):
    try:
        out = subprocess.run([binary, "--version"], capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, str(exc)
    ver = (out.stdout or "").strip().splitlines()[0] if out.stdout else ""
    return ver, None


def _version_tuple(ver):
    parts = []
    for chunk in ver.split("."):
        digits = "".join(ch for ch in chunk if ch.isdigit())
        parts.append(int(digits) if digits else 0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def run_checks(cfg, offline):
    c = Checks()

    # 1. config
    path = cfg.get("_path", "")
    source = cfg.get("_source") or "unknown"
    if cfg.get("_v1"):
        c.warn("config", f"{path} (source: {source}): deprecated v1 flat format loaded through "
                         "the shim; run doctor.py --migrate-config")
    elif source == "legacy":
        c.warn("config", f"{path} (source: legacy, schema_version {cfg_get(cfg, 'schema_version')}): "
                         "config inside the skill folder is deprecated; run doctor.py --init "
                         f"--from {path} or /setup-guide-maker")
    else:
        c.ok("config", f"{path} (source: {source}, schema_version {cfg_get(cfg, 'schema_version')})")
    for level, message in validate(cfg):
        if level == "FAIL":
            c.fail("config", message)
        elif level == "WARN":
            c.warn("config", message)

    # 2. deps
    py = sys.version_info
    if py < (3, 9):
        c.fail("deps", f"Python {py.major}.{py.minor}; 3.9+ required")
    else:
        c.ok("deps", f"Python {py.major}.{py.minor}.{py.micro}")
    try:
        import yaml  # noqa: F401
        c.ok("deps", "PyYAML installed")
    except ImportError:
        c.warn("deps", "PyYAML missing (pip install pyyaml); config.json still works")
    try:
        import PIL  # noqa: F401
        c.ok("deps", f"Pillow {PIL.__version__}")
    except ImportError:
        c.fail("deps", "Pillow missing (pip install pillow); covers and CTA bars need it")

    # 3. notion token
    token = secret(cfg, "notion")
    src = secret_source(cfg, "notion")
    if token:
        c.ok("notion-token", f"present (from {src})")
    elif offline:
        c.warn("notion-token", "no Notion token found (env NOTION_API_KEY, "
                               "~/.config/notion/api_key, or notion.api_key); publishing needs it")
    else:
        c.fail("notion-token", "no Notion token found (env NOTION_API_KEY, "
                               "~/.config/notion/api_key, or notion.api_key)")

    # 4. databases
    guide_db = cfg_get(cfg, "notion.guide_database_id", "")
    board_db = cfg_get(cfg, "notion.content_board_database_id", "")
    if offline:
        c.skip("notion-db", "offline; database checks skipped")
    elif not token:
        c.skip("notion-db", "no token; database checks skipped")
    else:
        import _notion
        _notion.init(cfg)
        for label, db_id, required, optional in (
                ("guide DB", guide_db, GUIDE_DB_PROPS, {}),
                ("content board", board_db, BOARD_PROPS, BOARD_OPTIONAL)):
            if not db_id:
                (c.warn if label == "guide DB" else c.skip)(
                    "notion-db", f"{label}: no id configured")
                continue
            try:
                db = _notion.retrieve_database(db_id)
            except Exception as exc:
                c.fail("notion-db", f"{label} {db_id}: not reachable ({str(exc)[:120]}). "
                                    "Share the database with your integration.")
                continue
            props = db.get("properties", {})
            missing = [f"{n} ({t})" for n, t in required.items()
                       if n not in props or props[n].get("type") != t]
            if missing:
                c.fail("notion-db", f"{label}: missing or wrong-typed properties: {', '.join(missing)}")
            else:
                c.ok("notion-db", f"{label}: reachable, {len(required)} required properties present")
            if label == "guide DB":
                options = {o.get("name") for o in props.get("Type", {}).get("select", {}).get("options", [])}
                want = set(cfg_get(cfg, "notion.guide_types") or [])
                lacking = sorted(want - options)
                if lacking:
                    c.warn("notion-db", f"guide DB Type select lacks: {', '.join(lacking)}")
            else:
                options = {o.get("name") for o in props.get("Status", {}).get("select", {}).get("options", [])}
                if "Draft" not in options:
                    c.warn("notion-db", "content board Status select has no 'Draft' option")

    # 5. public domain
    domain = cfg_get(cfg, "notion.public_domain", "")
    if domain:
        c.ok("public-domain", f"notion.public_domain = {domain}")
    else:
        c.warn("public-domain", "notion.public_domain empty; the public-URL check for DMs is skipped")

    # 6. yt-dlp
    binary = cfg_get(cfg, "tools.ytdlp_path", "") or shutil.which("yt-dlp") or ""
    if not binary or not (os.path.exists(binary) or shutil.which(binary)):
        c.warn("yt-dlp", "yt-dlp not found (pip install -U yt-dlp); transcripts and the "
                         "YouTube scan need it")
    else:
        ver, err = _ytdlp_version(binary)
        if err or not ver:
            c.warn("yt-dlp", f"{binary}: could not read version ({err})")
        elif _version_tuple(ver) < MIN_YTDLP:
            c.warn("yt-dlp", f"{ver} is older than {'.'.join(map(str, MIN_YTDLP))}; "
                             "topic-finder --flat mode needs the newer one")
        else:
            c.ok("yt-dlp", f"{ver} at {binary}")

    # 7. siblings
    graphics_provider = cfg_get(cfg, "graphics.provider", "none")
    dm_provider = cfg_get(cfg, "dm_tool.provider", "manual")
    for name, needed, why in (
            ("topic-finder", True, "Phase 0 topic research"),
            ("graphics-maker", graphics_provider != "none", "post graphic with the CTA band"),
            ("dm-automation", dm_provider != "manual", "DM scheduling")):
        p, err = _sibling_path(name)
        if p and (p / "SKILL.md").exists():
            note = ""
            if name == "topic-finder":
                cfg_dir = p / "config"
                real = [f for f in cfg_dir.glob("*.json") if ".example." not in f.name] if cfg_dir.exists() else []
                if not real:
                    note = "; only .example.json configs, copy and fill them"
            c.ok("siblings", f"{name} at {p}{note}")
        elif needed:
            c.warn("siblings", f"{name} not installed ({why} unavailable). {err or ''}".strip())
        else:
            c.skip("siblings", f"{name} not installed; not needed with the current config")

    # 8. provider keys
    wants = []
    if graphics_provider in ("kieai", "openai"):
        wants.append((graphics_provider, True, f"graphics.provider = {graphics_provider}"))
    if cfg_get(cfg, "cover.mode") == "ai":
        wants.append(("kieai", True, "cover.mode = ai"))
    sources = cfg_get(cfg, "topic_finder.sources") or []
    if "reddit" in sources or "x" in sources:
        wants.append(("apify", False, "topic_finder.sources includes reddit or x"))
    if dm_provider == "leadshark":
        wants.append(("leadshark", True, "dm_tool.provider = leadshark"))
    seen = set()
    for name, required, why in wants:
        if name in seen:
            continue
        seen.add(name)
        if secret(cfg, name):
            c.ok("providers", f"{name} key present (from {secret_source(cfg, name)}); {why}")
        elif required:
            c.fail("providers", f"{name} key missing; {why}")
        else:
            c.warn("providers", f"{name} key missing; {why}")
    if not wants:
        c.ok("providers", "no paid provider selected; Pillow paths only")

    # 9. fonts
    try:
        import banner_generator as bg
        from PIL import Image, ImageDraw
        bold, _ = bg.resolve_font_path(True)
        regular, _ = bg.resolve_font_path(False)
        if bold and regular:
            font = bg.load_font(40, bold=True)
            img = Image.new("RGB", (1200, 120), "white")
            ImageDraw.Draw(img).text((10, 10), CTA_STRING, fill="black", font=font)
            c.ok("fonts", f"bold {bold}, regular {regular}; CTA string renders")
        else:
            c.warn("fonts", "no TrueType font resolved; assets/fonts/Inter-*.ttf missing and no "
                            "platform font; covers fall back to Pillow's bitmap font")
    except Exception as exc:
        c.warn("fonts", f"font check failed: {exc}")

    # 10. cta mode
    mode = cfg_get(cfg, "copy.cta_mode", "graphic")
    if mode == "copy":
        c.warn("cta-mode", "copy.cta_mode = copy: the keyword goes in the post text. Evidence for "
                           "graphic: same asset 95 impressions with it, 11,432 without; one account "
                           "62,000 to 43. See references/strategy/cta-evidence.md")
    else:
        c.ok("cta-mode", "copy.cta_mode = graphic (keyword lives only in the post graphic)")

    # 11. work dir
    work_dir = Path(os.path.expanduser(cfg_get(cfg, "workflow.work_dir") or "/tmp/guide-maker"))
    try:
        work_dir.mkdir(parents=True, exist_ok=True)
        probe = work_dir / ".doctor-probe"
        probe.write_text("ok")
        probe.unlink()
        c.ok("work-dir", f"{work_dir} writable")
    except OSError as exc:
        c.fail("work-dir", f"{work_dir} not writable: {exc}")

    # 13. reference overrides in use
    for key in RESOURCES:
        try:
            rpath = resource(cfg, key)
            src = resource_source(cfg, key)
        except Exception as exc:  # a bad copy.banned_words_file, for instance
            c.warn("resources", f"{key}: could not resolve ({exc})")
            continue
        if not rpath.exists():
            c.warn("resources", f"{key}: {rpath} does not exist")
        elif src == "override":
            c.ok("resources", f"{key}: project override {rpath}")
        else:
            c.ok("resources", f"{key}: shipped {rpath.name} (override with .guide-maker/{RESOURCES[key][0]})")

    # 12. inline secrets vs git
    cfg_path = Path(path) if path else None
    try:
        raw = _read_file(cfg_path) if cfg_path and cfg_path.exists() else {}
    except Exception:
        raw = {}
    inline = inline_secrets(raw)
    if not inline:
        c.ok("gitignore", f"{cfg_path.name if cfg_path else 'config'} holds no inline API key "
                          "(database ids only); safe to commit or not, your call")
    else:
        ignored = git_ignores(cfg_path)
        if ignored is True:
            c.ok("gitignore", f"{cfg_path} holds {', '.join(inline)} and is ignored by git")
        elif ignored is False:
            c.warn("gitignore", f"{cfg_path} holds {', '.join(inline)} and is NOT ignored by git; "
                                f"add config.yaml to {cfg_path.parent / '.gitignore'} or move the "
                                "key to an env var or key file")
        else:
            c.ok("gitignore", f"{cfg_path} holds {', '.join(inline)}; not inside a git checkout, "
                              "nothing to commit it with")
    return c


def print_migrated(config_path):
    raw = _read_file(config_path)
    from _config import is_v1
    data = migrate_v1(raw) if is_v1(raw) else dict(raw)
    data["schema_version"] = SCHEMA_VERSION
    data.pop("_path", None)
    data.pop("_v1", None)
    ordered = {"schema_version": SCHEMA_VERSION}
    for key in DEFAULTS:
        if key in data and key != "schema_version":
            ordered[key] = data[key]
    for key, value in data.items():
        if key not in ordered:
            ordered[key] = value
    try:
        import yaml
        print("# guide-maker config, migrated to schema_version 2.")
        print("# Every key is documented in config.example.yaml; unset keys use its defaults.")
        print(yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, default_flow_style=False))
    except ImportError:
        print("schema_version: 2")
        print("# PyYAML is not installed; the rest is JSON (valid YAML). Save it as config.json.")
        print(json.dumps(ordered, indent=2, ensure_ascii=False))


# --- --init -------------------------------------------------------------------

def _migrated_yaml_text(raw):
    """A v2 YAML document for a v1 or JSON config (comments cannot be kept)."""
    data = migrate_v1(raw) if is_v1(raw) else dict(raw)
    data["schema_version"] = SCHEMA_VERSION
    for key in ("_path", "_v1", "_source"):
        data.pop(key, None)
    ordered = {"schema_version": SCHEMA_VERSION}
    for key in DEFAULTS:
        if key in data and key != "schema_version":
            ordered[key] = data[key]
    for key, value in data.items():
        if key not in ordered:
            ordered[key] = value
    try:
        import yaml
        return ("# guide-maker config, migrated to schema_version 2 by doctor.py --init.\n"
                "# Every key is documented in config.example.yaml; unset keys use its defaults.\n"
                + yaml.safe_dump(ordered, sort_keys=False, allow_unicode=True, default_flow_style=False))
    except ImportError:
        return None


def _set_state_path(text, state_dir):
    """Point paths.state at state_dir inside a YAML config text (comments kept)."""
    import re
    pattern = re.compile(r'^(paths:\s*\n(?:[ \t]+.*\n)*?)([ \t]+state:[ \t]*)("[^"]*"|\'[^\']*\'|\S*)(.*)$', re.M)
    if pattern.search(text):
        return pattern.sub(lambda m: f'{m.group(1)}{m.group(2)}"{state_dir}"{m.group(4)}', text, count=1)
    return text.rstrip("\n") + f'\n\n# Written by doctor.py --init --home: state for every project.\npaths:\n  state: "{state_dir}"\n'


def init_layout(target, from_old=None, force=False, home=False, log=print):
    """Write the config home skeleton into `target` (a .guide-maker/ folder, or
    ~/.config/guide-maker when home is True). Returns the list of paths written."""
    written = []

    def wrote(action, path):
        written.append(str(path))
        log(f"  {action:<6} {path}")

    target = Path(target).expanduser().resolve()
    target.mkdir(parents=True, exist_ok=True)
    example = skill_dir() / "config.example.yaml"
    config_out = target / "config.yaml"
    old_path = Path(from_old).expanduser().resolve() if from_old else None
    if old_path and not old_path.is_file():
        raise SystemExit(f"--from {old_path}: not a file")

    # config.yaml
    if config_out.exists() and not force:
        raise SystemExit(f"{config_out} exists; pass --force to overwrite it")
    raw_old = {}
    if old_path:
        raw_old = _read_file(old_path)
        if old_path.suffix.lower() == ".json" or is_v1(raw_old):
            text = _migrated_yaml_text(raw_old)
            if text is None:                       # no PyYAML: keep JSON
                config_out = target / "config.json"
                data = migrate_v1(raw_old) if is_v1(raw_old) else dict(raw_old)
                data["schema_version"] = SCHEMA_VERSION
                config_out.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
                wrote("write", config_out)
                text = None
        else:
            text = old_path.read_text(encoding="utf-8")
    else:
        text = example.read_text(encoding="utf-8")
    if text is not None:
        if home:
            text = _set_state_path(text, str(target / "state"))
        config_out.write_text(text, encoding="utf-8")
        wrote("write" if not old_path else "copy", config_out)

    # topic-finder/: example lists renamed for real use, then any real ones from the old install
    tf_dir = target / "topic-finder"
    tf_dir.mkdir(exist_ok=True)
    src_dirs = []
    try:
        src_dirs.append(sibling("topic-finder") / "config")
    except FileNotFoundError:
        pass
    for src_dir in src_dirs:
        for name in TOPIC_FINDER_FILES:
            src = src_dir / f"{name}.example.json"
            dst = tf_dir / f"{name}.json"
            if src.exists() and not dst.exists():
                shutil.copy2(src, dst)
                wrote("seed", dst)
    if old_path:
        old_tf = [old_path.parent.parent / "topic-finder" / "config",
                  old_path.parent / "topic-finder" / "config", old_path.parent / "topic-finder"]
        configured = str(cfg_get(_deep_merge(DEFAULTS, migrate_v1(raw_old) if is_v1(raw_old) else raw_old),
                                 "topic_finder.path") or "")
        if configured:
            old_tf.insert(0, Path(configured).expanduser() / "config")
        for src_dir in old_tf:
            if not src_dir.is_dir():
                continue
            for src in sorted(src_dir.glob("*.json")):
                if ".example." in src.name:
                    continue
                dst = tf_dir / src.name
                if dst.exists() and not force and dst.read_bytes() == src.read_bytes():
                    continue
                shutil.copy2(src, dst)
                wrote("copy", dst)
            break

    # formats/ and state/
    for name in ("formats", "state"):
        d = target / name
        if not d.exists():
            d.mkdir()
            wrote("mkdir", d)

    # old state and edited references
    if old_path:
        for cand in (old_path.parent / "format-usage-log.jsonl",
                     old_path.parent.parent / "graphics-maker" / "format-usage-log.jsonl"):
            if cand.is_file():
                dst = target / "state" / "format-usage-log.jsonl"
                if dst.exists():
                    with open(dst, "a", encoding="utf-8") as fh:
                        fh.write(cand.read_text(encoding="utf-8"))
                    cand.unlink()
                    wrote("merge", dst)
                else:
                    shutil.move(str(cand), str(dst))
                    wrote("move", dst)
        old_skill = old_path.parent
        if old_skill.resolve() != skill_dir().resolve():
            for key in ("voice", "examples", "top_performers"):
                override_name, shipped_rel = RESOURCES[key]
                edited = old_skill / shipped_rel
                shipped = skill_dir() / shipped_rel
                if edited.is_file() and (not shipped.is_file() or edited.read_bytes() != shipped.read_bytes()):
                    dst = target / override_name
                    if dst.exists() and not force:
                        log(f"  keep   {dst} (exists; --force to replace)")
                        continue
                    shutil.copy2(edited, dst)
                    wrote("copy", dst)

    # .gitignore: state always; config.yaml only when a key is inlined
    gi = target / ".gitignore"
    lines = ["state/"]
    written_raw = raw_old
    if not old_path and config_out.exists():
        try:
            written_raw = _read_file(config_out)
        except ImportError:          # no PyYAML; the example carries no key anyway
            written_raw = {}
    if inline_secrets(written_raw):
        lines.append(config_out.name)
    existing = gi.read_text(encoding="utf-8").splitlines() if gi.exists() else []
    merged = existing + [ln for ln in lines if ln not in existing]
    if merged != existing:
        gi.write_text("\n".join(merged) + "\n", encoding="utf-8")
        wrote("write", gi)
    return written


def run_init(args):
    if args.home:
        target = Path("~/.config/guide-maker").expanduser()
        label = "home"
    elif args.project:
        target = Path(args.project).expanduser().resolve() / PROJECT_DIRNAME
        label = "project"
    else:
        target = project_dir() / PROJECT_DIRNAME
        label = "project"
    print(f"Writing the {label} config home at {target}")
    written = init_layout(target, from_old=getattr(args, "from_old", None), force=args.force, home=args.home)
    if args.json:
        print(json.dumps({"target": str(target), "written": written}, indent=2))
    print(f"\nDone. Open {target / 'config.yaml'} and fill in the REQUIRED Notion block, "
          f"then run:\n  python3 {Path(__file__).resolve()} --config {target / 'config.yaml'}")
    if label == "project":
        print(f"(or just run the doctor from inside {target.parent}; the config is found by walking up)")
    if getattr(args, "from_old", None):
        print(f"When the doctor is green, delete the old file: {Path(args.from_old).expanduser().resolve()}")


# --- --list-databases ---------------------------------------------------------

def list_databases(cfg, offline, as_json):
    if offline:
        if as_json:
            print(json.dumps({"skipped": "offline", "databases": []}))
        else:
            print("SKIP list-databases  offline; nothing fetched")
        return 0
    token = secret(cfg, "notion")
    if not token:
        msg = ("no Notion token (env NOTION_API_KEY, ~/.config/notion/api_key, or notion.api_key); "
               "create an integration at https://www.notion.so/my-integrations and share your "
               "databases with it")
        if as_json:
            print(json.dumps({"error": msg, "databases": []}))
        else:
            print(f"FAIL list-databases  {msg}")
        return 1
    import _notion
    _notion.init(cfg, token=token)
    try:
        results = _notion.paginate("/search", {"filter": {"property": "object", "value": "database"},
                                               "page_size": 100}, method="POST")
    except Exception as exc:
        if as_json:
            print(json.dumps({"error": str(exc)[:300], "databases": []}))
        else:
            print(f"FAIL list-databases  {str(exc)[:300]}")
        return 1
    rows = []
    for db in results:
        if db.get("object") != "database":
            continue
        rows.append({
            "id": str(db.get("id", "")).replace("-", ""),
            "title": _notion.plain_text(db.get("title", [])) or "(untitled)",
            "properties": len(db.get("properties", {}) or {}),
            "property_names": sorted((db.get("properties", {}) or {}).keys()),
            "url": db.get("url", ""),
        })
    rows.sort(key=lambda r: r["title"].lower())
    if as_json:
        print(json.dumps(rows, indent=2, ensure_ascii=False))
    elif not rows:
        print("No databases are shared with this integration. In Notion, open the database, "
              "click ... > Connections, and add your integration.")
    else:
        for r in rows:
            print(f"{r['id']}  {r['title']}  (properties: {r['properties']})")
        print(f"\n{len(rows)} database(s). Guide DB needs Guide Title, Keyword, Type, Week, Status; "
              "the Content Board needs Title, Post Date, Type, Status, Keyword, Guide Link, Graphic.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="guide-maker health check")
    parser.add_argument("--offline", action="store_true", help="Skip network checks")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument("--print-paths", action="store_true", help="Print resolved paths and exit")
    parser.add_argument("--migrate-config", action="store_true",
                        help="Print the config as a v2 YAML file and exit")
    parser.add_argument("--list-databases", action="store_true",
                        help="List the Notion databases shared with the integration and exit")
    parser.add_argument("--init", action="store_true",
                        help="Write the .guide-maker/ skeleton (config, topic sources, formats, state)")
    parser.add_argument("--project", default=None, metavar="DIR",
                        help="With --init: the project folder that gets .guide-maker/ (default: cwd or its "
                             "first ancestor that already has one)")
    parser.add_argument("--home", action="store_true",
                        help="With --init: write ~/.config/guide-maker/ instead of a project folder")
    parser.add_argument("--from", dest="from_old", default=None, metavar="OLD_CONFIG",
                        help="With --init: copy this v1/v2 config (and the state and edited references "
                             "next to it) instead of starting from config.example.yaml")
    parser.add_argument("--force", action="store_true", help="With --init: overwrite an existing config")
    add_config_arg(parser)
    args = parser.parse_args()

    if args.init:
        if args.home and args.project:
            parser.error("--home and --project are exclusive")
        run_init(args)
        sys.exit(0)

    config_path = getattr(args, "config", None)
    try:
        cfg = load_config(config_path)
    except FileNotFoundError as exc:
        if args.print_paths:
            paths = resolved_paths(None)
            if args.json:
                print(json.dumps(paths, indent=2))
            else:
                _print_paths_text(paths)
            sys.exit(0)
        if args.list_databases:
            # the token can come from the environment or a key file; no config needed
            sys.exit(list_databases(_deep_merge(DEFAULTS, {}), args.offline, args.json))
        msg = str(exc)
        if args.json:
            print(json.dumps({"checks": [{"level": "FAIL", "name": "config", "message": msg}],
                              "config": None, "paths": resolved_paths(None)}, indent=2))
        else:
            print(f"FAIL config          {msg}")
        sys.exit(1)

    if args.migrate_config:
        print_migrated(cfg["_path"])
        sys.exit(0)

    if args.list_databases:
        sys.exit(list_databases(cfg, args.offline, args.json))

    paths = resolved_paths(cfg)
    if args.print_paths:
        if args.json:
            print(json.dumps(paths, indent=2))
        else:
            _print_paths_text(paths)
        sys.exit(0)

    checks = run_checks(cfg, args.offline)
    public_cfg = {k: v for k, v in cfg.items() if not k.startswith("_")}
    if args.json:
        print(json.dumps({"checks": checks.rows, "config": public_cfg, "paths": paths},
                         indent=2, ensure_ascii=False, default=str))
    else:
        width = max(len(r["name"]) for r in checks.rows)
        for r in checks.rows:
            print(f"{r['level']:<4} {r['name']:<{width}}  {r['message']}")
        counts = {}
        for r in checks.rows:
            counts[r["level"]] = counts.get(r["level"], 0) + 1
        print("\n" + ", ".join(f"{k} {v}" for k, v in sorted(counts.items())))
        if checks.failed:
            print("Fix every FAIL line before running the pipeline.")
    sys.exit(1 if checks.failed else 0)


if __name__ == "__main__":
    main()
