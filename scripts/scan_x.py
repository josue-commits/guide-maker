#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Scan X/Twitter accounts for recent posts, via Apify.

Third source alongside scan_youtube.py and scan_reddit.py. X is where lectures,
first-party engineer talks and repos land first, before they turn into YouTube
tutorials. Reads the account list from ../config/x-accounts.json.

Ranking rule: bookmarks and bookmark rate, never views. Views track jokes,
bookmarks track "I will come back and study this". Above about 0.8 percent
bookmark rate is substance, below about 0.1 percent is noise. Both thresholds
live in the config under scan_defaults.

Tweet text is a lead, not a source. Engagement accounts recut the same talk
under different numbers and attribute the same stat to different companies.
Verify anything quotable against the original talk, repo or docs page before
it enters a piece of content.

Why Apify: no login or session cookie, no rate limit, takes a since/until
window, returns replies and native video metadata. Cost is per item; the
script prints a worst-case estimate before it fetches anything and --dry-run
stops there.

Setup:
    1. Sign up free at https://apify.com and copy your API token
    2. export APIFY_TOKEN="..."  (or write it to ~/.config/apify/api_key)
    3. cp config/x-accounts.example.json config/x-accounts.json and edit it

Usage:
    python3 scan_x.py --days 8 --output /tmp/x-scan.json
    python3 scan_x.py --days 8 --dry-run          # print cost estimate, fetch nothing
    python3 scan_x.py --config /path/to/x-accounts.json --output /tmp/x-scan.json
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_CONFIG = SKILL_ROOT / "config" / "x-accounts.json"
EXAMPLE_CONFIG = SKILL_ROOT / "config" / "x-accounts.example.json"
API = "https://api.apify.com/v2"
TOKEN_FILE = Path.home() / ".config" / "apify" / "api_key"

VIDEO_HOSTS = ("youtube.com", "youtu.be", "vimeo.com", "loom.com")

DEFAULTS = {
    "days_back": 8,
    "max_items_per_account": 120,
    "long_form_seconds": 900,
    "substance_bookmark_rate": 0.8,
    "noise_bookmark_rate": 0.1,
}


def load_config(path: Path) -> dict:
    if not path.exists():
        print(f"Error: config file not found at {path}", file=sys.stderr)
        if EXAMPLE_CONFIG.exists():
            print(
                f"Copy the example to get started:\n"
                f"  cp {EXAMPLE_CONFIG} {path}\n"
                f"Then edit it with your own account list.",
                file=sys.stderr,
            )
        sys.exit(1)
    cfg = json.loads(path.read_text())
    if not cfg.get("accounts"):
        print(f"Error: {path} has no accounts", file=sys.stderr)
        sys.exit(1)
    if not cfg.get("apify", {}).get("actor"):
        print(f"Error: {path} has no apify.actor", file=sys.stderr)
        sys.exit(1)
    return cfg


def get_token() -> str:
    """APIFY_TOKEN env var wins, then ~/.config/apify/api_key."""
    tok = os.environ.get("APIFY_TOKEN", "").strip()
    if tok:
        return tok
    if TOKEN_FILE.exists():
        tok = TOKEN_FILE.read_text().strip()
        if tok:
            return tok
    print(
        "Error: no Apify token.\n"
        "1. Sign up at https://apify.com\n"
        "2. Copy your token from https://console.apify.com/account/integrations\n"
        f"3. export APIFY_TOKEN=\"...\"  or write it to {TOKEN_FILE}",
        file=sys.stderr,
    )
    sys.exit(1)


