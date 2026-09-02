---
name: guide-maker
description: "Turn YouTube videos into polished Notion guides with LinkedIn lead magnet copy. Use when the user provides a YouTube URL, transcript, or asks to create a guide/lead magnet. Also triggers on 'find me a topic', 'what's trending', 'make a guide from this', 'create a lead magnet', or 'turn this into a guide'."
---

# Guide Maker

## Setup

Before first use, check if `config.yaml` exists in this skill's directory.

If it doesn't exist:
1. Tell the user: "This is your first time using Guide Maker. Let's set it up."
2. Copy `config.example.yaml` to `config.yaml`
3. Walk the user through filling in the required fields:
   - **Notion API key** — Link them to https://www.notion.so/my-integrations. They need to create an integration, copy the secret, and share their target database with it.
   - **Guide Database ID** — Explain how to create the database (properties: Guide Title as title, Type as select, Week as date, Keyword as rich_text, Status as select). Show them how to find the database ID from the Notion URL.
   - **Author name** — Their name for the guide byline.
   - **LinkedIn URL** — Their LinkedIn profile URL for the byline link.
4. Ask about optional fields:
   - Community URL (for a callout at the top of guides)
   - KieAI API key (for AI-generated banners, $0.03 each)
   - Multi-account posting (additional LinkedIn accounts)
   - Content Board database (for tracking LinkedIn post performance)
5. Test the Notion connection by reading the database via the Notion API. If it fails, help them troubleshoot (usually a sharing permission issue).

Once config.yaml exists, load it at the start of every run. Use the values throughout the pipeline.

Resolve `SKILL_DIR` (the absolute path of this skill folder) once and pass it into every spawn prompt and every script call. The working directory is the project root, not the skill, so relative `scripts/...` paths fail.

---

## Pipeline Overview

| Step | What | Reference |
|------|------|-----------|
| 0 | Topic research (optional) | sibling skill `topic-finder` (`scripts/scan_all.py`, `health.json`) |
| 1 | Get source material | `references/writing/guide-spec.md` (source extraction section) |
| 2 | Classify guide type | `references/guides/guide-types.md` |
| 3 | Research and verify | (inline below) |
| 4 | Write the guide | `references/writing/guide-spec.md`, `references/writing/humanizer.md` |
| 5 | Structure as hub + subpages | `references/guides/hub-page-layout.md` |
| 6 | Publish to Notion + banner | `scripts/publish_guide_hub.py`, `scripts/banner_generator.py` |
| 7 | Quality check | (inline below) |
| 8 | Create Content Board entries | (optional, requires `content_board_database_id` in config) |

If something breaks, check `references/troubleshooting.md`.

---

## Phase 0: Topic Research (Optional)

Topic research lives in the sibling skill **topic-finder** (YouTube via yt-dlp, Reddit and X via Apify, then a correlation pass). guide-maker does not scan anything itself. Resolve the sibling first:

```bash
python3 -c "import sys; sys.path.insert(0, '{SKILL_DIR}/scripts'); from _config import sibling; print(sibling('topic-finder'))"
```

If that prints a `FileNotFoundError`, tell the user the install hint it contains (clone `josue-commits/topic-finder` next to guide-maker, or set `GUIDE_MAKER_SKILLS_DIR`) and **stop Phase 0**. Never fall back to web search: a briefing built on a silent fallback looks authoritative and misses the direct hits the scan exists to find.

When the sibling is present, spawn the writer agent:

```
Task(
  subagent_type="general-purpose",
  prompt="Read {SKILL_DIR}/AGENT.md in full. SKILL_DIR={SKILL_DIR}. Run Phase 0: Topic Research. Run {TOPIC_FINDER_DIR}/scripts/scan_all.py --sources youtube,reddit,x --out-dir {WORK_DIR}/scan, read {WORK_DIR}/scan/health.json, print the scan-health block first, then cluster, score and return the ranked briefing. Exclude these already-published titles and keywords: [list]. Do NOT spawn sub-agents or use the Task/Agent tool; do all the work yourself. Return the Phase 0 block.",
  run_in_background=true
)
```

`health.json` is the contract between the two skills:

```json
{"config_present": {"youtube": true, "reddit": true, "x": false},
 "youtube": {"channels_configured": 12, "channels_with_videos": 10, "videos": 39, "errors": []},
 "reddit": {"subs": 8, "posts": 84},
 "x": {"accounts": 0, "posts": 0, "cost_usd": 0.0},
 "correlation": {"topics_2plus": 6, "topics_all": 2},
 "web_search_used": false}
```

The agent applies the thresholds in `config.topic_finder.scan_health` to that file and refuses to rank if a configured source came back empty or `web_search_used` is true. Present the briefing to the user. Once they pick a topic, hand the selected URLs to Phase 1.

---

