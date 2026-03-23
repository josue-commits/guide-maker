#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan YouTube channels for recent videos using yt-dlp.

Reads channel list from channels.json (in the skill directory),
fetches recent video metadata in parallel, and outputs structured JSON.

Usage:
    python scripts/scan_channels.py --days 7 --max-per-channel 10 --output /tmp/channel-scan.json
"""

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from pathlib import Path


YTDLP_PATH = "yt-dlp"  # Default assumes yt-dlp is in PATH
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
CHANNELS_FILE = SKILL_DIR / "channels.json"


def load_channels(channels_file: Path) -> dict:
    with open(channels_file) as f:
        return json.load(f)


def scan_channel(channel: dict, max_videos: int, cutoff_date: str) -> list[dict]:
    """Scan a single channel for recent videos. Returns list of video dicts."""
    channel_url = channel["url"] + "/videos"
    cmd = [
        YTDLP_PATH,
        "--playlist-items", f"1:{max_videos}",
        "--dump-json",
        "--no-download",
        "--no-warnings",
        "--quiet",
        channel_url,
    ]

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60,
        )
    except subprocess.TimeoutExpired:
        print(f"  [TIMEOUT] {channel['name']} — skipping", file=sys.stderr)
        return []
    except Exception as e:
        print(f"  [ERROR] {channel['name']} — {e}", file=sys.stderr)
        return []

    if result.returncode != 0:
        stderr_snippet = result.stderr[:200] if result.stderr else "no stderr"
        print(f"  [WARN] {channel['name']} — yt-dlp returned {result.returncode}: {stderr_snippet}", file=sys.stderr)

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
            "view_count": data.get("view_count", 0),
            "duration": data.get("duration", 0),
            "description": (data.get("description") or "")[:500],
            "channel_name": channel["name"],
            "channel_focus": channel["focus"],
            "url": f"https://www.youtube.com/watch?v={data.get('id', '')}",
        })

    return videos


def main():
    parser = argparse.ArgumentParser(description="Scan YouTube channels for recent videos")
    parser.add_argument("--days", type=int, default=7, help="Lookback window in days (default: 7)")
    parser.add_argument("--max-per-channel", type=int, default=10, help="Max videos to check per channel (default: 10)")
    parser.add_argument("--output", type=str, default=None, help="Output file path (default: stdout)")
    parser.add_argument("--channels", type=str, default=None, help="Path to channels.json (default: auto-detected)")
    parser.add_argument("--workers", type=int, default=4, help="Parallel workers (default: 4)")
    parser.add_argument("--ytdlp-path", type=str, default=None, help="Path to yt-dlp binary (default: yt-dlp in PATH)")
    args = parser.parse_args()

    global YTDLP_PATH
    if args.ytdlp_path:
        YTDLP_PATH = args.ytdlp_path

    channels_file = Path(args.channels) if args.channels else CHANNELS_FILE
    if not channels_file.exists():
        print(f"Error: channels file not found at {channels_file}", file=sys.stderr)
        sys.exit(1)

    config = load_channels(channels_file)
    channels = config["channels"]
    days_back = args.days or config["scan_defaults"]["days_back"]
    max_per_channel = args.max_per_channel or config["scan_defaults"]["max_videos_per_channel"]

    cutoff = datetime.now() - timedelta(days=days_back)
    cutoff_date = cutoff.strftime("%Y%m%d")

    print(f"Scanning {len(channels)} channels (last {days_back} days, max {max_per_channel}/channel)...", file=sys.stderr)

    all_videos = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {
            executor.submit(scan_channel, ch, max_per_channel, cutoff_date): ch
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

    # Sort by upload date (newest first), then by view count
    all_videos.sort(key=lambda v: (v["upload_date"], v["view_count"]), reverse=True)

    output = {
        "scan_date": datetime.now().strftime("%Y-%m-%d"),
        "lookback_days": days_back,
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
