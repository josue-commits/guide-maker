---
name: guide-maker
description: "Turn a YouTube video, a transcript or a researched topic into a multi-page Notion guide plus the LinkedIn lead-magnet bundle around it: three copy variations, a cover, a post graphic that carries the keyword, DM templates and a Content Board card. Use when the user provides a YouTube URL or transcript, says 'make a guide from this', 'turn this into a lead magnet', 'create a Notion guide', 'write the copy for the guide', 'publish the guide', or asks 'find me a topic' / 'what's trending' / 'what should I write about'. Also use for partial steps: only the copy, only the DMs, only the publish."
---

# Guide Maker

You are the orchestrator. The writer agent (`AGENT.md`) does the heavy lifting in the background; you run the scripts, hold the gates, and talk to the user. Talk to the user in their language; everything the skill ships (guide, copy, DMs) is written in `workflow.language`.

## 0. Before anything

1. Resolve `SKILL_DIR`, the absolute path of this folder, and `SKILLS_ROOT`, its parent. Every command below uses absolute paths; the working directory is the project, not the skill.
2. Run the doctor. Never proceed on a red line.
   ```bash
   python3 {SKILL_DIR}/scripts/doctor.py
   ```
   No config yet? It says so. Copy `config.example.yaml` to `config.yaml`, walk the user through `docs/setup.md` at the repo root, run the doctor again. `--offline` skips the network checks, `--print-paths` shows what it resolved, `--migrate-config` prints a v2 file from a v1 one.
3. Load the config (`python3 {SKILL_DIR}/scripts/_config.py` prints the validation). `WORK_DIR` is `workflow.work_dir`. Guides are never written into the project directory.

## 1. Pipeline

| Step | What | Who | Reference |
|------|------|-----|-----------|
| 0 | Topic research (three sources, correlated) | writer agent via `topic-finder` | `references/research/topic-research.md` |
| 0.5 | Calibration read: CTA evidence, top performers, voice | writer agent | `references/strategy/cta-evidence.md` |
| 1 | Intake, research, outline, keyword | writer agent | `references/research/*`, `references/guides/guide-types.md` |
| **G1** | User approves the outline | user | always |
| 2 | Write guide, copy, DMs; lint | writer agent | `references/writing/*`, `references/linkedin/*`, `references/dm/dm-guide.md` |
| lint | `lint_copy.py copy` and `dm` exit 0 | you | `scripts/lint_copy.py` |
| **G2** | User approves the content | user | only if `workflow.gates: two` |
| 3a | Publish hub + subpages | you | `references/publishing.md` |
| 3b | Cover on the hub page, never with the keyword, required | you | `references/banner-guide.md` |
| 3c | Post graphic with the CTA band | you via `graphics-maker` | sibling `SKILL.md`, `references/strategy/cta-evidence.md` |
| 3d | Content Board card + Graphic property | you | `references/content-board.md` |
| 3e | DM bundle or schedule | you via `dm-automation` | `references/dm/dm-guide.md` |
| Q | Quality gates | you | section 8 |

If something breaks, read `references/troubleshooting.md`.

## 2. Gate model

- **G1 is unconditional.** No content is written before the user approves the outline, title and keyword.
- **G2 is config.** `workflow.gates: two` (default) shows the user the copy and the guide before anything reaches Notion. `one` ships the bundle with sensible defaults after G1 and asks one consolidated question only when something is genuinely ambiguous.
- **Release gates that are not user gates.** You hold these yourself and do not ask: the cover exists on the hub page; the CTA band on the post graphic is read character by character and matches the Content Board keyword; every lint exits 0; the keyword is unique (`keyword_check.py`); no `[Verify: ...]` placeholder survives.
- **Steps the skill never does.** Publishing the Notion page to the web (the user does it in the Notion UI; DM links are dead until then). Posting to LinkedIn. Sending a DM by hand.

## 3. Spawning the writer agent