## Phase 1: Source Intake + Research + Outline

When the user provides a YouTube URL, transcript, or topic:

1. Load `config.yaml` for author info and account settings.
2. Spawn the writer agent:

```
Task(
  subagent_type="general-purpose",
  prompt="Read {SKILL_DIR}/AGENT.md in full. SKILL_DIR={SKILL_DIR} (absolute path of this skill). Do NOT spawn sub-agents or use the Task/Agent tool; do all the work yourself. Run Phase 1: Research + Outline. Source material: [URL/transcript/topic]. Return the outline, guide type classification, proposed keyword, and notes about source quality.",
  run_in_background=true
)
```

3. When the agent returns, present the outline to the user for review:
   - Guide type classification
   - Proposed title
   - Proposed keyword
   - Step-by-step outline with descriptions
   - Source material notes
4. Get approval before proceeding to Phase 2. The user may request changes to the outline, title, keyword, or structure.

### Phase 1 Output Format
- **guide_type**: "Technical Tutorial", "Strategic Framework", or "Comparison/Persuasion"
- **title**: Proposed guide title
- **keyword**: Proposed keyword (short, memorable, ALL CAPS)
- **outline**: List of steps, each with emoji, title, and 2-3 sentence description
- **sources**: List of source URLs (YouTube, docs, etc.)
- **notes**: Concerns about source material quality or coverage gaps

---

## Phase 2: Write Everything

After the user approves the outline:

1. Load `config.yaml` for account list, community settings, and author info.
2. Spawn the writer agent:

```
Task(
  subagent_type="general-purpose",
  prompt="Read {SKILL_DIR}/AGENT.md in full. SKILL_DIR={SKILL_DIR} (absolute path of this skill). Do NOT spawn sub-agents or use the Task/Agent tool; do all the work yourself. Run Phase 2: Write Everything. Config: [pass relevant config values]. Approved outline: [paste outline]. Keyword: [KEYWORD]. Write the full guide (hub + subpages), LinkedIn copy for each account, and DM templates. Return all content.",
  run_in_background=true
)
```

3. When the agent returns, present all content to the user for review:
   - Hub page content
   - Each subpage (summarize, offer to show full text)
   - LinkedIn copy variations (for each account)
   - DM templates
   - Banner recommendation
4. Get approval. The user may request edits to any piece.

### Phase 2 Output Format
- **hub_description**: One-sentence guide description for the hub callout
- **build_items**: "What You'll Build" bullet points
- **audience_items**: "Who This Is For" bullet points
- **nav_note**: Navigation callout text
- **subpage_files**: List of /tmp/ markdown file paths (one per step)
- **linkedin_copy**: 3 variations for each configured account
- **dm_templates**: Community DM (if community_url configured) + Direct link DM
- **banner_recommendation**: Tools mentioned, suggested style, keyword for banner text

---

## Phase 3: Review with User

Present the content in a scannable format:

1. **Guide overview**: Title, type, keyword, number of subpages
2. **Hub page preview**: Description callout, What You'll Build, Who This Is For
3. **Subpage summaries**: One line per subpage with title and key topics
4. **LinkedIn copy**: Show hooks (first lines) for each variation per account. Offer to expand any variation the user wants to read in full.
5. **DM templates**: Show both versions
6. **Banner**: Describe the recommendation

The user approves, requests changes, or rejects. If changes are needed, either make them directly (small edits) or re-spawn the agent (structural changes).

---

## Phase 4: Publish to Notion

After approval:

1. **Publish the hub page and subpages** in one call. The script creates the Guide Database entry (title, type, week, keyword, status), publishes every `--step` markdown file as a child page, then writes the hub body with links to each step. It reads the database ID, author byline and community callout from `config.yaml`.
   ```bash
   python3 scripts/publish_guide_hub.py \
     --title "Guide Title" \
     --description "One-sentence guide description" \
     --keyword "KEYWORD" \
     --type "Technical Tutorial" \
     --week "YYYY-MM-DD" \
     --icon "🛠️" \
     --build-item "Outcome the reader gets" \
     --audience-item "Who this is for" \
     --nav-note "Start at Step 1 unless you already have X." \
     --step "⚡|Short Title|Description paragraph|/tmp/guides/01-step.md" \
     --step "🧩|Short Title|Description paragraph|/tmp/guides/02-step.md" \
     --source "Official docs|Tool documentation|https://example.com/docs"
   ```
   Add `--dry-run` to print the plan without touching Notion. The output includes the hub page ID you need next.

