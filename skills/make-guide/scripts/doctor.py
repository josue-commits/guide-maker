#!/usr/bin/env python3
"""Health check for the guide-maker install. Run it before every session.

Usage:
    doctor.py [--config PATH] [--offline] [--json] [--print-paths] [--migrate-config]

Twelve checks, each OK | WARN | FAIL | SKIP:
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
    12. .gitignore at the repo root covers config.yaml

--offline skips 4 and the network part of 3 (SKIP, never FAIL).
--json prints {"checks": [...], "config": {...}, "paths": {...}}.
--print-paths prints what was resolved (skill dir, skills root, config, siblings).
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
                     SCHEMA_VERSION, DEFAULTS, _read_file)

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


def resolved_paths(config_path):
    paths = {
        "skill_dir": str(skill_dir()),
        "skills_root": str(skills_root()),
        "repo_root": str(skills_root().parent),
        "config": config_path or "",
    }
    for name in ("topic-finder", "graphics-maker", "dm-automation"):
        p, _ = _sibling_path(name)
        paths[name] = str(p) if p else ""
    paths["ytdlp"] = shutil.which("yt-dlp") or ""
    return paths


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
    if cfg.get("_v1"):
        c.warn("config", f"{path}: deprecated v1 flat format loaded through the shim; "
                         "run doctor.py --migrate-config")
    else:
        c.ok("config", f"{path} (schema_version {cfg_get(cfg, 'schema_version')})")
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

    # 12. gitignore
    repo_root = skills_root().parent
    gi = repo_root / ".gitignore"
    if gi.exists() and "config.yaml" in gi.read_text(encoding="utf-8"):
        c.ok("gitignore", f"{gi} ignores config.yaml")
    else:
        c.warn("gitignore", f"{gi} missing or does not ignore config.yaml; your ids and keys "
                            "could be committed")
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


def main():
    parser = argparse.ArgumentParser(description="guide-maker health check")
    parser.add_argument("--offline", action="store_true", help="Skip network checks")
    parser.add_argument("--json", action="store_true", help="Machine-readable output")
    parser.add_argument("--print-paths", action="store_true", help="Print resolved paths and exit")
    parser.add_argument("--migrate-config", action="store_true",
                        help="Print the config as a v2 YAML file and exit")
    add_config_arg(parser)
    args = parser.parse_args()

    config_path = getattr(args, "config", None)
    try:
        cfg = load_config(config_path)
    except FileNotFoundError as exc:
        if args.print_paths:
            print(json.dumps(resolved_paths(""), indent=2))
            sys.exit(0)
        msg = str(exc)
        if args.json:
            print(json.dumps({"checks": [{"level": "FAIL", "name": "config", "message": msg}],
                              "config": None, "paths": resolved_paths("")}, indent=2))
        else:
            print(f"FAIL config          {msg}")
        sys.exit(1)

    if args.migrate_config:
        print_migrated(cfg["_path"])
        sys.exit(0)

    paths = resolved_paths(cfg.get("_path", ""))
    if args.print_paths:
        for key, value in paths.items():
            print(f"{key:<16} {value or '(not found)'}")
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
