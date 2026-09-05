#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Run every enabled scanner, correlate the results, and write health.json.

This is the entry point other skills call. It never falls back to web search:
when a source has no config or returns nothing, health.json says so and the
exit code is 1, so the caller can decide instead of quietly getting thinner
research.

Files written to --out-dir:
    youtube.json, reddit.json, x.json   raw scanner outputs (only for sources that ran)
    topics.json, topics.txt             correlate.py output in both forms
    health.json                         exactly the contract in references/health-contract.md
    run.json                            scan date, sources requested, dry_run flag, failure list
    logs/<source>.log                   scanner stderr

Usage:
    python3 scan_all.py --out-dir /tmp/tf-scan                      # all three sources
    python3 scan_all.py --sources youtube,reddit --out-dir /tmp/tf   # a subset
    python3 scan_all.py --sources none --out-dir /tmp/tf             # only health.json, exits 1
    python3 scan_all.py --out-dir /tmp/tf --dry-run                  # plan and cost, no fetches

Exit codes: 0 every requested source has config and returned results,
1 a requested source has no config or zero results (health.json is still written).
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG_DIR = SKILL_ROOT / "config"

ALL_SOURCES = ("youtube", "reddit", "x")
CONFIG_FILES = {
    "youtube": "youtube-channels.json",
    "reddit": "subreddits.json",
    "x": "x-accounts.json",
}
DEFAULT_DAYS = {"youtube": 7, "reddit": 7, "x": 8}


def empty_health():
    return {
        "config_present": {"youtube": False, "reddit": False, "x": False},
        "youtube": {"channels_configured": 0, "channels_with_videos": 0, "videos": 0, "errors": []},
        "reddit": {"subs": 0, "posts": 0},
        "x": {"accounts": 0, "posts": 0, "cost_usd": 0.0},
        "correlation": {"topics_2plus": 0, "topics_all": 0},
        "web_search_used": False,
    }


def read_json(path: Path):
    try:
        return json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None


def run_script(name: str, argv: list, log_path: Path) -> int:
    """Run a sibling script, tee its stderr into log_path, return the exit code."""
    cmd = [sys.executable, str(SCRIPT_DIR / name)] + argv
    print(f"\n$ {' '.join(cmd)}", file=sys.stderr)
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(proc.stderr)
    sys.stderr.write(proc.stderr)
    if proc.stdout and name != "correlate.py":
        # scanners write their JSON via --output; anything on stdout is informational
        sys.stderr.write(proc.stdout)
    return proc.returncode


