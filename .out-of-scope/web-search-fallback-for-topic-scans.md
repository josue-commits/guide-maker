# Web search as a fallback when a topic scan fails

When a scanner returns nothing (no config, no token, a dead channel list, a renamed Apify actor) Phase 0 stops and says which source failed. Requests to fall back to web search so the briefing is never empty are out of scope.

## Why

- A silent fallback hides the failure that needs fixing. The operator sees a briefing, not a broken scanner, and the broken scanner stays broken for weeks.
- Web search results are not the signal. The three sources are curated lists the operator chose; a search engine's top ten for "AI tools this week" is whoever paid for placement.
- The health gate exists so the writer can trust the research. `health.json` carries `web_search_used: false` as a hard contract; a caller that sees `true` is supposed to refuse the briefing.

## What to do instead

- Read `health.json`. It names the dead source and, for YouTube, the channel handles that returned errors.
- `scan_all.py --sources youtube,reddit` scans the sources that work and reports the one that was skipped, in the open.
- Fix the config in `.guide-maker/topic-finder/` or the token, and re-run.
