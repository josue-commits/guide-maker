---
name: ask-guide-maker
description: "Ask which skill or step fits where you are in the week. A router over the guide-maker skills."
disable-model-invocation: true
---

# Ask Guide Maker

Six skills, one pipeline, and a week that rarely starts at the beginning of it. This skill maps where you are to the step that fits. It runs nothing; it names the entry point and what to hand it.

The runbook lives in the `make-guide` pipeline table ([../make-guide/SKILL.md](../make-guide/SKILL.md), section 1). This page adds the on-ramps and the failure paths; [FLOWS.md](./FLOWS.md) has the long branches. One page per skill under `docs/skills/` at the repo root explains each one on its own.

## The main flow: topic to post

The route most weeks travel. `/make-guide` drives the whole chain from one sentence, and every hop can be entered alone.

1. **`/topic-finder`** scans your channels, subreddits and X accounts, prints the scan-health block first, and hands you a ranked briefing; you pick one topic and its URLs go to the next step. A YouTube URL or a transcript you already have skips this hop.
2. **`/make-guide` Phase 1** reads the source, verifies every claim, checks what you already shipped, and hands back the **outline**: guide type, title, subpages, sources, and a one-word **keyword** derived from the title, already checked for collisions.
3. **Gate 1, yours.** You approve or edit the outline, the title and the keyword. Nothing is written before this.
4. **`/make-guide` Phase 2** writes the guide, three copy variations, every DM version the config allows, a cover recommendation and a **graphic brief**, and lints all of it until the linter exits 0.
5. **Gate 2, yours** (`workflow.gates: two`). You read the hooks, the subpage summaries and the DMs before anything reaches Notion.
6. **Publish** sends the hub and subpages to the Guide Database and hands back the **hub page id**; the cover goes on that page next, and it never carries the keyword.
7. **`/graphics-maker`** takes the graphic brief and the keyword and returns the post PNG with the CTA bar typeset across the bottom; you read the keyword on it character by character.
8. **The board card** takes the title, keyword, guide link, the three copy toggles, the DM toggles and the graphic, one card per guide.
9. **`/dm-automation`** takes the **public URL** of the hub page, the keyword and the graphic, and either writes the paste-ready bundle with a checklist (manual) or schedules the post with the keyword automation attached (adapter), dry run first.
10. **You** publish the Notion page to the web (that is what makes the public URL resolve), pick one of the three variations, and post. No script does any of these three.

### Context hygiene

Keep steps 2 through 6 in one session: the outline, the writing and the publish build on the same research, and the writer agent's Phase 2 wants the approved outline verbatim. Steps 7 through 9 can start fresh: everything they need (title, keyword, hub page id, graphic brief) is on the board card or in the work dir, so a new session that reads the card loses nothing.

## On-ramps

Where you are on the left, where to enter on the right.

| Situation | Entry point |
|---|---|
| I have a YouTube URL | `/make-guide`: "make a guide from this video: <url>". Phase 1 pulls the transcript with yt-dlp. |
| I have a transcript, a doc, or a repo README | `/make-guide`: "make a guide about <topic>, here is the transcript: <paste>". Same Phase 1, no yt-dlp. |
| I have a topic and no source | `/topic-finder` if the topic is in your niche lists, otherwise give `/make-guide` the official docs URL; it refuses to research from a web search alone. |
| I do not know what to write this week | `/topic-finder`: "find me a topic". Read the scan-health block before the ranking. |
| I need a graphic for a post that already exists | `/graphics-maker`: `card` with the title, a subtitle and the keyword. Free, under a minute. |
| The keyword is taken | `/make-guide` before Gate 1: derive a new one from the title, run `keyword_check.py` again. FLOWS.md has the branch. |
| The guide is in Notion, I only need the copy | `/make-guide`: "write the copy for this guide" with the hub URL. Phase 2 copy only, lint included. |
| The post is scheduled, I need the DMs | `/dm-automation`: `render` with the public URL, then `keywords --check`, then `attach --dry-run` on the live post if you use an adapter. |
| Reach dropped on the last post | Open the post: is the keyword, or any "comment", "like", "repost" line, in the copy? `lint_copy.py copy` on the text tells you; `docs/strategy.md` has the numbers. |
| Monday's post did well, what did it get | `/dm-automation`: `stats --range weekly` on an adapter. Manual: your DM tool's dashboard, then the Impressions, Comments and DMs Sent numbers on the board card. |
| Pages show a `Page icon:` line | `/make-guide`: `scan_published_leaks.py`, then republish the subpages it names. |
| The DM link is dead | You have not published the page to the web. Share, Publish in Notion, then `md_to_notion.py public-url --page-id <id> --check` turns green. |
| I want to change my Notion database, DM tool or provider | `/setup-guide-maker` again. It updates the config in place. |

