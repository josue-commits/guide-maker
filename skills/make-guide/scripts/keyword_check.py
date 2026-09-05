#!/usr/bin/env python3
"""Check a lead-magnet keyword: shape first, then collisions.

Usage:
    keyword_check.py KEYWORD [--config PATH] [--offline] [--json]
    keyword_check.py --list [--config PATH] [--json]

Shape (offline, always first): 3 to 12 ASCII capital letters, ^[A-Z]{3,12}$.
The DM tool matches the comment text against this exact string and the
graphic renders it, so one word, all caps, no digits, no punctuation.

Collisions (network, skipped with --offline):
    Content Board  `Keyword` property equals the keyword (any case)
    Guide DB       `Keyword` property equals it, or a guide title contains it as a word
    DM tool        dm_tool.provider is not manual and the dm-automation sibling reports
                   the keyword as an existing automation trigger

--list prints every keyword and title the checks would compare against, for
the EXCLUDE list you pass to the writer agent.

Exit 0 free, 1 bad shape or collision, 2 warnings only (title contains the word).
"""

import argparse
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import load_config, cfg_get, sibling, add_config_arg  # noqa: E402

SHAPE = re.compile(r"^[A-Z]{3,12}$")


def check_shape(keyword):
    """Return (ok, message)."""
    if SHAPE.match(keyword or ""):
        return True, f"{keyword}: shape ok ([A-Z]{{3,12}})"
    hint = ""
    letters = re.sub(r"[^A-Za-z]", "", keyword or "")
    if letters and 3 <= len(letters) <= 12:
        hint = f"; did you mean {letters.upper()}?"
    return False, (f"{keyword!r} is not a valid keyword: 3-12 capital letters only, "
                   f"no digits, spaces or punctuation{hint}")


def _existing(cfg):
    """(board_keywords, guide_keywords, guide_titles) from Notion."""
    import _notion
    _notion.init(cfg)
    board, guide_kw, titles = [], [], []
    board_db = cfg_get(cfg, "notion.content_board_database_id", "")
    guide_db = cfg_get(cfg, "notion.guide_database_id", "")
    if board_db:
        for page in _notion.query_database(board_db):
            kw = _notion.prop_text(page, "Keyword").strip()
            if kw:
                board.append((kw, _notion.title_of(page, "Title")))
    if guide_db:
        for page in _notion.query_database(guide_db):
            kw = _notion.prop_text(page, "Keyword").strip()
            title = _notion.title_of(page, "Guide Title")
            if kw:
                guide_kw.append((kw, title))
            if title:
                titles.append(title)
    return board, guide_kw, titles


def _dm_tool_keywords(cfg):
    """Keywords the DM tool already has automations for, via the sibling CLI."""
    provider = cfg_get(cfg, "dm_tool.provider", "manual")
    if provider == "manual":
        return None, "dm_tool.provider is manual; nothing to compare"
    try:
        dm_dir = sibling("dm-automation")
    except FileNotFoundError as exc:
        return None, str(exc)
    cli = dm_dir / "scripts" / "dm_cli.py"
    if not cli.exists():
        return None, f"{cli} not found"
    cmd = [sys.executable, str(cli), "keywords", "--json"]
    if cfg.get("_path"):
        cmd += ["--config", cfg["_path"]]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, f"dm_cli.py keywords failed: {exc}"
    if out.returncode != 0:
        return None, f"dm_cli.py keywords exited {out.returncode}: {out.stderr.strip()[:200]}"
    try:
        data = json.loads(out.stdout or "[]")
    except json.JSONDecodeError:
        return None, "dm_cli.py keywords did not return JSON"
    if isinstance(data, dict):
        data = data.get("keywords", [])
    words = []
    for item in data:
        if isinstance(item, str):
            words.append(item)
        elif isinstance(item, dict):
            words.append(item.get("keyword") or item.get("name") or "")
    return [w for w in words if w], f"{len(words)} keywords from the DM tool"


