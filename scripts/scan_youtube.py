#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan YouTube channels for recent videos using yt-dlp.

Reads channel list from ../config/youtube-channels.json, fetches recent video
metadata in parallel, and outputs structured JSON.

Setup:
    1. Install yt-dlp: brew install yt-dlp (or pip install yt-dlp)
    2. Copy config/youtube-channels.example.json to config/youtube-channels.json
    3. Edit with your own channel list

Usage:
    python3 scan_youtube.py --days 7 --max-per-channel 10 --output /tmp/yt-scan.json
    python3 scan_youtube.py --days 7 --flat --output /tmp/yt-scan.json
    python3 scan_youtube.py --config /path/to/youtube-channels.json --output /tmp/yt-scan.json

Modes:
    default   full per-video extraction: exact views and date plus the description. Slow.
    --flat    --flat-playlist plus approximate_date: about 6x faster, far less bandwidth,
              returns view_count and an approximate upload_date, no description.
              Needs yt-dlp >= 2026.07.04 (older builds return null view_count in
              flat mode). The script checks the installed version and falls back to
              the full scan with a message when the build is too old.

Each video carries channel_category (the "category" field of its channel entry,
for example "tool" or "business") so downstream scoring can keep tracks apart.
"""

import argparse
import json
import shutil
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG = SKILL_ROOT / "config" / "youtube-channels.json"
EXAMPLE_CONFIG = SKILL_ROOT / "config" / "youtube-channels.example.json"

# First yt-dlp release that returns view_count in --flat-playlist mode.
FLAT_MIN_VERSION = (2026, 7, 4)


def find_ytdlp() -> str:
    """Locate yt-dlp on PATH. Fail with a helpful message if missing."""
    path = shutil.which("yt-dlp")
    if not path:
        print(
            "Error: yt-dlp not found on PATH.\n"
            "Install it with: brew install yt-dlp  (or: pip install yt-dlp)",
            file=sys.stderr,
        )
        sys.exit(1)
    return path


def ytdlp_version(ytdlp: str):
    """Return the installed yt-dlp version as a tuple of ints, or None if unknown."""
    try:
        out = subprocess.run([ytdlp, "--version"], capture_output=True, text=True, timeout=30)
    except Exception:
        return None
    raw = (out.stdout or "").strip().split("\n")[0]
    parts = raw.split(".")
    try:
        return tuple(int(x) for x in parts[:3])
    except ValueError:
        return None


def flat_supported(ytdlp: str) -> bool:
    """True when the installed yt-dlp can run --flat with view counts.

    Prints a clear message and returns False when the build is too old or the
    version cannot be read, so the caller falls back to the full scan.
    """
    ver = ytdlp_version(ytdlp)
    want = ".".join(f"{x:02d}" if i else str(x) for i, x in enumerate(FLAT_MIN_VERSION))
    if ver is None:
        print(
            f"[flat] could not read the yt-dlp version; --flat needs >= {want}. "
            "Falling back to the full scan.",
            file=sys.stderr,
        )
        return False
    if ver < FLAT_MIN_VERSION:
        have = ".".join(f"{x:02d}" if i else str(x) for i, x in enumerate(ver))
        print(
            f"[flat] yt-dlp {have} is older than {want}; flat mode would return null "
            "view counts. Falling back to the full scan. Upgrade with: "
            "pip install -U yt-dlp  (or: brew upgrade yt-dlp)",
            file=sys.stderr,
        )
        return False
    return True


def load_channels(channels_file: Path) -> dict:
    if not channels_file.exists():
        print(f"Error: config file not found at {channels_file}", file=sys.stderr)
        if EXAMPLE_CONFIG.exists():
            print(
                f"Copy the example to get started:\n"
                f"  cp {EXAMPLE_CONFIG} {channels_file}\n"
                f"Then edit it with your own channel list.",
                file=sys.stderr,
            )
        sys.exit(1)
    with open(channels_file) as f:
        return json.load(f)


def scan_channel(ytdlp: str, channel: dict, max_videos: int, cutoff_date: str, flat: bool = False) -> list[dict]:
    """Scan a single channel for recent videos. Returns list of video dicts.

    flat=True adds --flat-playlist and the approximate_date extractor arg:
    view_count plus an approximate upload_date, no description, much faster.
    flat=False does full per-video extraction.
    """
    channel_url = channel["url"].rstrip("/") + "/videos"
    cmd = [
        ytdlp,
        "--playlist-items", f"1:{max_videos}",
        "--dump-json",
        "--no-download",
        "--no-warnings",
        "--quiet",
    ]
    if flat:
        cmd += ["--flat-playlist", "--extractor-args", "youtubetab:approximate_date"]
    cmd.append(channel_url)

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {channel['name']}: skipping", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [ERROR] {channel['name']}: {e}", file=sys.stderr)
        return []

    if result.returncode != 0:
        stderr_snippet = result.stderr[:200] if result.stderr else "no stderr"
        print(f"  [WARN] {channel['name']}: yt-dlp returned {result.returncode}: {stderr_snippet}", file=sys.stderr)

    videos = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        upload_date = data.get("upload_date", "")
        if not upload_date or upload_date < cutoff_date:
            continue

        videos.append({
            "id": data.get("id", ""),
            "title": data.get("title", ""),
            "upload_date": upload_date,
            # Coerce None to 0. Live and upcoming videos return null view_count
            # and duration, and the sort below compares them to ints, so one
            # scheduled premiere on any channel used to kill the whole scan.
            "view_count": data.get("view_count") or 0,
            "duration": data.get("duration") or 0,
            "description": (data.get("description") or "")[:500],
            "channel_name": channel["name"],
            "channel_focus": channel.get("focus", ""),
            "channel_category": channel.get("category", ""),
            "url": f"https://www.youtube.com/watch?v={data.get('id', '')}",
        })

    return videos


def main():
    parser = argparse.ArgumentParser(description="Scan YouTube channels for recent videos")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (default: 7)")
    parser.add_argument("--max-per-channel", "--max-videos", dest="max_per_channel", type=int, default=10, help="Max videos to check per channel (default: 10)")
    parser.add_argument("--output", type=str, default=None, help="Output file path (default: stdout)")
    parser.add_argument("--config", type=str, default=None, help=f"Path to channels config (default: {DEFAULT_CONFIG})")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers (default: 4)")
    parser.add_argument(
        "--flat", action="store_true",
        help="Fast flat-playlist scan: view_count + approximate upload_date, no description "
             "(needs yt-dlp >= 2026.07.04; older builds fall back to the full scan)",
    )
    args = parser.parse_args()

    ytdlp = find_ytdlp()
    flat = bool(args.flat and flat_supported(ytdlp))

    config_file = Path(args.config) if args.config else DEFAULT_CONFIG
    config = load_channels(config_file)
    channels = config["channels"]

    days_back = args.days
    if not days_back:
        days_back = config.get("scan_defaults", {}).get("days_back", 7)

    max_per_channel = args.max_per_channel
    if not max_per_channel:
        max_per_channel = config.get("scan_defaults", {}).get("max_videos_per_channel", 10)

    cutoff = datetime.now() - timedelta(days=days_back)
    cutoff_date = cutoff.strftime("%Y%m%d")

    mode = "flat" if flat else "full"
    print(f"Scanning {len(channels)} channels (last {days_back} days, max {max_per_channel}/channel, {mode} mode)...", file=sys.stderr)

    all_videos = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(scan_channel, ytdlp, ch, max_per_channel, cutoff_date, flat): ch
            for ch in channels
        }
        for future in as_completed(futures):
            ch = futures[future]
            try:
                videos = future.result()
                print(f"  {ch['name']}: {len(videos)} recent videos", file=sys.stderr)
                all_videos.extend(videos)
            except Exception as e:
                print(f"  [ERROR] {ch['name']}: {e}", file=sys.stderr)

    all_videos.sort(key=lambda v: (v["upload_date"], v["view_count"]), reverse=True)

    output = {
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "lookback_days": days_back,
        "mode": mode,
        "channels_scanned": len(channels),
        "videos_found": len(all_videos),
        "videos": all_videos,
    }

    json_str = json.dumps(output, indent=2, ensure_ascii=False)

    if args.output:
        out_path = Path(args.output)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            f.write(json_str)
        print(f"\nWrote {len(all_videos)} videos to {args.output}", file=sys.stderr)
    else:
        print(json_str)

    print(f"\nDone. {len(all_videos)} videos from {len(channels)} channels.", file=sys.stderr)


if __name__ == "__main__":
    main()
