# Topic Finder

Version 2.0.0

A Claude Code skill that finds trending content topics in your niche by scanning YouTube channels, Reddit subreddits and X/Twitter accounts, then clustering and ranking topics with cross-platform validation.

## What it does

1. Scrapes a curated list of YouTube channels (via yt-dlp), in two tracks: `tool` and `business`
2. Scrapes a curated list of subreddits (via Apify)
3. Scrapes a curated list of X accounts (via Apify), ranked on bookmarks rather than views
4. Clusters topics across all three sources (`correlate.py`)
5. Scores each cluster on trending strength, documentation quality and source depth
6. Writes a `health.json` other skills can check before they trust the research
7. Returns a ranked briefing

A topic that hits two sources in the same week is a strong signal. A topic that hits all three is the strongest signal this tool produces.

## Install

Drop the `topic-finder/` folder into your `.claude/skills/` directory:

```bash
git clone https://github.com/<your-handle>/topic-finder.git ~/.claude/skills/topic-finder
```

Or for a single project:

```bash
git clone https://github.com/<your-handle>/topic-finder.git /path/to/project/.claude/skills/topic-finder
```

If another skill calls this one (a guide or lead-magnet pipeline, say), install both as siblings under the same `.claude/skills/` so the caller can find `topic-finder/scripts/scan_all.py` by a predictable path.

Requirements: Python 3.9 or newer, standard library only. yt-dlp for YouTube. An Apify token for Reddit and X.

## Setup

### 1. Install yt-dlp

```bash
brew install yt-dlp
# or: pip install yt-dlp
```

The fast `--flat` YouTube mode needs yt-dlp 2026.07.04 or newer. Older builds are detected and fall back to the full scan.

### 2. Get an Apify token (free tier is enough)

- Sign up at https://apify.com
- Copy your API token from https://console.apify.com/account/integrations
- Either export it or write it to a key file:

```bash
echo 'export APIFY_TOKEN="..."' >> ~/.zshrc && source ~/.zshrc
# or
mkdir -p ~/.config/apify && echo "..." > ~/.config/apify/api_key
```

Apify free tier covers about 5 USD of usage per month. A Reddit scan costs roughly 0.05 to 0.15 USD, an X scan of 7 accounts over 8 days about 0.12 USD. Both paid scanners have `--dry-run`, which prints the estimate and fetches nothing.

### 3. Configure your sources

Pick the preset that matches your niche, or start from the generic templates.

**AI coding / AI dev tools niche** (Claude Code, Cursor, AI agents, LLM builds):

```bash
cd ~/.claude/skills/topic-finder
cp config/youtube-channels.ai-coding.example.json config/youtube-channels.json
cp config/subreddits.ai-coding.example.json config/subreddits.json
cp config/x-accounts.example.json config/x-accounts.json
```

**Any other niche**, from the generic templates:

```bash
cp config/youtube-channels.example.json config/youtube-channels.json
cp config/subreddits.example.json config/subreddits.json
cp config/x-accounts.example.json config/x-accounts.json
```

Edit each file to match your niche. 8 to 15 channels, 8 to 15 subreddits and 5 to 10 X accounts is the sweet spot; more dilutes the signal.

Two things worth doing while you edit:

- Give each YouTube channel a `category`: `tool` (teaches how to use the thing) or `business` (teaches how to sell it). The two tracks are scored separately so a "how I made 30k" video is never judged as a tutorial and vice versa.
- Optionally copy `config/topics.example.json` to `config/topics.json` and name the topics you care about as regex lists. Without it, `correlate.py` clusters on shared title n-grams, which needs no upkeep.

The real config files are gitignored. Only the `.example.json` files are tracked, so your channel and account lists never end up in a commit.

**Want to contribute a preset for your niche?** PRs welcome. Add `youtube-channels.<niche>.example.json`, `subreddits.<niche>.example.json` and, if you have one, `x-accounts.<niche>.example.json`.

## Use

In Claude Code, just ask:
- "Find me a topic"
- "What's trending this week?"
- "Scan my channels"
- "Scan X"

Or run the scripts directly:

```bash
# everything, one command
python3 scripts/scan_all.py --out-dir /tmp/tf-scan

# one scanner at a time
python3 scripts/scan_youtube.py --days 7 --flat --output /tmp/yt-scan.json
python3 scripts/scan_reddit.py --days 7 --output /tmp/reddit-scan.json
python3 scripts/scan_x.py --days 8 --output /tmp/x-scan.json
python3 scripts/correlate.py --youtube /tmp/yt-scan.json --reddit /tmp/reddit-scan.json --x /tmp/x-scan.json
```

`scan_all.py` writes the raw scans, `topics.json` and `topics.txt`, plus `health.json` and `run.json`, into the out dir. It exits 1 when a requested source has no config or came back empty, and it never substitutes web search for a missing source. The `health.json` shape is documented in `references/health-contract.md`; a calling skill reads that file before it reads any topic.

## How ranking works

| Dimension | Weight | Signal |
|---|---|---|
| Trending | 40% | Sources spanned (two platforms scores at least 7, three at least 9), recency, engagement. X engagement is bookmark rate, never views. |
| Documentation | 30% | Official docs, repos, first-party talks behind the topic. |
| Source depth | 30% | Long tutorials, active threads, working code. |

Topics that fail the depth bar are dropped no matter how hot they are. Full rubric in `references/scoring-rubric.md`.

On X specifically: above 0.8 percent bookmark rate is substance, below 0.1 percent is noise, and tweet text is a lead, not a source. Verify numbers against the linked talk or repo before quoting them.

## File layout

```
topic-finder/
├── SKILL.md                              # Skill definition + workflow
├── README.md                             # This file
├── VERSION
├── scripts/
│   ├── scan_all.py                      # Runs everything, writes health.json
│   ├── scan_youtube.py                  # YouTube scraper (yt-dlp)
│   ├── scan_reddit.py                   # Reddit scraper (Apify)
│   ├── scan_x.py                        # X/Twitter scraper (Apify)
│   └── correlate.py                     # Cross-source clustering
├── config/
│   ├── youtube-channels.example.json    # Template (tool/business categories)
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

## Upgrading from 1.x

- `scan_youtube.py` no longer crashes on channels with a live or scheduled video (null view counts are coerced to 0). It gains `--flat` and `channel_category` on every video.
- `config/youtube-channels.json` entries should add `"category": "tool"` or `"business"`. Missing categories are treated as an empty string and still scan.
- New files: `scan_x.py`, `correlate.py`, `scan_all.py`, `config/x-accounts.example.json`, `config/topics.example.json`, `references/health-contract.md`.
- `scan_reddit.py` now also reads the token from `~/.config/apify/api_key` and has `--dry-run`.
- `.gitignore` covers `config/x-accounts.json` and `config/topics.json` in addition to the channel and subreddit files.

## Notes

- This skill only finds topics. It does not write content. Pair it with your own writing workflow.
- The rubric is honest about depth. It drops hot topics that have no real source material behind them, and it says "quiet week" instead of inventing a top 5.
- Re-run weekly. Trending shifts fast in fast-moving niches.
