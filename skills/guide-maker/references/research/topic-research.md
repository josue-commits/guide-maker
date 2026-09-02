# Topic Research: gates the writer agent applies in Phase 0 and Phase 1

Phase 0 finds topics. Phase 1 turns one into an outline. Both have gates that reject work before it is written, because a thin topic produces a thin guide no matter how good the writing is. Every threshold here is a config key so you can tune it; the defaults are what worked for a three-guides-a-week cadence.

## 1. Scan-health gate (Phase 0, first thing printed)

`topic-finder/scripts/scan_all.py` writes `health.json` next to the scan outputs. The agent prints a scan-health block **before** any ranking and stops when the scan did not run:

```
Scan health:
- Config: youtube [present] reddit [present] x [MISSING]
- YouTube: 39 videos across 10/12 channels (2 errors: members-only, 404)
- Reddit: 84 posts across 8 subs
- X: 0 posts across 0 accounts ($0.00)
- Correlation: 6 topics on 2+ sources, 2 on all
- Web search used: no
```

Stop conditions (`topic_finder.scan_health`):

| Condition | Key |
|-----------|-----|
| A configured source has no config file | `fail_on_missing_config: true` |
| YouTube returned no videos, or fewer channels with videos than the floor | `min_channels_with_videos: 5` |
| Reddit or X returned fewer posts than the floor for a configured source | `min_reddit_posts: 1`, `min_x_posts: 1` |
| `web_search_used` is true | always |

A dead source is a failure to fix, not a fallback. A briefing built on web search looks authoritative and misses the direct hits the scan exists to find; that is worse than no briefing.

## 2. Two YouTube tracks, scored apart

`topic_finder.youtube_tracks` names the channel categories (default `tool` and `business`). Score and surface them separately, never as one merged list. A "how I made money with X" video judged on the tool rubric either never surfaces or produces a get-rich-quick guide. The business track exists to supply topics with a sales or go-to-market angle; that angle is a preference for a slot, not a gate on the topic.

## 3. X ranked on bookmarks, never views

Views track jokes; bookmarks track "I will come back and study this". `topic_finder.x_bookmark_rate`: above `substance` (0.8%) is substance, below `noise` (0.1%) is noise. In one test window a 1.8M-view meme scored 0.07% and an 81K-view technical explainer scored 1.33%.

**Tweet text is a lead, not a source.** The same lecture gets reposted at three different stated runtimes; one real statistic gets recycled at four different numbers with three different employers attached. The linked videos and articles are real; the framing around them is not. Trace every number and every named talk to a first-party page before it enters an outline.

## 4. Already covered

Before proposing a topic, check both (`research.check_already_covered`):

- **Guide DB titles.** Keywords are unique per guide but titles are what tell you a topic shipped. Query the Guide Database and read the title column.
- **Content Board keywords.** For collisions on the keyword itself.

Flag a genuinely new development on a covered topic as an "Update Opportunity" instead of dropping it silently.

## 5. Depth gate (Phase 0 final filter, Phase 1 re-check)

A topic advances only if it clears every row (`research.depth_gate`):

| Signal | Minimum | Key |
|--------|---------|-----|
| Official docs | at least one authoritative source (vendor docs, changelog, repo README) | `require_official_docs` |
| Authoritative sources | 3+ (docs, repos, institutional talks, blog posts) | `min_authoritative_sources` |
| Source runtime | 20+ minutes of video OR 10+ pages of written material | `min_video_minutes` / `min_written_pages` |
| Implementation paths | more than one valid approach, not a one-liner | (judgment) |
| Section depth | can fill `min_subpages` to `max_subpages` subpages with real code, commands or configs | `min_subpages` / `max_subpages` |
| Use-case framing | can it be packaged for a specific professional role? | (judgment; not required) |

**Hard rejects, no matter how hot** (`research.hard_reject`):
- News or drama with no tutorial payoff ("X company did Y")
- Single-feature announcements with no docs yet
- Topics where every existing source says the same two or three things
- Pure opinion or reaction content
- Anything matching `excluded_topics` (plain strings match case-insensitively; `/regex/` entries are regular expressions). Put competitor products and off-brand subjects here.

`research.auto_accept_patterns` is the opposite list: topic shapes you already know work for your audience (for example "a bundle of agent skills for one professional role"). Empty by default; fill it after a few weeks of data.

## 6. Gap analysis (Phase 1, `research.gap_analysis: required`)

Before outlining, answer in writing:

- What do existing guides on this topic already cover well?
- What are they missing? Usually: real configs, edge cases, non-obvious gotchas, opinionated recommendations.
- What will this guide explain that none of the existing sources handle?

Write the answer into the outline's "Who This Is For" and "What You'll Build". The guide must win on the gap, not duplicate coverage.

**The gap analysis stays internal.** It goes in the agent's return block to the orchestrator, never into the published body. See `sources-policy.md`, "No cross-guide references".

## 7. Verification (Phase 1, every claim)

- Web search every tool, platform and price mentioned. Never include a URL you have not confirmed works.
- Cross-reference what creators say against official docs or the repo. Creators get things wrong.
- If you cannot find the primary source for a claim, the claim does not go in the guide. Mark it `[Verify: ...]` in the outline so the orchestrator sees it; the leak scanner catches any that reach a published page.