Use this prompt shape for every phase. The no-nested-agents line is not optional: a sub-agent that spawns a sub-agent dies and the work is lost silently.

```
Task(
  subagent_type="general-purpose",
  run_in_background=true,
  prompt="""Read {SKILL_DIR}/AGENT.md in full before doing anything.
PHASE: <0 | 1 | 2>
SKILL_DIR: {SKILL_DIR}
CONFIG: {SKILL_DIR}/config.yaml   (already validated by doctor.py)
WORK_DIR: {WORK_DIR}
TOPIC_FINDER_DIR: {SKILLS_ROOT}/topic-finder   (Phase 0 only)
INPUTS: <URL | transcript path | approved outline + keyword | topic pick>
EXCLUDE: <already-published titles and keywords, from the Guide DB and Content Board>
RECENT CLOSERS: <last three weeks from the closer log, Phase 2 only>
RULES: Do NOT spawn sub-agents or use the Task/Agent tool; do all the work yourself.
Absolute paths only. Write files under WORK_DIR, never into the project.
Run the linters named in AGENT.md until they exit 0.
RETURN the Phase <N> block exactly as AGENT.md specifies."""
)
```

## 4. Phase 0: topic research

1. `python3 -c "import sys; sys.path.insert(0,'{SKILL_DIR}/scripts'); from _config import sibling; print(sibling('topic-finder'))"`. If it raises, show the user the install hint and stop Phase 0. Never fall back to web search.
2. Pull the exclusion list: Guide DB titles and Content Board keywords (`keyword_check.py --list` when online).
3. Spawn Phase 0. The agent runs `scan_all.py --sources youtube,reddit,x --out-dir {WORK_DIR}/scan`, reads `health.json`, and prints the **scan-health block first**. A dead source is a stop, not a fallback.
4. Present the briefing: scan health, then 3 ranked topics (two YouTube tracks scored apart, X ranked on bookmarks), each with every resource found across sources. The user picks one; hand its URLs to Phase 1.

## 5. Phase 1: intake, research, outline

1. Spawn Phase 1 with the URL, transcript or topic. The agent extracts the transcript (yt-dlp), fetches official docs, verifies every claim, checks already-covered, applies the depth gate, writes the gap analysis, classifies the guide type (four types), outlines 4-7 subpages and derives a one-word keyword from the guide name.
2. Run `python3 {SKILL_DIR}/scripts/keyword_check.py KEYWORD --config {SKILL_DIR}/config.yaml`. Shape first (offline), then collisions against the Content Board, the Guide DB and the DM tool. A collision means a new keyword before G1.
3. Present the Phase 1 block: type, title, keyword, outline with per-step descriptions, sources tagged `official | institutional | creator-research-only`, gap analysis, `[Verify: ...]` items.
4. **G1.** The user approves or edits the outline, title or keyword.

## 6. Phase 2: write everything

1. Spawn Phase 2 with the approved outline, keyword, config and the recent closer log.
2. The agent writes `{WORK_DIR}/hub.md`, `{WORK_DIR}/NN-step.md` per subpage, three copy variations per account (`{WORK_DIR}/copy/<account>-<hook>.txt`), every DM version the config allows (`{WORK_DIR}/dm/<version>.txt`), a cover recommendation and a post-graphic brief. It runs the linters itself; you run them again:
   ```bash
   python3 {SKILL_DIR}/scripts/lint_copy.py copy {WORK_DIR}/copy/*.txt --keyword KEYWORD --config {SKILL_DIR}/config.yaml
   python3 {SKILL_DIR}/scripts/lint_copy.py dm {WORK_DIR}/dm/*.txt --config {SKILL_DIR}/config.yaml
   ```
   Exit 1 goes back to the agent with the findings. Exit 2 (warnings) you read and decide.
3. **G2** if `workflow.gates: two`: hooks of each variation, subpage summaries, DM versions, cover and graphic briefs. Expand anything the user asks for. Small edits you make; structural changes go back to the agent.

