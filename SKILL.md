---
name: topic-finder
description: Find trending content topics by scanning YouTube channels, Reddit subreddits, and X/Twitter accounts in your niche. Use when the user says "find me a topic", "what's trending", "what should I write about", "scan my channels", "scan reddit", "scan twitter", "scan X", or wants topic ideas for content (videos, guides, posts, newsletters). Scrapes a curated list of YouTube channels via yt-dlp, plus curated subreddits and X accounts via Apify, then clusters and ranks topics with cross-platform validation.
---

# Topic Finder

Surfaces trending topics in your niche by combining three signals:

1. **YouTube channel scan**: what creators in your niche are publishing right now, in two tracks (`tool` and `business`)
2. **Reddit scan**: what your target audience is actually discussing
3. **X/Twitter scan**: what lands before it reaches YouTube: lectures, first-party engineer talks, docs, repos

A topic appearing on more than one source in the same week is the strongest signal available, and a topic on all three beats a topic on two. `scripts/correlate.py` does that matching, `scripts/scan_all.py` runs everything and writes a health file other skills can trust.

**On the X scan:** rank items by bookmarks and bookmark rate, not views. Views track jokes, bookmarks track "I will come back and study this". Above 0.8 percent bookmark rate is substance, below 0.1 percent is noise. Treat the post text as a lead, not a source: accounts recycle real talks under invented numbers, so verify anything quotable against a first-party page.

---

## Setup (One Time)

### 1. Install yt-dlp
```bash
brew install yt-dlp
# or: pip install yt-dlp
```

The YouTube scanner needs no API key. yt-dlp reads public channel pages. The fast `--flat` mode needs yt-dlp 2026.07.04 or newer; older builds fall back to the full scan with a message.

### 2. Get an Apify token (for Reddit and X)
- Sign up free at https://apify.com
- Copy your API token from https://console.apify.com/account/integrations
- Either `export APIFY_TOKEN="..."` in your shell profile, or write it to `~/.config/apify/api_key`

The Apify free tier covers about 5 USD of usage per month. A Reddit scan costs roughly 0.05 to 0.15 USD, an X scan of 7 accounts over 8 days about 0.12 USD. Every paid scanner has `--dry-run` to print the estimate without fetching.

### 3. Configure your sources

Pick a preset, or start from the generic templates.

**AI coding / AI dev tools niche** (Claude Code, Cursor, AI agents, LLM builds):

```bash
cp config/youtube-channels.ai-coding.example.json config/youtube-channels.json
cp config/subreddits.ai-coding.example.json config/subreddits.json
cp config/x-accounts.example.json config/x-accounts.json      # no X preset, fill in your own
```

**Any other niche**, from the generic templates:

```bash
cp config/youtube-channels.example.json config/youtube-channels.json
cp config/subreddits.example.json config/subreddits.json
cp config/x-accounts.example.json config/x-accounts.json
cp config/topics.example.json config/topics.json               # optional named topic map
```

Edit each file for YOUR niche. The real files are gitignored; only the `.example.json` files are tracked.

Give every YouTube channel a `category`: `tool` for channels that teach how to use the thing, `business` for channels that teach how to sell it. The two tracks are scored separately (see `references/scoring-rubric.md`, Rule 0).

`config/topics.json` is optional. With it, `correlate.py` clusters on your named regex topics. Without it, `correlate.py` clusters on shared title n-grams (`--auto`), which needs no upkeep.

---

## Usage

### One command

```bash
python3 scripts/scan_all.py --out-dir /tmp/tf-scan
```

Runs all three scanners, correlates, and writes `youtube.json`, `reddit.json`, `x.json`, `topics.json`, `topics.txt`, `health.json` and `run.json` into the out dir. Exit code 1 means a requested source had no config or returned nothing; read `run.json` for the reason.

```bash
python3 scripts/scan_all.py --sources youtube,reddit --out-dir /tmp/tf-scan   # subset
python3 scripts/scan_all.py --out-dir /tmp/tf-scan --dry-run                  # plan and cost only
python3 scripts/scan_all.py --out-dir /tmp/tf-scan --full                     # YouTube with descriptions
```

### Scanner by scanner

```bash
# YouTube (last 7 days, top 10 per channel, fast flat mode)
python3 scripts/scan_youtube.py --days 7 --flat --output /tmp/yt-scan.json

# Reddit (last 7 days)
python3 scripts/scan_reddit.py --days 7 --output /tmp/reddit-scan.json

# X/Twitter (last 8 days)
python3 scripts/scan_x.py --days 8 --output /tmp/x-scan.json

# Correlate whichever scans you ran
python3 scripts/correlate.py --youtube /tmp/yt-scan.json --reddit /tmp/reddit-scan.json --x /tmp/x-scan.json
python3 scripts/correlate.py --youtube /tmp/yt-scan.json --x /tmp/x-scan.json --min-sources 2 --json
```

Every script takes `--config` to point at a config file somewhere else, and `--help`.

### Ask in Claude Code

Trigger phrases:
- "Find me a topic"
- "What's trending this week?"
- "What should I write about?"
- "Scan my channels"
- "Scan reddit for ideas"
- "Scan X"

The skill runs the scanners and returns a ranked topic briefing.

---

## How Topics Get Ranked

`correlate.py` clusters items covering the same topic or tool across all sources. The agent then scores each cluster on three dimensions:

