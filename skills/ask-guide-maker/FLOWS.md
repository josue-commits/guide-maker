# Flows

The long branches behind [SKILL.md](./SKILL.md). Three parts: what each hop of the main flow consumes and produces, what to do when a gate fails, and one worked week with three guides.

Paths below are relative to the skills root (`make-guide/scripts/...`); every command takes `--config <path>` and the path comes from `doctor.py --print-paths`.

## 1. The hops

| Hop | Consumes | Produces | Handoff to the next hop |
|---|---|---|---|
| `topic-finder` scan | the source lists in `.guide-maker/topic-finder/`, the exclusion list (Guide DB titles, board keywords) | `health.json`, `topics.json`, a ranked briefing | the URLs of the topic you picked |
| `make-guide` Phase 1 | a URL, a transcript or those URLs | the outline: type, title, 4 to 7 subpages, sources tagged official / institutional / creator-research-only, gap analysis, `[Verify: ...]` items, a keyword | the outline and the keyword |
| `keyword_check.py` | the keyword | exit 0, or the collision it found | a keyword that is free |
| Gate 1 | the outline | your approval or edits | the approved outline |
| `make-guide` Phase 2 | the approved outline, the keyword, the recent closer log | `hub.md`, `NN-step.md` per subpage, `copy/<account>-<hook>.txt` x3, `dm/<version>.txt`, a cover recommendation, a graphic brief | the work dir |
| `lint_copy.py copy`, `lint_copy.py dm` | the copy and DM files | exit 0, 1 (errors) or 2 (warnings) | clean files |
| Gate 2 | hooks, subpage summaries, DM versions, the two briefs | your approval or edits | the approved content |
| `publish_guide_hub.py` | `hub.md`, the subpage files, the sources, type, week, icon | `HUB_PAGE_ID`, the hub URL | the hub page id |
| `banner_generator.py` | a short title, the page id | the cover PNG, uploaded to the hub page | nothing; this is a gate |
| `graphics-maker` | the graphic brief, the keyword | the post PNG with the CTA bar, C2PA stripped, and the rendered CTA string printed | the PNG |
| `md_to_notion.py create-content-entry` | title, keyword, post date, the hub URL, three copy files, the DM files, the PNG | the board card with the graphic on its `Graphic` property | the card |
| `md_to_notion.py public-url --check` | the hub page id | exit 0 when the public URL answers 200 | the public URL |
| `dm-automation render` | the public URL, the guide title | one plain-text file per DM version | the DM files |
| `dm-automation schedule` or `attach` | post copy, the PNG, the time, the keyword, the DM files | manual: `dm-bundle/` with `post.txt`, `dm-*.txt`, the graphic, `checklist.md`; adapter: the scheduled post and a paused automation | the checklist, or the automation to flip on |
| You | the public page, three variations, the bundle | a live post with the graphic, the automation running | next week |

The keyword crosses every hop from Phase 1 on. It must be the same string on the outline, the card, the PNG and in the DM tool. When any two disagree, nothing fires: the tool watches for one word and the graphic asks for another.

## 2. When a gate fails

Each branch below is a loop back to a named hop, not a workaround. There is no fallback for a failed gate, because the copy is forbidden from carrying the keyword and the DM is the only delivery path.

### Lint failure

`lint_copy.py copy` or `lint_copy.py dm` exits 1.

- Read the rule name in the output. `keyword-in-copy`, `em-dash`, `banned-word`, `banned-cta`, `word-count` on copy; `name-tag`, `hard-wrap`, `public-url`, `max-lines` on a DM.
- A structural finding (the keyword in the text, a banned CTA line, a hook that is not the one asked for) goes back to the writer agent with the findings pasted in; it rewrites and re-lints.
- A local finding (one em dash, one banned word, one line too many in a DM) you fix by hand in the file and re-run the linter.
- Exit 2 is a warning. Read it, decide, and say what you decided. It does not block.
- Never widen `copy.words` or add to the closers list to make a failing file pass. Change the config between weeks, on purpose, not mid-lint.

### Keyword collision

`keyword_check.py KEYWORD` exits 1 and names where it found the keyword: the board, a Guide DB title, or the DM tool.

- Derive another word from the same title. `ENGINE` from Lead Engine, `FLOWS` from workflows; one word, 3 to 12 capitals, never arbitrary.
- Run the check again. Repeat until exit 0.
- This happens before Gate 1. If a collision surfaces later (the DM tool had an automation the offline check could not see), the new keyword has to reach three places: the board card, the graphic (regenerate it; do not edit the old PNG), and the DM automation. Then re-read the graphic.

### Cover missing

The hub page has no cover, or `workflow.cover_required` is true and the doctor or the orchestrator flagged it.

- `banner_generator.py simple --title "Short Title" --keyword KEYWORD --output <work>/cover.png --upload-to HUB_PAGE_ID`. Free, Pillow, seconds.
- `ai` mode needs a provider key and costs cents; `upload` puts an image you already have on the page.
- The cover never carries the keyword. If it does, it is a post graphic in the wrong place; make a new cover.
- The guide is not "ready" until this exists. Do not create the board card or render DMs around a hub page with no cover.

