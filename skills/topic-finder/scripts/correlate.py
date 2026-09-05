#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-source topic correlation.

Takes the scan outputs (YouTube, Reddit, X) and clusters them into topics, so
one piece of content can be built from every resource that touches it no
matter which platform surfaced it. A topic on two or more sources in the same
week is the strongest signal the rubric has. This makes that computable.

Two clustering modes:

    topics  Regex topic map loaded from a JSON file: a list of
            {"label": str, "patterns": [regex, ...]}. Default file is
            ../config/topics.json; ship your own from config/topics.example.json.
            A resource can land in several topics on purpose.

    auto    No topic file needed. Clusters on 2 and 3 word n-grams shared by
            titles across sources. Rougher labels, zero upkeep. Used when
            --auto is passed or when no topics file exists.

Usage:
    python3 correlate.py --youtube /tmp/yt-scan.json --reddit /tmp/reddit-scan.json --x /tmp/x-scan.json
    python3 correlate.py --youtube /tmp/yt-scan.json --x /tmp/x-scan.json --min-sources 2
    python3 correlate.py --youtube /tmp/yt-scan.json --reddit /tmp/reddit-scan.json --auto --json
    python3 correlate.py ... --topics /path/to/topics.json --json --output /tmp/topics.json

Exit codes: 0 ran, 1 no scan file could be loaded or the topics file is invalid.
"""

import argparse
import json
import re
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_ROOT = SCRIPT_DIR.parent
DEFAULT_TOPICS = SKILL_ROOT / "config" / "topics.json"
EXAMPLE_TOPICS = SKILL_ROOT / "config" / "topics.example.json"

SOURCES = ("YT", "RD", "X")
LONG_FORM_MINUTES = 15

STOPWORDS = set("""
a an and are as at be but by can do for from has have how i if in into is it its
just my new no not of on or our so than that the their them then there these they
this to up us vs was we what when which who why will with you your
""".split())


# ---------- loading ----------

def load(path, label):
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        print(f"  [skip] {label}: {p} not found", file=sys.stderr)
        return None
    try:
        return json.loads(p.read_text())
    except json.JSONDecodeError as e:
        print(f"  [skip] {label}: {p} is not valid JSON ({e})", file=sys.stderr)
        return None


def yt_items(blob):
    for v in blob.get("videos", []):
        views = v.get("view_count") or 0
        yield {
            "source": "YT",
            "title": v.get("title", ""),
            "text": f"{v.get('title', '')} {v.get('description', '')}",
            "weight": views // 100,
            "metric": f"{views:,} views",
            "who": v.get("channel_name", "?"),
            "category": v.get("channel_category", ""),
            "url": v.get("url", ""),
            "depth": (v.get("duration") or 0) / 60,
        }


def rd_items(blob):
    for p in blob.get("posts", blob.get("results", [])):
        yield {
            "source": "RD",
            "title": p.get("title", ""),
            "text": f"{p.get('title', '')} {p.get('body_snippet', '')}",
            "weight": (p.get("comments") or 0) * 3,
            "metric": f"{p.get('upvotes', 0)}up {p.get('comments', 0)}c",
            "who": "r/" + p.get("subreddit", "?"),
            "category": "",
            "url": p.get("url", ""),
            "depth": 0,
        }


def x_items(blob):
    for r in blob.get("posts", []):
        yield {
            "source": "X",
            "title": (r.get("text") or "")[:200],
            "text": r.get("text") or "",
            "weight": r.get("bookmarks") or 0,
            "metric": f"{r.get('bookmarks', 0)}bm {r.get('bm_rate', 0)}%",
            "who": "@" + r.get("handle", "?"),
            "category": r.get("account_focus", ""),
            "url": r.get("url", ""),
            "depth": (r.get("video_seconds") or 0) / 60,
        }


def build_pool(args):
    pool, loaded = [], []
    for flag, label, fn in (("youtube", "YouTube", yt_items), ("reddit", "Reddit", rd_items), ("x", "X", x_items)):
        blob = load(getattr(args, flag), label)
        if blob is None:
            continue
        loaded.append(label)
        pool += list(fn(blob))
    for i, it in enumerate(pool):
        it["_id"] = i
    return pool, loaded


# ---------- topics mode ----------

def load_topics(path):
    """Return [(label, [compiled regex]), ...] or None if the file is absent."""
    p = Path(path) if path else DEFAULT_TOPICS
    if not p.exists():
        return None
    try:
        raw = json.loads(p.read_text())
    except json.JSONDecodeError as e:
        print(f"Error: topics file {p} is not valid JSON ({e})", file=sys.stderr)
        sys.exit(1)
    if isinstance(raw, dict):
        raw = raw.get("topics", [])
    topics = []
    for t in raw:
        label = t.get("label")
        pats = t.get("patterns") or []
        if not label or not pats:
            print(f"Error: topics file {p}: every entry needs a label and a non-empty patterns list", file=sys.stderr)
            sys.exit(1)
        try:
            topics.append((label, [re.compile(x, re.I) for x in pats]))
        except re.error as e:
            print(f"Error: topics file {p}: bad regex under '{label}': {e}", file=sys.stderr)
            sys.exit(1)
    return topics


def cluster_by_topics(pool, topics):
    out = []
    for label, rx in topics:
        hits = [it for it in pool if any(r.search(it["text"] or "") for r in rx)]
        if hits:
            out.append((label, hits))
    return out


# ---------- auto mode ----------

def tokens(text):
    return [w for w in re.sub(r"[^a-z0-9+#.\- ]+", " ", (text or "").lower()).split()
            if w not in STOPWORDS and len(w) > 1]


def ngrams(text, sizes=(2, 3)):
    toks = tokens(text)
    out = set()
    for n in sizes:
        for i in range(len(toks) - n + 1):
            out.add(" ".join(toks[i:i + n]))
    return out


def cluster_auto(pool):
    """Group items on shared 2 and 3 word title n-grams.

    Candidate n-grams need at least two items. Candidates are ranked by how
    many sources they span, then by item count, then by length (a 3-gram is a
    sharper label than a 2-gram). Greedy dedupe drops any candidate whose
    item set mostly overlaps one already accepted.
    """
    by_gram = {}
    for it in pool:
        for g in ngrams(it["title"]):
            by_gram.setdefault(g, set()).add(it["_id"])
    cands = [(g, ids) for g, ids in by_gram.items() if len(ids) >= 2]
    by_id = {it["_id"]: it for it in pool}

    def srcs(ids):
        return {by_id[i]["source"] for i in ids}

    cands.sort(key=lambda c: (-len(srcs(c[1])), -len(c[1]), -len(c[0].split()), c[0]))

    accepted = []
    for g, ids in cands:
        dup = False
        for _, seen in accepted:
            inter = len(ids & seen)
            if inter and inter / len(ids | seen) >= 0.5:
                dup = True
                break
        if not dup:
            accepted.append((g, ids))
    return [(g, [by_id[i] for i in sorted(ids)]) for g, ids in accepted]


# ---------- scoring and output ----------

def score_clusters(clusters, min_sources):
    results = []
    for label, hits in clusters:
        by_src = {}
        for h in hits:
            by_src.setdefault(h["source"], []).append(h)
        if len(by_src) < min_sources:
            continue
        long_form = sum(1 for h in hits if h["depth"] >= LONG_FORM_MINUTES)
        # Cross-source coverage dominates, then engagement weight, then long-form depth.
        score = len(by_src) * 1000 + sum(h["weight"] for h in hits) / 10 + long_form * 50
        results.append({
            "label": label,
            "score": round(score, 1),
            "sources": sorted(by_src, key=lambda s: -len(by_src[s])),
            "source_count": len(by_src),
            "resource_count": len(hits),
            "long_form": long_form,
            "by_source": by_src,
        })
    results.sort(key=lambda r: -r["score"])
    return results


def print_text(results, top):
    for r in results:
        print("=" * 100)
        print(r["label"])
        print(f"  sources: {'+'.join(r['sources'])}  ({r['source_count']}/{len(SOURCES)})   "
              f"resources: {r['resource_count']}   long-form: {r['long_form']}   score: {r['score']:.0f}")
        print("=" * 100)
        for src in SOURCES:
            items = r["by_source"].get(src)
            if not items:
                print(f"  [{src}] none")
                continue
            for h in sorted(items, key=lambda h: -h["weight"])[:top]:
                d = f"{h['depth']:.0f}min " if h["depth"] >= LONG_FORM_MINUTES else ""
                txt = re.sub(r"\s+", " ", h["text"])[:88]
                print(f"  [{src}] {d}{h['metric']:<18} {h['who']:<20} {txt}")
        print()


def to_json(results, mode, pool, loaded, top):
    topics = []
    for r in results:
        resources = []
        for src in SOURCES:
            for h in sorted(r["by_source"].get(src, []), key=lambda h: -h["weight"])[:top]:
                resources.append({
                    "source": src,
                    "title": h["title"],
                    "metric": h["metric"],
                    "who": h["who"],
                    "category": h["category"],
                    "url": h["url"],
                    "depth_minutes": round(h["depth"], 1),
                    "weight": h["weight"],
                })
        topics.append({k: r[k] for k in ("label", "score", "sources", "source_count", "resource_count", "long_form")}
                      | {"resources": resources})
    return {
        "mode": mode,
        "sources_loaded": loaded,
        "pool": len(pool),
        "topics_all": len(results),
        "topics_2plus": sum(1 for r in results if r["source_count"] >= 2),
        "topics": topics,
    }


def main():
    ap = argparse.ArgumentParser(description="Cluster scan results into cross-source topics")
    ap.add_argument("--youtube", default=None, help="scan_youtube.py output")
    ap.add_argument("--reddit", default=None, help="scan_reddit.py output")
    ap.add_argument("--x", default=None, help="scan_x.py output")
    ap.add_argument("--topics", default=None, help=f"Topic map JSON (default: {DEFAULT_TOPICS})")
    ap.add_argument("--auto", action="store_true", help="Cluster on shared title n-grams instead of a topic map")
    ap.add_argument("--min-sources", type=int, default=1, help="Keep topics seen on at least this many sources (default: 1)")
    ap.add_argument("--top", type=int, default=5, help="Resources shown per source per topic (default: 5)")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of the text report")
    ap.add_argument("--output", default=None, help="Write the report here instead of stdout")
    args = ap.parse_args()

    if not (args.youtube or args.reddit or args.x):
        ap.error("pass at least one of --youtube, --reddit, --x")

    pool, loaded = build_pool(args)
    if not loaded:
        print("Error: no scan file could be loaded", file=sys.stderr)
        sys.exit(1)
    print(f"pool: {len(pool)} resources from {', '.join(loaded)}", file=sys.stderr)

    topics = None if args.auto else load_topics(args.topics)
    if topics is None:
        if not args.auto:
            hint = f"; copy {EXAMPLE_TOPICS.name} to {DEFAULT_TOPICS.name} for named topics" if EXAMPLE_TOPICS.exists() else ""
            print(f"no topics file at {args.topics or DEFAULT_TOPICS}, using --auto n-gram clustering{hint}", file=sys.stderr)
        mode = "auto"
        clusters = cluster_auto(pool)
    else:
        mode = "topics"
        clusters = cluster_by_topics(pool, topics)

    results = score_clusters(clusters, args.min_sources)
    print(f"{len(results)} topics ({mode} mode, min sources {args.min_sources}), "
          f"{sum(1 for r in results if r['source_count'] >= 2)} on 2+ sources", file=sys.stderr)

    if args.json:
        text = json.dumps(to_json(results, mode, pool, loaded, args.top), indent=2, ensure_ascii=False)
    else:
        import io
        buf = io.StringIO()
        old = sys.stdout
        sys.stdout = buf
        try:
            print_text(results, args.top)
        finally:
            sys.stdout = old
        text = buf.getvalue()

    if args.output:
        out = Path(args.output)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text)
        print(f"wrote {out}", file=sys.stderr)
    else:
        sys.stdout.write(text)


if __name__ == "__main__":
    main()