def main():
    parser = argparse.ArgumentParser(description="Keyword shape and collision check")
    parser.add_argument("keyword", nargs="?", help="The keyword to check")
    parser.add_argument("--offline", action="store_true", help="Shape check only, no network")
    parser.add_argument("--list", action="store_true", help="Print existing keywords and titles")
    parser.add_argument("--json", action="store_true")
    add_config_arg(parser)
    args = parser.parse_args()

    if not args.keyword and not args.list:
        parser.print_help()
        sys.exit(1)

    result = {"keyword": args.keyword, "shape_ok": None, "findings": [], "exit": 0}
    findings = result["findings"]

    if args.keyword:
        ok, msg = check_shape(args.keyword)
        result["shape_ok"] = ok
        findings.append({"level": "OK" if ok else "FAIL", "check": "shape", "message": msg})
        if not ok:
            result["exit"] = 1
            _emit(result, args.json)
            sys.exit(1)

    if args.offline:
        findings.append({"level": "SKIP", "check": "collisions", "message": "offline; collision check skipped"})
        _emit(result, args.json)
        sys.exit(0)

    try:
        cfg = load_config(getattr(args, "config", None))
    except FileNotFoundError as exc:
        findings.append({"level": "FAIL", "check": "config", "message": str(exc)})
        result["exit"] = 1
        _emit(result, args.json)
        sys.exit(1)

    if not cfg_get(cfg, "notion.guide_database_id") and not cfg_get(cfg, "notion.content_board_database_id"):
        findings.append({"level": "SKIP", "check": "collisions",
                         "message": "no Notion database ids in the config; nothing to compare"})
        _emit(result, args.json)
        sys.exit(0)

    try:
        board, guide_kw, titles = _existing(cfg)
    except SystemExit as exc:
        findings.append({"level": "FAIL", "check": "notion", "message": str(exc)})
        result["exit"] = 1
        _emit(result, args.json)
        sys.exit(1)
    except Exception as exc:  # network or API error
        findings.append({"level": "FAIL", "check": "notion", "message": f"Notion query failed: {exc}"})
        result["exit"] = 1
        _emit(result, args.json)
        sys.exit(1)

    dm_words, dm_note = _dm_tool_keywords(cfg)
    result["existing"] = {
        "content_board": [k for k, _ in board],
        "guide_db": [k for k, _ in guide_kw],
        "guide_titles": titles,
        "dm_tool": dm_words or [],
    }

    if args.list:
        _emit(result, args.json, list_only=True)
        sys.exit(0)

    kw = args.keyword.upper()
    for existing, title in board:
        if existing.upper() == kw:
            findings.append({"level": "FAIL", "check": "content-board",
                             "message": f"{kw} already used on the Content Board card {title!r}"})
    for existing, title in guide_kw:
        if existing.upper() == kw:
            findings.append({"level": "FAIL", "check": "guide-db",
                             "message": f"{kw} already used by the guide {title!r}"})
    word = re.compile(r"\b" + re.escape(kw) + r"\b", re.I)
    for title in titles:
        if word.search(title):
            findings.append({"level": "WARN", "check": "guide-title",
                             "message": f"a published guide title contains the word: {title!r}. "
                                        "Check it is not the same topic."})
    if dm_words is None:
        findings.append({"level": "SKIP", "check": "dm-tool", "message": dm_note})
    else:
        if any(w.upper() == kw for w in dm_words):
            findings.append({"level": "FAIL", "check": "dm-tool",
                             "message": f"{kw} already has an automation in the DM tool"})
        else:
            findings.append({"level": "OK", "check": "dm-tool", "message": f"{kw} not in the DM tool ({dm_note})"})

    levels = {f["level"] for f in findings}
    if "FAIL" in levels:
        result["exit"] = 1
    elif "WARN" in levels:
        result["exit"] = 2
    else:
        findings.append({"level": "OK", "check": "collisions", "message": f"{kw} is free"})
    _emit(result, args.json)
    sys.exit(result["exit"])


def _emit(result, as_json, list_only=False):
    if as_json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return
    if list_only:
        ex = result.get("existing", {})
        print("Content Board keywords:", ", ".join(ex.get("content_board", [])) or "(none)")
        print("Guide DB keywords:     ", ", ".join(ex.get("guide_db", [])) or "(none)")
        print("DM tool keywords:      ", ", ".join(ex.get("dm_tool", [])) or "(none)")
        print("Guide titles:")
        for t in ex.get("guide_titles", []):
            print(f"  - {t}")
        return
    for f in result["findings"]:
        print(f"{f['level']:<4} {f['check']:<14} {f['message']}")


if __name__ == "__main__":
    main()