### CTA bar misspelled, missing or illegible

You opened the final PNG and the keyword does not read exactly as the board card spells it, or the bar is absent, or it is too small at feed scale.

- With `graphics.cta_bar.renderer: pillow` (the default) the bar is typeset from real glyphs and cannot misspell. A misspelling means the string passed to `finalize` or `card` was wrong: run it again with the right keyword and read the printed CTA string against the card.
- With `renderer: model` the provider drew the bar. Switch to `pillow` and run `finalize` on the scene; do not retry the model until it spells it right.
- Missing: `graphics_generate.py finalize --image <png> --keyword KEYWORD` adds it to any local PNG.
- Illegible: raise `graphics.cta_bar.height_pct` slightly, or set `cta_bar.bg` and `cta_bar.fg` for contrast, and finalize again.
- The wording must be one of the two canonical strings in `graphics-maker/references/cta-bar.md`. A third phrasing does not ship even when it reads fine.

### Public URL 404

`md_to_notion.py public-url --page-id <id> --check` exits 1, or the checklist's `curl` line does not answer 200.

- The page is not published to the web. Notion's API cannot do it; the user opens the hub page, Share, Publish. Every subpage inherits.
- Until it answers 200, no DM goes live: the manual checklist stays unchecked and an adapter automation stays paused. Scheduling the post is fine; flipping the automation on is not.
- `notion.public_domain` empty means the skill cannot even build the URL. Set it (`<workspace>.notion.site`) with `/setup-guide-maker` or by editing the config, then check again.
- A `notion.so` or `app.notion.com` link in a DM is the same failure one step earlier: `lint_copy.py dm` rejects it, and `dm-automation render` exits 2 on it.

### Scan health FAIL

`scan_all.py` exited 1, or `health.json` shows a source under its threshold (`topic_finder.scan_health` in the config).

- Read `health.json` before any topic. `youtube.errors` lists dead or renamed channels: fix the handle in `.guide-maker/topic-finder/youtube-channels.json`. An empty `reddit` or `x` block with a token present means the Apify actor changed; the scanner prints the slug it called.
- No Apify token: set `topic_finder.sources: [youtube]` and scan again, or add the token. Do not fill the gap with a web search; the writer agent refuses to, and so should you. The briefing says which source was missing.
- A source under threshold with real config and a real token is a stop. Tell the user what failed and pick a source they already have (a URL, a transcript) for this week.

## 3. One worked week: three guides

The cadence the pipeline was built for: a guide on Monday, Wednesday and Friday, each with its own keyword, posted at the same early-morning slot. Days below are the posting days; the work happens the week before and the weekend.

**Weekend before.** Run `/topic-finder` once. Read the scan-health block, then the ranking: the two YouTube tracks scored apart, X ranked on bookmarks. Pick three topics, ideally one with a sales or go-to-market angle for Friday. Run `keyword_check.py --list` once so the exclusion list is fresh. Then, one topic at a time, `/make-guide` Phase 1 for each, Gate 1 for each, three approved outlines with three distinct keywords. Check the three against each other too: `keyword_check.py` sees the board, not the other two outlines sitting in the work dir.

**Sunday to Monday, guide A.** Phase 2, lint, Gate 2, publish, cover, graphic, card, `public-url --check`. Publish the hub page to the web. Render the DMs, `schedule --dry-run`, then `schedule` for Monday's slot with the graphic and the keyword automation; manual users open `dm-bundle/checklist.md` and follow it in their tool. Read the graphic one last time. Log the closer used.

**Monday morning.** The post goes out with the graphic. Watch the first comment: confirm the DM fired and the link opened. If the DM did not fire, the keyword on the automation differs from the one on the graphic; fix the automation, never the graphic.

**Monday to Wednesday, guide B.** Same sequence as guide A. Before Phase 2, `lint_copy.py rotation --log <state>/closer-log.jsonl` so the closer is not the one Monday used. Before the card, `keyword_check.py` again: Monday's keyword is on the board now.

**Wednesday to Friday, guide C.** Same sequence. Three different closers across the week, three different keywords, three cards on the board.

**Friday afternoon.** Fill Impressions, Comments and DMs Sent on the three cards (`dm-automation stats` on an adapter, your tool's dashboard otherwise). Move the winner into `.guide-maker/top-performers.md` once it has real numbers. Run `/topic-finder` for next week.

What repeats every slot is the same three checks: the guide is published (to Notion and to the web), the copy ends on a value line with the keyword nowhere in the text, and the keyword is set in the DM tool and spelled the same on the graphic.

Sessions: the weekend Phase 1 runs can share one session per guide (research and outline together). Each Phase 2 through card run is its own session that starts from the approved outline. Graphics and DMs for a guide can start cold from the board card.