def parse_youtube_errors(log_text: str) -> list:
    """Scanner lines tagged [WARN], [ERROR] or [TIMEOUT] are per-channel failures."""
    out = []
    for line in log_text.splitlines():
        s = line.strip()
        if s.startswith(("[WARN]", "[ERROR]", "[TIMEOUT]")):
            out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser(description="Run all topic-finder scanners, correlate, write health.json")
    ap.add_argument("--sources", default="all",
                    help="Comma list of youtube,reddit,x, or 'all' (default), or 'none' (write health.json only)")
    ap.add_argument("--out-dir", required=True, help="Directory for scan outputs, topics and health.json")
    ap.add_argument("--config-dir", default=None, help=f"Directory holding the config files (default: {DEFAULT_CONFIG_DIR})")
    ap.add_argument("--days-youtube", type=int, default=DEFAULT_DAYS["youtube"], help="YouTube lookback in days (default: 7)")
    ap.add_argument("--days-reddit", type=int, default=DEFAULT_DAYS["reddit"], help="Reddit lookback in days (default: 7)")
    ap.add_argument("--days-x", type=int, default=DEFAULT_DAYS["x"], help="X lookback in days (default: 8)")
    ap.add_argument("--max-videos", type=int, default=10, help="Max videos per YouTube channel (default: 10)")
    ap.add_argument("--full", action="store_true", help="Full YouTube extraction with descriptions instead of --flat")
    ap.add_argument("--topics", default=None, help="Topic map for correlate.py (default: config/topics.json, else --auto)")
    ap.add_argument("--auto", action="store_true", help="Force n-gram clustering in correlate.py")
    ap.add_argument("--min-sources", type=int, default=1, help="Passed to correlate.py (default: 1)")
    ap.add_argument("--dry-run", action="store_true", help="Print the plan and paid-API cost estimates, fetch nothing")
    args = ap.parse_args()

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    logs = out_dir / "logs"
    config_dir = Path(args.config_dir) if args.config_dir else DEFAULT_CONFIG_DIR

    if args.sources.strip().lower() == "none":
        requested = []
    elif args.sources.strip().lower() == "all":
        requested = list(ALL_SOURCES)
    else:
        requested = [s.strip().lower() for s in args.sources.split(",") if s.strip()]
        bad = [s for s in requested if s not in ALL_SOURCES]
        if bad:
            ap.error(f"unknown source(s): {', '.join(bad)}; choose from {', '.join(ALL_SOURCES)}")

    health = empty_health()
    run_info = {
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "sources_requested": requested,
        "dry_run": bool(args.dry_run),
        "out_dir": str(out_dir),
    }
    failures = []

    configs = {s: config_dir / CONFIG_FILES[s] for s in ALL_SOURCES}
    for s in ALL_SOURCES:
        health["config_present"][s] = configs[s].exists()

    if not requested:
        failures.append("no sources requested")

    for s in requested:
        if not configs[s].exists():
            failures.append(f"{s}: no config at {configs[s]} (copy config/{CONFIG_FILES[s].replace('.json', '.example.json')})")

    scan_files = {}

    # ---- YouTube ----
    if "youtube" in requested and configs["youtube"].exists():
        cfg = read_json(configs["youtube"]) or {}
        channels = cfg.get("channels", [])
        health["youtube"]["channels_configured"] = len(channels)
        if args.dry_run:
            print(f"[dry-run] youtube: {len(channels)} channels, {args.days_youtube}d, free (yt-dlp)", file=sys.stderr)
        else:
            out = out_dir / "youtube.json"
            argv = ["--config", str(configs["youtube"]), "--days", str(args.days_youtube),
                    "--max-per-channel", str(args.max_videos), "--output", str(out)]
            if not args.full:
                argv.append("--flat")
            rc = run_script("scan_youtube.py", argv, logs / "youtube.log")
            log_text = (logs / "youtube.log").read_text() if (logs / "youtube.log").exists() else ""
            health["youtube"]["errors"] = parse_youtube_errors(log_text)
            data = read_json(out) if rc == 0 else None
            if data is None:
                health["youtube"]["errors"].append(f"scan_youtube.py exited {rc}")
            else:
                videos = data.get("videos", [])
                health["youtube"]["videos"] = len(videos)
                health["youtube"]["channels_with_videos"] = len({v.get("channel_name") for v in videos})
                scan_files["youtube"] = out
        if health["youtube"]["videos"] == 0:
            failures.append("youtube: zero videos")

    # ---- Reddit ----
    if "reddit" in requested and configs["reddit"].exists():
        cfg = read_json(configs["reddit"]) or {}
        health["reddit"]["subs"] = len(cfg.get("subreddits", []))
        out = out_dir / "reddit.json"
        argv = ["--config", str(configs["reddit"]), "--days", str(args.days_reddit), "--output", str(out)]
        if args.dry_run:
            run_script("scan_reddit.py", argv + ["--dry-run"], logs / "reddit.log")
        else:
            rc = run_script("scan_reddit.py", argv, logs / "reddit.log")
            data = read_json(out) if rc == 0 else None
            if data is not None:
                health["reddit"]["posts"] = len(data.get("posts", []))
                scan_files["reddit"] = out
        if health["reddit"]["posts"] == 0:
            failures.append("reddit: zero posts")

    # ---- X ----
    if "x" in requested and configs["x"].exists():
        cfg = read_json(configs["x"]) or {}
        health["x"]["accounts"] = len(cfg.get("accounts", []))
        out = out_dir / "x.json"
        argv = ["--config", str(configs["x"]), "--days", str(args.days_x), "--output", str(out)]
        if args.dry_run:
            run_script("scan_x.py", argv + ["--dry-run"], logs / "x.log")
        else:
            rc = run_script("scan_x.py", argv, logs / "x.log")
            data = read_json(out) if rc == 0 else None
            if data is not None:
                health["x"]["posts"] = len(data.get("posts", []))
                health["x"]["cost_usd"] = float(data.get("cost_usd") or 0.0)
                scan_files["x"] = out
        if health["x"]["posts"] == 0:
            failures.append("x: zero posts")

    # ---- Correlate ----
    if scan_files:
        argv = ["--json", "--min-sources", str(args.min_sources), "--output", str(out_dir / "topics.json")]
        for s, p in scan_files.items():
            argv += [f"--{s}", str(p)]
        if args.topics:
            argv += ["--topics", args.topics]
        if args.auto:
            argv.append("--auto")
        rc = run_script("correlate.py", argv, logs / "correlate.log")
        topics = read_json(out_dir / "topics.json") if rc == 0 else None
        if topics is not None:
            health["correlation"]["topics_all"] = int(topics.get("topics_all", 0))
            health["correlation"]["topics_2plus"] = int(topics.get("topics_2plus", 0))
            text_argv = [a for a in argv if a not in ("--json",)]
            text_argv[text_argv.index("--output") + 1] = str(out_dir / "topics.txt")
            run_script("correlate.py", text_argv, logs / "correlate-text.log")
        else:
            failures.append(f"correlate.py exited {rc}")

    # health.json carries exactly the contract keys; run.json carries the rest.
    (out_dir / "health.json").write_text(json.dumps(health, indent=2))
    run_info["failures"] = failures
    (out_dir / "run.json").write_text(json.dumps(run_info, indent=2))

    print("\nhealth:", file=sys.stderr)
    print(json.dumps(health, indent=2), file=sys.stderr)
    print(f"\nwrote {out_dir / 'health.json'} and run.json", file=sys.stderr)
    if failures:
        print("FAIL: " + "; ".join(failures), file=sys.stderr)
        sys.exit(1)
    print("OK", file=sys.stderr)


if __name__ == "__main__":
    main()
