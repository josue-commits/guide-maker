# Topic Scoring Rubric

Score each clustered topic on three dimensions, then compute the composite. Three sources feed the clusters: YouTube (two tracks), Reddit, and X. `scripts/correlate.py` builds the clusters; this rubric ranks them.

## Rule 0: Two YouTube tracks, scored separately

Every channel in `config/youtube-channels.json` carries a `category`: `tool` (how to use the thing) or `business` (how to sell it, price it, build a business on it). Each video inherits it as `channel_category`.

Score the two tracks with their own top list and surface topics from both. Never merge them into one ranked list. A business video ("how I made 30k with AI agents") scored against the tool rubric either never surfaces or produces a get-rich-quick piece. A tool video scored against the business rubric looks like it has no angle. Neither is what you want.

When a cluster mixes tracks, that is a good sign: the same tool is being taught and sold in the same week. Note it in the briefing and pick the angle that fits the slot you are filling.

## Rule 1: X ranks on bookmarks, never views

For X posts use bookmarks and bookmark rate (bookmarks divided by views) as the engagement signal. Views track jokes, bookmarks track "I will come back and study this". From one real scan: a 1.8M-view meme scored 0.07 percent, an 81K-view technical explainer scored 1.33 percent.

| Bookmark rate | Read it as |
|---|---|
| above 0.8 percent | substance, count it toward Trending and Source depth |
| 0.1 to 0.8 percent | ordinary, count it toward Trending only |
| below 0.1 percent | noise, ignore it |

The thresholds live in `config/x-accounts.json` under `scan_defaults`. `scan_x.py` tags every post against them.

Tweet text is a lead, not a source. Accounts recut the same talk at different lengths and recycle one stat with swapped numbers and employers. Follow the link to the talk, repo or docs page and cite that. A post with no first-party link behind it counts for Trending and for nothing else.

## 1. Trending (Weight: 40%)

How much momentum does this topic have right now?

| Score | Meaning |
|-------|---------|
| 1-2 | One source, low engagement, fading |
| 3-4 | A couple of items on one platform, moderate engagement |
| 5-6 | Several items on one platform OR strong engagement on one item |
| 7-8 | Two platforms in the same week (any pair of YouTube, Reddit, X) |
| 9-10 | All three platforms in the same week, or two platforms plus recent (last 3 days) plus high engagement |

**Bonuses:**
- Recency: last 3 days beats last 7 days (+1)
- Two platforms in the same week: minimum score 7
- Three platforms in the same week: minimum score 9. This is the strongest signal the scan can produce
- Engagement in the top quartile of the scan (views, upvotes, or X bookmark rate): +1

**Penalties:**
- Single platform only: cap at 5
- Items older than 7 days: -2
- X items below the noise threshold do not count at all

## 2. Documentation (Weight: 30%)

Is there enough authoritative material to write a thorough piece?

| Score | Meaning |
|-------|---------|
| 1-2 | No official docs, no canonical source |
| 3-4 | Sparse docs, scattered blog posts only |
| 5-6 | Some official docs but incomplete |
| 7-8 | Solid official docs plus repos plus maintainer threads |
| 9-10 | Comprehensive docs, multiple primary sources, active maintainers |

**What counts as documentation:**
- Official product docs
- Repos with READMEs
- Maintainer blog posts, talks, or changelogs
- First-party lectures and engineer talks (often surfaced by the X scan)
- Discussion threads with maintainer engagement

**What does NOT count:**
- Reaction videos
- Hot-take blog posts
- Posts that summarize a talk without linking it
- Numbers that appear only in tweet text

## 3. Source Depth (Weight: 30%)

How rich are the sources you would be drawing from?

| Score | Meaning |
|-------|---------|
| 1-2 | Short clips, surface-level posts only |
| 3-4 | One decent tutorial OR one substantive thread |
| 5-6 | A couple of tutorials plus an active discussion |
| 7-8 | Long-form tutorials plus an active thread plus maintainer engagement |
| 9-10 | Multiple deep tutorials, comments rich with real-world use, working code samples |

**Tells of high source depth:**
- Videos 15 minutes or longer (YouTube, or native X video over the `long_form_seconds` threshold)
- Reddit threads with 50+ comments where commenters share their own implementations
- Code samples that work as-is
- Edge cases discussed (gotchas, failure modes)

## Composite Score

```
composite = (trending x 0.4) + (documentation x 0.3) + (source_depth x 0.3)
```

## Depth Bar (Drop Threshold)

Regardless of trending score, drop a topic if:
- Documentation is below 4 AND source depth is below 4
- All sources are reaction videos, hot takes, or posts with no primary material behind them
- The topic is purely speculative ("what if X did Y?") with no shipped product
- The only cross-platform evidence is X posts below the noise threshold

A topic that is hot with nothing real underneath produces a thin piece. Skip it and move to the next cluster.

## Honesty Rule

If nothing in the scan clears 6.5 composite, say so. Do not inflate scores to fill a list. A briefing that says "this week is quiet, here are 2 weak signals worth watching" is worth more than a fake top 5. `health.json` (see `health-contract.md`) tells you when a source came back empty, which is a different problem from a quiet week: report that as a broken source, not as a lack of topics.