| Dimension | Weight | What it measures |
|-----------|--------|------------------|
| **Trending** | 40% | How many sources are talking about it. Two platforms in the same week scores at least 7, all three at least 9. Recency matters (last 3 days beats last 7). X counts by bookmark rate, never views. |
| **Documentation** | 30% | Is there enough authoritative material to write a thorough piece? Official docs, repos, first-party talks. |
| **Source depth** | 30% | How rich are the sources? A long tutorial plus an active thread beats a short clip plus a thin post. |

**Composite score:** `(trending x 0.4) + (documentation x 0.3) + (source_depth x 0.3)`

The two YouTube tracks (`tool`, `business`) get their own top list each and are never merged into one ranking. Anything below the depth bar (no real documentation, surface-level posts only) is dropped regardless of how trending it is.

Full rubric: `references/scoring-rubric.md`

---

## Output Format

The agent returns a markdown briefing like this:

```
# Topic Research Briefing, 2026-09-01

## Scan Summary
- YouTube channels scanned: 17 (14 tool, 3 business), 16 returned videos
- Videos analyzed: 47
- Subreddits scanned: 13, posts kept: 31
- X accounts scanned: 7, posts kept after dedupe: 212, cost: 0.11 USD
- Cross-platform hits: 4 (2 on all three sources)
- Dead channels: 1 (see health.json youtube.errors)

## Top Topics

### 1. [Topic name]  Score: 8.4/10  Sources: YT+RD+X
**Trending:** 9/10, on 4 YouTube channels, 3 subreddits and 2 X accounts this week
**Documentation:** 8/10, official docs plus 2 repos
**Source depth:** 8/10, 2 long tutorials, a 40-minute engineer talk, an active Reddit thread

**YouTube sources (tool track):**
- Creator A, "Title" (45K views, 3 days ago)
- Creator B, "Title" (12K views, 5 days ago)

**Reddit sources:**
- r/subreddit, "Title" (412 upvotes, 89 comments)

**X sources:**
- @account, "First line of the post" (1,080 bookmarks, 1.33 percent, 40-minute video, links to the slides)

**Recommended angle:** [One sentence on the most promising framing]
```

---

## Used by guide-maker

Other skills, such as a guide or lead-magnet pipeline, call this skill for their topic research phase. The contract is `scripts/scan_all.py` plus `health.json`:

1. The caller runs `python3 <topic-finder>/scripts/scan_all.py --out-dir <dir>`.
2. It reads `<dir>/health.json` (shape in `references/health-contract.md`) before it reads any topic. Exit code 1 or an empty source means the research is incomplete; the caller reports that to the user instead of filling the gap with web search. `web_search_used` in the file is always `false` for that reason.
3. It reads `<dir>/topics.json` for the clusters, with `topics_2plus` as the count of topics that have cross-source validation.
4. It shows `youtube.errors` (dead channels) and `x.cost_usd` in its own summary.

Install this skill as a sibling of the calling skill so the path is predictable:

```
.claude/skills/
├── guide-maker/        # or whatever calls this
└── topic-finder/       # this repo
```

---

## Files

```
topic-finder/
├── SKILL.md                              # This file
├── README.md
├── VERSION
├── scripts/
│   ├── scan_all.py                      # Runs everything, writes health.json
│   ├── scan_youtube.py                  # YouTube channel scraper (yt-dlp)
│   ├── scan_reddit.py                   # Reddit scraper (Apify)
│   ├── scan_x.py                        # X/Twitter scraper (Apify)
│   └── correlate.py                     # Cross-source clustering
├── config/
│   ├── youtube-channels.example.json    # Template with tool/business categories
│   ├── youtube-channels.ai-coding.example.json
│   ├── subreddits.example.json
│   ├── subreddits.ai-coding.example.json
│   ├── x-accounts.example.json          # Placeholder handles, actor, thresholds
│   └── topics.example.json              # Optional named topic map
├── references/
│   ├── scoring-rubric.md                # Scoring methodology
│   └── health-contract.md               # health.json shape and exit codes
└── tests/fixtures/scan/                 # Small scan outputs for correlate.py
```

---

## Workflow When Triggered

1. Confirm `config/youtube-channels.json`, `config/subreddits.json` and `config/x-accounts.json` exist (else point the user to Setup). A missing source is skipped with `--sources`, never replaced with web search.
2. Run `scripts/scan_all.py --out-dir /tmp/tf-scan`.
3. Read `health.json` first. If the exit code was 1, tell the user which source failed and stop.
4. Read `topics.json` and the three raw scan files.
5. Score each cluster against `references/scoring-rubric.md`, tool and business tracks separately.
6. Drop clusters that fail the depth bar.
7. Return a ranked briefing of the top 5 to 10 topics with cross-platform notes and the scan summary.
8. Be honest. If nothing is trending, say so. Do not invent topics.

---

## Notes

- **No content writing here.** This skill only finds topics. Use your own writing skill or workflow afterward.
- **Keep configs scoped.** 8 to 15 channels, 8 to 15 subreddits, 5 to 10 X accounts. More dilutes the signal.
- **Re-run weekly.** Trending shifts fast in fast-moving niches.
- **Tokens stay out of the repo.** Scripts read `APIFY_TOKEN` or `~/.config/apify/api_key`. Never hardcode.
- **Real configs stay out of the repo.** `config/*.json` without `.example` is gitignored.
