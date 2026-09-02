# Publishing to Notion

## Target
Guide Database on your Notion workspace (`notion.guide_database_id` in the config).

**CAUTION:** If this is a shared workspace, always confirm with the team before publishing. Use `--dry-run` first.

## Two image assets per guide

Every guide ships with two images and they are not interchangeable:

1. **The cover**, on the Notion hub page. Made here with `banner_generator.py`. It **never** carries the keyword.
2. **The post graphic**, on the LinkedIn post and uploaded to the Content Board `Graphic` property. Made by the `graphics-maker` sibling. It **always** carries the keyword in a full-width CTA band.

Producing only one and calling the guide done is the most common miss. A guide is not "ready for review" until the cover exists on the hub page and the post graphic has a legible keyword.

## Publishing Steps

1. Save all markdown files under `workflow.work_dir` (default `/tmp/guide-maker/`)
2. Present the complete guide to the user for review (Gate 2, if `workflow.gates: two`)
3. After approval, run the hub publisher:

```bash
python3 {SKILL_DIR}/scripts/publish_guide_hub.py \
  --config {SKILL_DIR}/config.yaml \
  --title "Guide Title Here" \
  --description "One-sentence guide description" \
  --keyword "KEYWORD" \
  --type "Technical Tutorial" \
  --week "YYYY-MM-DD" \
  --icon "🛠️" \
  --build-item "Outcome the reader gets" \
  --audience-item "Who this is for" \
  --nav-note "Start at Step 1 unless you already have X." \
  --step "⚡|Step Title|Step description paragraph|/tmp/guide-maker/01-step.md" \
  --step "🧩|Step Title|Step description paragraph|/tmp/guide-maker/02-step.md" \
  --source "official|Tool documentation|https://example.com/docs" \
  --source "institutional|University lecture on X|https://example.edu/talk"
```

Source types: `official` (docs, changelogs, repos, the tool's own site), `institutional` (a university lecture, a course published by the vendor, a talk by a named-role engineer), `blog`, `pdf`. `youtube` and other creator-channel types are refused unless `sources.cite_creator_videos` is true. See `references/research/sources-policy.md`.

4. Share the in-app Notion URL with the user. **Publishing the page to the web is a manual step the user does in the Notion UI.** The pipeline never does it. Until they do, the public URL in the DMs is a 404; check with `md_to_notion.py public-url --page-id ID --check`.

## Cover generation (required)

After publishing the hub page, generate a cover and set it as the page cover. **This is not an optional polish step** (`workflow.cover_required: true`). The pipeline order is content, publish hub, **cover**, post graphic, Content Board card. Do not report "ready for review" before the cover exists on the hub page.

`banner_generator.py` has three subcommands:

| Subcommand | What it does | Needs |
|---|---|---|
| `simple` | Pillow render with brand colors from config, bundled Inter font | nothing |
| `ai` | KieAI generation from a prompt and reference images, cropped to 1500x600 | `kieai_api_key` |
| `upload` | Upload an existing PNG as a page cover | nothing |

```bash
# Free cover
python3 {SKILL_DIR}/scripts/banner_generator.py simple \
  --title "Short Guide Title" \
  --subtitle "Optional subtitle" \
  --style dark \
  --output /tmp/guides/cover.png \
  --upload-to HUB_PAGE_ID

# AI cover (read references/banner-guide.md first)
python3 {SKILL_DIR}/scripts/banner_generator.py ai \
  --prompt "Your prompt here" \
  --ref-image "STYLE_REF_URL" \
  --ref-image "LOGO_URL_1" \
  --ref-image "LOGO_URL_2" \
  --output /tmp/guides/cover.png \
  --upload-to HUB_PAGE_ID

# Upload only
python3 {SKILL_DIR}/scripts/banner_generator.py upload --file /tmp/guides/cover.png --page-id HUB_PAGE_ID
```

`--style` accepts `dark`, `gradient` or `accent`. `--upload-to` generates and sets the cover in one step. If AI generation fails, the script falls back to a `simple` cover automatically. The output directory is created if it does not exist.

Pass `--keyword KEYWORD` (or set `GUIDE_MAKER_KEYWORD`) and the script refuses a `--title` equal to the keyword. The cover never carries the keyword; that is the post graphic's job. `--allow-keyword` overrides, for the rare case where the guide's real title is one word.

**Process for `ai`:**
1. Read the agent's banner recommendation from Phase 2 output (tools, style)
2. **Check for style reference:** If this is a sequel or same-series guide, find the previous cover and pass it as a `--ref-image`
3. **Research logos (MANDATORY):** For every tool on the cover, web search for the real logo PNG. Without `--ref-image`, the model invents fake logos.
4. Craft the prompt using the templates in `references/banner-guide.md`

**Reference image rules:**
- PNG only (SVGs cause `invalid_image_format` errors)
- Direct URL to the image file (not a landing page)
- Publicly accessible (the API fetches server-side)
- Up to 5 reference images per generation
- Style references (previous covers) count toward the 5 image limit

## Screenshots

When source material contains diagrams, charts, or visual workflows, capture and embed them.

**Process:**
1. Navigate to the source page using a browser automation tool
2. Discover image/visual elements using CSS selectors
3. Identify which visuals add real value (skip icons, avatars, decorative images)
4. Use element-level screenshots for tight crops. Never full-page screenshots.
5. Save to `/tmp/screenshots/` with descriptive names
6. Upload to the relevant Notion subpage using the file upload API

**When to skip:** Text-only source, conceptual guide, user hasn't asked and visuals wouldn't add much.
**When mandatory:** User asks, source has architecture diagrams/data viz, guide covers a tool with a visual interface.