## Standalone

Off the main flow entirely.

- **A topic scan without a guide**: `/topic-finder` on its own. It only finds topics and says so honestly when nothing is trending.
- **Lint on any text**: `make-guide/scripts/lint_copy.py copy <file> --keyword <KW>` for post copy, `lint_copy.py dm <file>` for a DM. Works on text that never came from the pipeline.
- **A cover for an old page**: `make-guide/scripts/banner_generator.py simple --title "..." --keyword <KW> --upload-to <page id>`. `--keyword` is a guard: the command refuses a title that equals the keyword, because the cover never carries it.
- **The leak scan**: `make-guide/scripts/scan_published_leaks.py` walks every published hub and subpage for directive lines and placeholders.
- **A keyword check on its own**: `make-guide/scripts/keyword_check.py <KW>` (shape, then the board, the Guide DB and the DM tool).

## Release gates you hold

Five checks the orchestrator does not ask you about. When you review a finished bundle, look at these:

1. **The cover is on the hub page.** Open the hub page in Notion: there is an image at the top, and the keyword is not on it.
2. **The CTA bar reads the keyword.** Open the final PNG at feed size and read the keyword letter by letter against the board card. Then check the wording is one of the two canonical strings, not a variant.
3. **Every lint exited 0.** Three copy files, every DM file. A warning (exit 2) is read and decided; an error (exit 1) never ships.
4. **The keyword is unique.** `keyword_check.py` exit 0, and the same spelling on the card, the graphic and in the DM tool.
5. **No `[Verify: ...]` survives.** Grep the work dir and the published pages; a placeholder on a live page is a claim nobody checked.

## Precondition

**`/setup-guide-maker`** once per project, before the first guide. It writes `.guide-maker/config.yaml`, the overrides and the `## Agent skills` block, and ends with the doctor.

What each skill does without it:

| Skill | Without setup |
|---|---|
| `make-guide` | Hard. Refuses to start a pipeline on a red doctor line; no Guide Database id means no publish. |
| `dm-automation` | Hard. Needs the author, the community and the public domain to render a DM. |
| `graphics-maker` | Soft. `card` runs on defaults with any keyword; brand colors and a provider are config. |
| `topic-finder` | Soft. Runs with `--config-dir` pointed at any folder holding the source lists. |
| `ask-guide-maker` | Runs. It is this page. |

## Further reading

- [../make-guide/SKILL.md](../make-guide/SKILL.md): the pipeline table, the gate model, every command
- [FLOWS.md](./FLOWS.md): what each hop consumes and produces, what to do when a gate fails, the three-guides-a-week worked example
- `docs/skills/<name>.md` at the repo root: one page per skill ([make-guide](../../docs/skills/make-guide.md), [topic-finder](../../docs/skills/topic-finder.md), [graphics-maker](../../docs/skills/graphics-maker.md), [dm-automation](../../docs/skills/dm-automation.md), [setup-guide-maker](../../docs/skills/setup-guide-maker.md), [ask-guide-maker](../../docs/skills/ask-guide-maker.md))
- [docs/strategy.md](../../docs/strategy.md): why the keyword lives in the graphic
- [docs/troubleshooting.md](../../docs/troubleshooting.md): the doctor's FAIL lines and their fixes
