#!/usr/bin/env python3
"""Sweep every published guide page for authoring scaffolding that leaked into body text.

Usage:
    scan_published_leaks.py [--config PATH] [--database-id ID] [--report-only]
                            [--json] [--out FILE] [--workers N] [--limit N]

Walks each hub page in the Guide Database plus its child pages and matches
every text block against eight leak patterns: page-icon directives, icon
directives, block scaffolding ("Block 3:"), callout scaffolding, [Verify: ...]
placeholders, unfilled link slots, [Name] / {name} merge tags, and TODO
markers. Findings print as a table and, with --out, land in a JSON file.

Read the output before acting: some hits are legitimate content (a guide
about publishing genuinely contains the words "Community callout"). Delete
only what is unambiguously a note to the tooling.

Exit 1 when there are findings, unless --report-only. Exit 0 when clean.
Read-only: nothing is written to Notion.
"""

import argparse
import json
import os
import re
import sys
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _config import load_config, cfg_get, add_config_arg  # noqa: E402
import _notion  # noqa: E402

LEAKS = {
    "page-icon":          r"(?i)\bpage\s+icon\s*:",
    "icon-directive":     r"(?im)^\s*\*{0,2}icon\*{0,2}\s*:\s*\S",
    "block-scaffold":     r"(?i)\bblock\s+\d+\s*:",
    "callout-scaffold":   r"(?i)CALLOUT\s*\(",
    "verify-placeholder": r"\[Verify:",
    "unfilled-link":      r"(?i)\[notion link\]|\{notion_guide_url\}|GUIDE_URL_PLACEHOLDER|STEP_\d+_URL|\{guide_url\}",
    "name-placeholder":   r"\[Name\]|\{name\}|\{first_?name\}",
    "todo":               r"\b(TODO|TKTK|XXX)\b",
}
_COMPILED = {name: re.compile(pat) for name, pat in LEAKS.items()}


def scan_hub(hub):
    """Scan one hub and its child pages. Returns (rows, pages_seen, error)."""
    title, hub_id, created = hub
    rows, pages_seen = [], 0
    try:
        kids = _notion.children(hub_id)
    except Exception as exc:
        return rows, 0, f"{title}: {exc}"

    targets = [(hub_id, "HUB", title, kids)]
    for block in kids:
        if block.get("type") == "child_page":
            targets.append((block["id"], "SUB", block["child_page"]["title"], None))

    for page_id, kind, page_name, pre in targets:
        try:
            blocks = pre if pre is not None else _notion.children(page_id)
        except Exception:
            continue
        pages_seen += 1
        for block in blocks:
            text = _notion.block_text(block)
            if not text:
                continue
            for name, pat in _COMPILED.items():
                if pat.search(text):
                    rows.append({"created": created, "guide": title, "kind": kind,
                                 "page": page_name, "page_id": page_id, "leak": name,
                                 "text": text[:160], "block_id": block["id"],
                                 "block_type": block.get("type")})
    return rows, pages_seen, None


def main():
    parser = argparse.ArgumentParser(description="Scan published guide pages for leaked scaffolding")
    parser.add_argument("--database-id", default=None, help="Override notion.guide_database_id")
    parser.add_argument("--report-only", action="store_true", help="Exit 0 even with findings")
    parser.add_argument("--json", action="store_true", help="Print findings as JSON")
    parser.add_argument("--out", default=None, help="Write findings JSON to this file")
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--limit", type=int, default=0, help="Scan only the N most recent hubs")
    add_config_arg(parser)
    args = parser.parse_args()

    cfg = load_config(getattr(args, "config", None))
    _notion.init(cfg)
    guide_db = args.database_id or cfg_get(cfg, "notion.guide_database_id", "")
    if not guide_db:
        print("Error: notion.guide_database_id is empty and no --database-id given.", file=sys.stderr)
        sys.exit(1)

    hubs = []
    for page in _notion.query_database(guide_db):
        hubs.append((_notion.title_of(page, "Guide Title") or "(untitled)",
                     page["id"], (page.get("created_time") or "")[:10]))
    hubs.sort(key=lambda h: h[2], reverse=True)
    if args.limit:
        hubs = hubs[:args.limit]
    print(f"hubs: {len(hubs)}", flush=True)

    findings, total_pages, errors = [], 0, []
    with ThreadPoolExecutor(max_workers=max(1, args.workers)) as ex:
        for rows, n, err in ex.map(scan_hub, hubs):
            findings += rows
            total_pages += n
            if err:
                errors.append(err)

    findings.sort(key=lambda f: f["created"], reverse=True)
    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as fh:
            json.dump(findings, fh, indent=1, ensure_ascii=False)

    if args.json:
        print(json.dumps({"pages": total_pages, "findings": findings, "errors": errors},
                         indent=2, ensure_ascii=False))
    else:
        print(f"pages scanned: {total_pages}")
        print(f"findings: {len(findings)}")
        if errors:
            print(f"errors: {len(errors)}")
            for e in errors[:5]:
                print("  !", e)
        if findings:
            print()
            for kind, count in Counter(f["leak"] for f in findings).most_common():
                print(f"  {kind:<20} {count}")
            print()
            for f in findings:
                print(f'{f["created"]} | {f["guide"][:40]:<40} | {f["kind"]} {f["page"][:38]:<38} '
                      f'| {f["leak"]:<18} | {f["text"][:60]!r}')

    if findings and not args.report_only:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
