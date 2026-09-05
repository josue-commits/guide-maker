#!/usr/bin/env python3
"""
Reddit Topic Scanner: scrapes configured subreddits via Apify for trending posts.

Setup:
    1. Sign up free at https://apify.com
    2. Get your API token from https://console.apify.com/account/integrations
    3. Export it: export APIFY_TOKEN="..."  (or write it to ~/.config/apify/api_key)
    4. Copy config/subreddits.example.json to config/subreddits.json
    5. Edit with your own subreddit list

Usage:
    python3 scan_reddit.py [--days 7] [--output /tmp/reddit-scan.json]
    python3 scan_reddit.py --dry-run     # list what would be scanned, call nothing
"""

import sys
import json
import os
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timezone, timedelta
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG = SKILL_ROOT / "config" / "subreddits.json"
EXAMPLE_CONFIG = SKILL_ROOT / "config" / "subreddits.example.json"

APIFY_ACTOR = "harshmaur~reddit-scraper"
APIFY_BASE = "https://api.apify.com/v2"
TOKEN_FILE = Path.home() / ".config" / "apify" / "api_key"


def get_apify_token() -> str:
    """APIFY_TOKEN env var wins, then ~/.config/apify/api_key."""
    token = os.environ.get("APIFY_TOKEN", "").strip()
    if token:
        return token
    if TOKEN_FILE.exists():
        token = TOKEN_FILE.read_text().strip()
        if token:
            return token
    print(
        "Error: no Apify token.\n"
        "1. Sign up at https://apify.com\n"
        "2. Copy your token from https://console.apify.com/account/integrations\n"
        f"3. export APIFY_TOKEN=\"...\"  or write it to {TOKEN_FILE}",
        file=sys.stderr,
    )
    sys.exit(1)


def apify_scrape_subreddit(token, sub_name, sort="hot", max_posts=10):
    """Scrape a subreddit via Apify actor, return list of posts."""
    url = (
        f"{APIFY_BASE}/acts/{APIFY_ACTOR}/run-sync-get-dataset-items"
        f"?token={token}"
    )
    start_url = f"https://www.reddit.com/r/{sub_name}/{sort}/"
    body = json.dumps({
        "startUrls": [{"url": start_url}],
        "maxPostsCount": max_posts,
        "crawlCommentsPerPost": False,
        "fastMode": True,
    }).encode("utf-8")

    req = urllib.request.Request(
        url, data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=300) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8")
        print(f"Apify error {e.code} for r/{sub_name}: {error_body}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Error scraping r/{sub_name}: {e}", file=sys.stderr)
        return []


def filter_post(post, min_upvotes=50, days_cutoff=7):
    """Keep posts with enough upvotes and recent enough."""
    upvotes = post.get("upVotes", 0)
    if upvotes < min_upvotes:
        return False

    created = post.get("createdAt", "")
    if not created:
        return False

    try:
        post_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
        cutoff = datetime.now(timezone.utc) - timedelta(days=days_cutoff)
        if post_date < cutoff:
            return False
    except ValueError:
        return False

    flair = (post.get("flair") or "").lower()
    if "megathread" in flair or "announcement" in flair:
        return False

    return True


def simplify_post(post, subreddit_name, weight):
    body = post.get("body", "")
    title = post.get("title", "")
    upvotes = post.get("upVotes", 0)
    comments = post.get("commentsCount", 0)
    engagement = upvotes + (comments * 3)

    return {
        "subreddit": subreddit_name,
        "subreddit_weight": weight,
        "title": title,
        "body_snippet": body[:300].replace("\n", " ") if body else "",
        "url": post.get("postUrl", ""),
        "upvotes": upvotes,
        "comments": comments,
        "engagement": engagement,
        "created_at": post.get("createdAt", ""),
        "author": post.get("authorName", ""),
        "flair": post.get("flair"),
        "post_type": post.get("postType", ""),
    }