## 7. Phase 3: publish and package

Every command takes `--config {SKILL_DIR}/config.yaml` and `--dry-run` where it writes. Run the dry run first the first time you use a command in a session.

**3a. Hub + subpages**
```bash
python3 {SKILL_DIR}/scripts/publish_guide_hub.py --config {SKILL_DIR}/config.yaml \
  --title "Guide Title" --description "One sentence." --keyword KEYWORD \
  --type "Technical Tutorial" --week YYYY-MM-DD --icon "🛠️" \
  --build-item "..." --audience-item "..." --nav-note "..." \
  --step "⚡|Short title|Description|{WORK_DIR}/01-step.md" \
  --source "official|Title|https://..." --source "institutional|Title|https://..."
```
Creator-channel sources are refused by default. The output has `HUB_PAGE_ID`.

**3b. Cover (required, never the keyword)**
```bash
python3 {SKILL_DIR}/scripts/banner_generator.py --config {SKILL_DIR}/config.yaml simple \
  --title "Short Title" --keyword KEYWORD --output {WORK_DIR}/cover.png --upload-to HUB_PAGE_ID
```
`ai` and `upload` are the other subcommands (`references/banner-guide.md`). The guide is not "ready" until this exists.

**3c. Post graphic with the CTA band** (sibling `graphics-maker`; skip only if it is not installed, and say so)
```bash
G={SKILLS_ROOT}/graphics-maker/scripts
python3 $G/graphics_generate.py card --title "Short Title" --keyword KEYWORD --out {WORK_DIR}/graphic.png        # Pillow, free, default
python3 $G/graphics_generate.py scene --brief {WORK_DIR}/graphic-brief.md --out {WORK_DIR}/scene/ --estimate    # provider, two variants, no text
python3 $G/graphics_generate.py finalize {WORK_DIR}/scene/pick.png --keyword KEYWORD --out {WORK_DIR}/graphic.png   # CTA band + C2PA strip
python3 $G/cta_bar.py {WORK_DIR}/graphic.png --keyword KEYWORD --check
```
`text`, `single` and `tweak` exist for provider-rendered text. Whatever path you took, open the final PNG and read the keyword character by character. Misspelled, missing or illegible means it does not ship.

**3d. Content Board card** (skipped when `notion.content_board_database_id` is empty)
```bash
python3 {SKILL_DIR}/scripts/md_to_notion.py create-content-entry --config {SKILL_DIR}/config.yaml \
  --title "KEYWORD | Mon 09/07" --keyword KEYWORD --post-date YYYY-MM-DD --day Monday \
  --guide-link "https://www.notion.so/..." --status Draft --type guide \
  --variation "Contrarian Hook|@{WORK_DIR}/copy/main-contrarian.txt" \
  --variation "Problem/Pain Hook|@{WORK_DIR}/copy/main-problem_pain.txt" \
  --variation "Quantity/Build Hook|@{WORK_DIR}/copy/main-quantity_build.txt" \
  --dm "Direct|@{WORK_DIR}/dm/direct.txt" --dm "Combined|@{WORK_DIR}/dm/combined.txt" \
  --graphic {WORK_DIR}/graphic.png
```
One card per guide (`workflow.one_card_per: guide`); `account` makes one per account. The graphic goes on the `Graphic` files property, never as a body image.

**3e. DM bundle** (sibling `dm-automation`; without it, the DM toggles on the card are the deliverable)
```bash
D={SKILLS_ROOT}/dm-automation/scripts
python3 $D/dm_cli.py render --guide-url "$(python3 {SKILL_DIR}/scripts/md_to_notion.py public-url --page-id HUB_PAGE_ID)" --guide-title "Title" --out {WORK_DIR}/dm/
python3 $D/dm_cli.py schedule --keyword KEYWORD --dm {WORK_DIR}/dm/combined.txt --image {WORK_DIR}/graphic.png --dry-run
```
`dm_tool.provider: manual` writes a checklist; `leadshark` creates the automation paused. Before any DM goes live:
```bash
python3 {SKILL_DIR}/scripts/md_to_notion.py public-url --page-id HUB_PAGE_ID --check
```
Exit 1 means the user has not published the page to the web yet. Tell them; do not schedule.