def _request(url, tok, payload=None, timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(
        f"{url}{'&' if '?' in url else '?'}token={tok}",
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST" if payload is not None else "GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")[:300]
        print(f"Error: Apify returned {e.code} for {url.split('?')[0]}: {body}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"Error: could not reach Apify: {e.reason}", file=sys.stderr)
        sys.exit(1)


def run_actor(actor: str, payload: dict, tok: str, poll_every=15, max_wait=900):
    slug = actor.replace("/", "~")
    run = _request(f"{API}/acts/{slug}/runs", tok, payload)["data"]
    run_id, ds = run["id"], run["defaultDatasetId"]
    print(f"  run {run_id} started", file=sys.stderr)

    waited = 0
    while waited < max_wait:
        time.sleep(poll_every)
        waited += poll_every
        status = _request(f"{API}/actor-runs/{run_id}", tok)["data"]
        if status["status"] not in ("RUNNING", "READY"):
            cost = status.get("usageTotalUsd")
            print(f"  {status['status']} in {waited}s, cost ${cost}", file=sys.stderr)
            if status["status"] != "SUCCEEDED":
                print(f"Error: run {run_id} ended with {status['status']}", file=sys.stderr)
                sys.exit(1)
            return ds, cost
        print(f"  ...{waited}s", file=sys.stderr)
    print(f"Error: run {run_id} still going after {max_wait}s", file=sys.stderr)
    sys.exit(1)


def fetch_items(dataset_id: str, tok: str):
    return _request(f"{API}/datasets/{dataset_id}/items?clean=true", tok, timeout=300)


def video_info(t):
    """Longest attached native video: (seconds, best mp4 url). (0, None) if none."""
    best_secs, best_url, best_bitrate = 0, None, -1
    for key in ("extendedEntities", "entities"):
        for m in (t.get(key) or {}).get("media") or []:
            vi = m.get("video_info") or {}
            secs = (vi.get("duration_millis") or 0) / 1000
            if secs <= 0:
                continue
            best_secs = max(best_secs, secs)
            for v in vi.get("variants") or []:
                if v.get("content_type") == "video/mp4" and (v.get("bitrate") or 0) > best_bitrate:
                    best_bitrate, best_url = v.get("bitrate") or 0, v.get("url")
    return best_secs, best_url


def split_links(t):
    """External article links vs external video links vs native X Article links."""
    urls = [u.get("expanded_url") for u in (t.get("entities") or {}).get("urls") or []]
    urls = [u for u in urls if u]
    x_article = [u for u in urls if "/i/article/" in u]
    x_other = [u for u in urls if ("x.com" in u or "twitter.com" in u) and u not in x_article]
    ext_video = [u for u in urls if any(h in u for h in VIDEO_HOSTS)]
    ext_article = [u for u in urls if u not in x_article and u not in x_other and u not in ext_video]
    return x_article, ext_article, ext_video


def norm_text(s):
    return re.sub(r"\W+", " ", (s or "").lower()).strip()


def dedupe(rows):
    """Drop exact id repeats, then near-duplicate reposts of the same video.

    Accounts recut and repost the same talk at slightly different lengths.
    Keying on the first 60 chars of normalized text plus the video length
    rounded to the minute collapses those without merging different posts.
    """
    seen_ids, seen_keys, out, dropped = set(), set(), [], 0
    for r in sorted(rows, key=lambda x: -x["bookmarks"]):
        if r["id"] in seen_ids:
            dropped += 1
            continue
        seen_ids.add(r["id"])
        key = (norm_text(r["text"])[:60], round(r["video_seconds"] / 60))
        if key[0] and key in seen_keys:
            dropped += 1
            continue
        seen_keys.add(key)
        out.append(r)
    return out, dropped


def normalize(raw, focus_by_handle):
    rows = []
    for t in raw:
        author = t.get("author") or {}
        secs, vurl = video_info(t)
        x_art, ext_art, ext_vid = split_links(t)
        views = t.get("viewCount") or 0
        bm = t.get("bookmarkCount") or 0
        handle = author.get("userName") or "?"
        rows.append({
            "id": str(t.get("id") or ""),
            "handle": handle,
            "account_focus": focus_by_handle.get(handle.lower(), ""),
            "author_followers": author.get("followers") or 0,
            "text": t.get("text") or "",
            "created": t.get("createdAt") or "",
            "url": t.get("twitterUrl") or t.get("url") or "",
            "views": views,
            "bookmarks": bm,
            "likes": t.get("likeCount") or 0,
            "replies": t.get("replyCount") or 0,
            "retweets": t.get("retweetCount") or 0,
            "quotes": t.get("quoteCount") or 0,
            "bm_rate": round(bm / max(views, 1) * 100, 3),
            "is_reply": bool(t.get("isReply")),
            "is_retweet": bool(t.get("isRetweet")),
            "is_quote": bool(t.get("isQuote")),
            "conversation_id": t.get("conversationId") or "",
            "in_reply_to": t.get("inReplyToUsername"),
            "video_seconds": secs,
            "video_url": vurl,
            "x_article_urls": x_art,
            "article_urls": ext_art,
            "video_urls": ext_vid,
            "lang": t.get("lang") or "",
        })
    return rows


def main():
    ap = argparse.ArgumentParser(description="Scan X/Twitter accounts for recent posts via Apify")
    ap.add_argument("--days", type=int, default=None, help="Lookback window in days (default: config scan_defaults.days_back)")
    ap.add_argument("--max-items", type=int, default=None, help="Max posts per account (default: config scan_defaults.max_items_per_account)")
    ap.add_argument("--output", default=None, help="Output JSON path (default: stdout)")
    ap.add_argument("--config", default=None, help=f"Path to accounts config (default: {DEFAULT_CONFIG})")
    ap.add_argument("--dry-run", action="store_true", help="Print the cost estimate and the search terms, fetch nothing")
    args = ap.parse_args()

    cfg = load_config(Path(args.config) if args.config else DEFAULT_CONFIG)
    accounts = [a["handle"].lstrip("@") for a in cfg["accounts"]]
    focus_by_handle = {a["handle"].lstrip("@").lower(): a.get("focus", "") for a in cfg["accounts"]}
    d = dict(DEFAULTS)
    d.update(cfg.get("scan_defaults", {}))
    days = args.days or d["days_back"]
    max_items = args.max_items or d["max_items_per_account"]

    now = datetime.now(timezone.utc)
    since = (now - timedelta(days=days)).strftime("%Y-%m-%d_00:00:00_UTC")
    until = (now + timedelta(days=1)).strftime("%Y-%m-%d_00:00:00_UTC")

    terms = [
        f"from:{h} since:{since} until:{until} include:nativeretweets"
        for h in accounts
    ]

    price = float(cfg["apify"].get("price_per_item_usd", 0))
    est = len(accounts) * max_items * price
    print(f"{len(accounts)} accounts, {days}d window, <= {max_items}/account", file=sys.stderr)
    print(f"worst-case cost ${est:.3f} at ${price} per item", file=sys.stderr)
    if args.dry_run:
        for t in terms:
            print(f"  {t}", file=sys.stderr)
        print("dry run: nothing fetched", file=sys.stderr)
        return

    tok = get_token()
    ds, cost = run_actor(
        cfg["apify"]["actor"],
        {"searchTerms": terms, "maxItems": max_items, "queryType": "Latest"},
        tok,
    )
    raw = fetch_items(ds, tok)
    rows = normalize(raw, focus_by_handle)
    rows, dropped = dedupe(rows)

    long_form = [r for r in rows if r["video_seconds"] >= d["long_form_seconds"]]
    substance = [r for r in rows if r["bm_rate"] >= d["substance_bookmark_rate"]]
    noise = [r for r in rows if r["bm_rate"] < d["noise_bookmark_rate"]]

    payload = {
        "scan_date": now.strftime("%Y-%m-%d"),
        "lookback_days": days,
        "accounts": accounts,
        "cost_usd": cost,
        "raw_count": len(raw),
        "after_dedupe": len(rows),
        "duplicates_dropped": dropped,
        "long_form_count": len(long_form),
        "substance_count": len(substance),
        "noise_count": len(noise),
        "thresholds": {
            "long_form_seconds": d["long_form_seconds"],
            "substance_bookmark_rate": d["substance_bookmark_rate"],
            "noise_bookmark_rate": d["noise_bookmark_rate"],
        },
        "posts": rows,
    }
    json_str = json.dumps(payload, indent=2, ensure_ascii=False)
    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json_str)
        print(f"wrote {args.output}", file=sys.stderr)
    else:
        print(json_str)

    print(f"\n{len(raw)} raw, {dropped} dupes dropped, {len(rows)} kept", file=sys.stderr)
    print(f"{len(long_form)} long-form videos (>= {d['long_form_seconds']}s)", file=sys.stderr)
    print(f"{len(substance)} at or above {d['substance_bookmark_rate']}% bookmark rate, "
          f"{len(noise)} below {d['noise_bookmark_rate']}%", file=sys.stderr)


if __name__ == "__main__":
    main()