def load_config(config_path: Path) -> dict:
    if not config_path.exists():
        print(f"Error: config file not found at {config_path}", file=sys.stderr)
        if EXAMPLE_CONFIG.exists():
            print(
                f"Copy the example to get started:\n"
                f"  cp {EXAMPLE_CONFIG} {config_path}\n"
                f"Then edit it with your own subreddit list.",
                file=sys.stderr,
            )
        sys.exit(1)
    with open(config_path) as f:
        return json.load(f)


def run(days=7, output_path=None, config_path=None, dry_run=False):
    """Scan all configured subreddits and return ranked posts."""
    config_file = Path(config_path) if config_path else DEFAULT_CONFIG
    config = load_config(config_file)

    subreddits = config.get("subreddits", [])
    sort = config.get("sort", "hot")
    max_posts = config.get("max_posts_per_sub", 10)
    min_upvotes = config.get("min_upvotes", 50)

    if dry_run:
        print(f"{len(subreddits)} subreddits, {days}d window, {sort} sort, "
              f"<= {max_posts} posts each, min {min_upvotes} upvotes", file=sys.stderr)
        for sub in subreddits:
            print(f"  r/{sub['name']}", file=sys.stderr)
        print("dry run: nothing fetched", file=sys.stderr)
        return {"scanned_at": None, "days_window": days, "subreddit_count": len(subreddits),
                "total_posts_kept": 0, "scan_summary": [], "posts": [], "dry_run": True}

    token = get_apify_token()

    all_posts = []
    scan_summary = []

    for sub in subreddits:
        name = sub["name"]
        weight = sub.get("weight", 1)
        print(f"Scanning r/{name}...", file=sys.stderr)

        posts = apify_scrape_subreddit(token, name, sort=sort, max_posts=max_posts)
        filtered = [p for p in posts if filter_post(p, min_upvotes, days)]
        simplified = [simplify_post(p, name, weight) for p in filtered]

        all_posts.extend(simplified)
        scan_summary.append({
            "subreddit": name,
            "posts_fetched": len(posts),
            "posts_kept": len(filtered),
        })
        print(f"  Fetched {len(posts)}, kept {len(filtered)}", file=sys.stderr)

    for p in all_posts:
        p["ranked_score"] = p["engagement"] * p["subreddit_weight"]

    all_posts.sort(key=lambda x: x["ranked_score"], reverse=True)

    result = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "days_window": days,
        "subreddit_count": len(subreddits),
        "total_posts_kept": len(all_posts),
        "scan_summary": scan_summary,
        "posts": all_posts,
    }

    if output_path:
        out_path = Path(output_path)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        print(f"\nSaved to {output_path}", file=sys.stderr)

    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reddit Topic Scanner")
    parser.add_argument("--days", type=int, default=7, help="Days lookback window")
    parser.add_argument("--output", default="/tmp/reddit-scan.json", help="Output JSON path")
    parser.add_argument("--config", default=None, help=f"Path to subreddits config (default: {DEFAULT_CONFIG})")
    parser.add_argument("--top", type=int, default=10, help="Print top N posts")
    parser.add_argument("--dry-run", action="store_true", help="List what would be scanned, call nothing")
    args = parser.parse_args()

    result = run(days=args.days, output_path=args.output, config_path=args.config, dry_run=args.dry_run)
    if result.get("dry_run"):
        sys.exit(0)

    print(f"\n--- Top {args.top} Posts (by weighted engagement) ---")
    for i, p in enumerate(result["posts"][:args.top], 1):
        print(f"\n{i}. [r/{p['subreddit']}] {p['title']}")
        print(f"   Upvotes: {p['upvotes']} | Comments: {p['comments']} | Score: {p['ranked_score']}")
        print(f"   URL: {p['url']}")
        if p["body_snippet"]:
            print(f"   {p['body_snippet'][:150]}...")

    print(f"\n--- Scan Summary ---")
    print(f"Subreddits scanned: {result['subreddit_count']}")
    print(f"Total posts kept: {result['total_posts_kept']}")