Log the closers used: append `{"date": "YYYY-MM-DD", "closer": "..."}` per variation to `{WORK_DIR}/../closer-log.jsonl` and run `lint_copy.py rotation --log` before the next week's copy.

## 8. Quality gates (before "done")

- Guide: every section teaches something actionable; code blocks copy-paste ready; every URL verified; no hallucinated features; H2 with emoji, H3 plain; no banned vocabulary; no cross-guide references; no directive lines on the page (`scan_published_leaks.py` after the publish).
- Copy: `lint_copy.py copy` exit 0; three genuinely different hooks; prose by default; keyword absent from the text; one closer ending on the pointing-down emoji, three different closers.
- DMs: `lint_copy.py dm` exit 0; one destination per version; public guide URL.
- Assets: cover on the hub page; post graphic with a legible, correctly spelled keyword; graphic on the card's `Graphic` property.
- Keyword: unique (`keyword_check.py`), identical on the card, the graphic and in the DM tool.

## 9. Key rules

1. The keyword lives only in the post graphic. Never in the copy. `references/strategy/cta-evidence.md` has the numbers.
2. Two image assets per guide, not interchangeable: cover (no keyword) and post graphic (always the keyword).
3. Humanizer always on. `lint_copy.py` is the floor, not the ceiling.
4. Never an unverified URL. Never a claim without a primary source.
5. Creator videos are research, institutional talks are citable, no cross-guide references.
6. Read the example guide matching the type before writing; match its depth.
7. G1 always; G2 per config; release gates are yours.
8. One guide is one keyword, derived from the guide name, unique across the account.
9. Every spawn prompt carries the no-nested-agents line and absolute paths.
10. Guides are written under `WORK_DIR`, never into the project. They live in Notion.
11. The user publishes to the web by hand and posts by hand. The skill stops at the bundle.
12. Config over constants. If you are typing a name, URL, color or count, it belongs in `config.yaml`.

## 10. Tools

| Tool | Purpose |
|------|---------|
| `{SKILL_DIR}/scripts/doctor.py` | 12-line health check; `--offline`, `--json`, `--print-paths`, `--migrate-config` |
| `{SKILL_DIR}/scripts/_config.py` | Config loader shared by every skill; prints validation when run |
| `{SKILL_DIR}/scripts/publish_guide_hub.py` | Hub + subpages to the Guide DB |
| `{SKILL_DIR}/scripts/md_to_notion.py` | `blocks`, `publish-subpage`, `create-content-entry`, `public-url` |
| `{SKILL_DIR}/scripts/banner_generator.py` | Cover: `simple`, `ai`, `upload` |
| `{SKILL_DIR}/scripts/lint_copy.py` | `copy`, `dm`, `rotation` |
| `{SKILL_DIR}/scripts/keyword_check.py` | Shape and collision check |
| `{SKILL_DIR}/scripts/scan_published_leaks.py` | Sweep published pages for directives and placeholders |
| `{SKILLS_ROOT}/topic-finder/scripts/scan_all.py` | Three-source scan, `health.json` |
| `{SKILLS_ROOT}/graphics-maker/scripts/graphics_generate.py`, `cta_bar.py` | Post graphic with the CTA band |
| `{SKILLS_ROOT}/dm-automation/scripts/dm_cli.py` | Render DMs, schedule with the DM tool |
| `yt-dlp` (`tools.ytdlp_path` or PATH) | Transcripts |
| WebSearch / WebFetch | Verification |
