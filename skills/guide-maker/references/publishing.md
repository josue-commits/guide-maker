# Publishing to Notion

## Target
Guide Database on your Notion workspace (ID from config.yaml).

**CAUTION:** If this is a shared workspace, always confirm with the team before publishing.

## Publishing Steps

1. Save all markdown files in `/tmp/guides/`
2. Present the complete guide to the user for review
3. After approval, run the hub publisher:

```bash
python3 scripts/publish_guide_hub.py \
  --title "Guide Title Here" \
  --description "One-sentence guide description" \
  --keyword "KEYWORD" \
  --type "Technical Tutorial" \
  --week "YYYY-MM-DD" \
  --icon "🛠️" \
  --step "⚡|Step Title|Step description paragraph|path/to/step1.md" \
  --step "🧩|Step Title|Step description paragraph|path/to/step2.md" \
  --source "YouTube|Video Title|https://youtube.com/watch?v=..." \
  --source "PDF|Document Title|https://example.com/doc.pdf"
```

4. Share the Notion URL with the user

## Banner Generation

After publishing the hub page, generate a banner and set it as the page cover.

**Model:** nano-banana-2 (via KieAI Jobs API, optional)
**Full reference:** `references/banner-guide.md` (prompt templates, logo workflow, style rules)

**Read `references/banner-guide.md` before generating any banner.**

**Process:**
1. Read the agent's banner recommendation from Phase 2 output (tools, keyword, style)
2. **Check for style reference:** If this is a sequel or same-series guide, find the previous banner and use it as a `--ref-image` to match the visual style
3. **Research logos (MANDATORY):** For every tool/brand on the banner, web search for the real logo PNG. Without `--ref-image`, the AI invents fake logos.
4. Craft the prompt using templates from `references/banner-guide.md`
5. Generate and upload:

```bash
python3 scripts/banner_generator.py ai \
  --prompt "Your prompt here" \
  --ref-image "STYLE_REF_URL" \
  --ref-image "LOGO_URL_1" \
  --ref-image "LOGO_URL_2" \
  --output /tmp/banner.png \
  --upload-to HUB_PAGE_ID
```

**Reference image rules:**
- PNG only (SVGs cause `invalid_image_format` errors)
- Direct URL to the image file (not a landing page)
- Publicly accessible (the API fetches server-side)
- Up to 5 reference images per generation
- Style references (previous banners) count toward the 5 image limit

If AI generation fails, the script falls back to a simple Pillow banner automatically.

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
