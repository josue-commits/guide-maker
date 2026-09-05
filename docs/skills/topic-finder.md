# topic-finder

## What it does

`topic-finder` scans three sources in your niche (YouTube channels in two tracks, subreddits, X accounts), clusters what they have in common, and returns a ranked briefing with every resource it found per topic and a health report on the scan itself. A topic that shows up on two sources in the same week is the strongest signal it produces; on all three, stronger still.

A dead source is a stop, never a web-search fallback. When a scanner returns nothing (no config, no token, wrong channel handles, a renamed actor) the run exits non-zero, `health.json` says which source and why, and no briefing is produced. Falling back to a search engine quietly is how a broken scanner stays broken for a month.

## When to reach for it

Type `/topic-finder`, or the agent reaches for it when you say "find me a topic", "what's trending", "what should I write about", "scan my channels", "scan reddit", "scan X". `make-guide` calls it for Phase 0.

| Your situation | Where to go |
|---|---|
| Topic ideas for anything (a video, a newsletter, a post) | `topic-finder` on its own |
| A topic that should become a guide | `topic-finder`, then [make-guide](./make-guide.md) with the pick and its URLs |
| A URL or transcript already in hand | Skip this; `make-guide` from Phase 1 |

## Prerequisites

| It needs | Notes |
|---|---|
| Source lists | `.guide-maker/topic-finder/youtube-channels.json`, `subreddits.json`, `x-accounts.json`, optional `topics.json`. `/setup-guide-maker` copies the examples in and offers the `ai-coding` preset; `scan_all.py --config-dir` points at them |
| `yt-dlp` on PATH | YouTube needs no API key. 2026.07.04 or newer for the fast `--flat` mode; older builds fall back to the full scan |
| An Apify token | `APIFY_TOKEN` or `~/.config/apify/api_key`, for Reddit and X. The free tier covers a weekly scan; `--dry-run` prints the cost first |
| From `config.yaml`, when `make-guide` drives it | `topic_finder` (sources, lookback days, tracks, `scan_health` thresholds, `x_bookmark_rate`) and `excluded_topics` |

Setup is a soft dependency: the skill runs from any folder of JSON lists.

## The health gate

The word to hold onto is **health**. Every run writes `health.json` next to the topic files: which sources had config, how many channels returned videos, how many posts each source kept, the X scan's cost, the dead channel handles, and `web_search_used`, which is always `false`. The caller reads it before it reads a single topic; `make-guide` prints it as the first block of the briefing and refuses to rank when `topic_finder.scan_health` thresholds are not met.

Two scoring rules come with the sources:

- **Two YouTube tracks, never merged.** Channels tagged `tool` teach how to use the thing; channels tagged `business` teach how to sell it. Each track gets its own top list. A business video scored on the tool rubric either never surfaces or produces a get-rich-quick guide.
- **X is ranked on bookmark rate, never views.** Views track jokes; bookmarks track "I will come back and study this". Above 0.8 percent is substance, below 0.1 percent is noise. Tweet text is a lead, not a source: engagement accounts recycle real talks under invented numbers, and every figure gets verified against a first-party page before it is quoted.

## Common questions

**Scan health FAIL: channels with videos below threshold.**

One or more YouTube handles are wrong, or the channel is members-only. `health.json` lists them under `youtube.errors`. Fix the handle in `.guide-maker/topic-finder/youtube-channels.json`.

**Reddit or X returned nothing.**

No `APIFY_TOKEN`, or the Apify actor was renamed. The scanner prints the actor slug it called; check it on apify.com and update the config file.

**`--flat` not supported.**

yt-dlp older than 2026.07.04. The scanner falls back to the full scan on its own; `pip install -U yt-dlp` for the faster path.

**Can it search the web when a source is empty?**

No, by design, and it will not gain that fallback: [`.out-of-scope/web-search-fallback-for-topic-scans.md`](../../.out-of-scope/web-search-fallback-for-topic-scans.md). Scan the sources that work with `--sources youtube,reddit` and fix the one that failed.

**Where did the config files go?**

In v2 they lived in the skill folder at `topic-finder/config/`. In v3 the real lists live in `.guide-maker/topic-finder/` in your project; the skill folder keeps only the `*.example.json` templates, because `npx skills update` replaces that folder.

**I found a bug in a scanner. Where do I fix it?**

Upstream, at the `topic-finder` repository. `skills/topic-finder/` here is a git subtree pinned to a tag; edits made in this tree are overwritten on the next pull.

## It's working if

- The briefing opens with a scan summary: channels scanned and how many returned videos, posts kept per source, the X cost, dead channels by handle.
- Each topic lists the sources it was found on, per platform, with the video, thread or post behind it.
- X entries show a bookmark count and a rate, not a view count.
- When a source fails you get a stop with the reason, not a shorter briefing.

## Where it fits

`topic-finder` is Phase 0 of the chain and a standalone for anything else you write. [make-guide](./make-guide.md) is its consumer, because the resources it lists per topic become Phase 1's inputs; `excluded_topics` in the shared config is how the two stay out of each other's way. When you are unsure where you are in the week, [ask-guide-maker](./ask-guide-maker.md) routes you.