2. **Generate and upload the cover.** Three subcommands: `simple` (Pillow, free), `ai` (KieAI, needs a key), `upload` (an existing PNG).
   ```bash
   # Free, always works
   python3 scripts/banner_generator.py simple \
     --title "Short Guide Title" --subtitle "Optional line" \
     --style dark --output /tmp/guides/cover.png --upload-to HUB_PAGE_ID

   # AI cover with real logo references (see references/banner-guide.md)
   python3 scripts/banner_generator.py ai \
     --prompt "White background banner ..." \
     --ref-image "https://.../logo.png" \
     --output /tmp/guides/cover.png --upload-to HUB_PAGE_ID

   # Upload a cover you already have
   python3 scripts/banner_generator.py upload --file /tmp/guides/cover.png --page-id HUB_PAGE_ID
   ```
   `--upload-to` sets the image as the page cover. If `ai` fails it falls back to `simple` automatically.

3. **Verify**: open the published guide URL and confirm every block rendered, then share the URL with the user.

---

## Phase 5: Create Content Board Entries (Optional)

Only run this phase if `content_board_database_id` is set in config.yaml.

For each configured account:
1. Create a Content Board entry with:
   - Title (guide title)
   - Account name
   - Post Date
   - Type: "guide"
   - Status: "Draft"
   - Keyword
   - Guide Link (URL to the published guide)
2. Add LinkedIn copy as toggle blocks (3 variations per account)
3. Add DM templates below a divider

Toggle format:
- Toggle title = hook type ("Contrarian Hook", "Problem/Pain Hook", "Quantity/Build Hook")
- Toggle content = code block (plain text) for easy copy/paste

DM template format:
- Divider
- H2: "DM Templates"
- Toggle (H3): "Community DM" (only if community_url is configured)
- Toggle (H3): "Direct Guide Link DM"

---

## Step 3: Research and Verify (Inline Reference)

Before writing a single word of guide content:
- Web search every tool, software, and platform mentioned
- Verify all URLs. Never include a URL you haven't confirmed works.
- Check current pricing, version numbers, feature availability
- Find official documentation links for tools discussed
- If you cannot verify a URL, mark it as "[Verify: tool-name documentation]"

---

## Quality Check

Before presenting content to the user, verify:

**Guide content:**
- Every section has real substance, no filler
- All code blocks are syntactically correct and copy-paste ready
- All URLs verified via web search
- No hallucinated tools, features, or capabilities
- H1 only for title, H2 has emoji prefix, H3 for subsections
- No banned AI vocabulary or phrases (humanizer filter)
- Title compelling enough to make someone comment on LinkedIn

**LinkedIn copy:**
- Each variation is 180-250 words (reject under 140 or over 300)
- Zero emojis in body (only the pointing-down emoji on the last line)
- Zero em dashes
- Zero markdown formatting
- Zero hashtags
- Prose by default; arrow bullets only for a genuine framework
- 3 variations are genuinely different hooks (contrarian, problem/pain, quantity/build) on the prose 8-beat skeleton
- No banned vocabulary or phrases
- CTA is one value line ending on the pointing-down emoji; the keyword is absent from the text (it lives in the post graphic, see `references/strategy/cta-evidence.md`)

**DM templates:**
- Personalized with guide topic
- Correct links (community URL or direct guide link)
- Human tone, not automated-sounding
- Concise (3-5 short paragraphs max)

---

## Key Rules

1. **Humanizer is always on.** Every sentence runs through the banned vocabulary and pattern filter. No exceptions. Read `references/writing/humanizer.md` for the full list.
2. **Never include unverified URLs.** If you can't confirm a link works, flag it for the user.
3. **Read the example guides** matching your detected type before writing. Match their depth, formatting density, and tone. Examples are in `references/guides/examples/`.
4. **Present classification and outline before writing.** Don't write the full guide without the user's approval on the direction.
5. **One guide per week, then move on.** Timely content beats recycled content.
6. **Unique keyword per guide.** Enables tracking across LinkedIn accounts.
7. **Never create guide files in the project directory.** Use `/tmp/` for all intermediate files. Guides live in Notion only.
8. **Account handling is config-driven.** Read accounts from `config.yaml`. Could be 1 account or 10. Generate copy for each.
9. **Community CTA is conditional.** Only include the community callout on hub pages if `community_url` is set in config.yaml.
10. **Guide sources stay clean.** Never include YouTube video URLs as sources in the published guide. Only link to official documentation, blog posts, and other non-video external resources. YouTube videos are research inputs, not reader citations.

---

## Tools

| Tool | Purpose |
|------|---------|
| `yt-dlp` (path from config.yaml) | Extract YouTube transcripts |
| `WebSearch` / `WebFetch` | Research topics, verify URLs, check pricing |
| `scripts/md_to_notion.py` | Convert markdown to Notion blocks and publish subpages |
| `scripts/publish_guide_hub.py` | Create hub page with subpage links and structure |
| `scripts/banner_generator.py` | Generate banners (KieAI or Pillow) and upload to Notion |
| `topic-finder` (sibling skill) | Scan YouTube, Reddit and X for topics; writes `health.json` |
