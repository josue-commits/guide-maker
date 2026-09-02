# Cover Generation Guide

How to generate the Notion hub page cover for a guide. This is **one of two image assets** and they are not interchangeable:

| Asset | Where it goes | Carries the keyword? | Script |
|-------|---------------|----------------------|--------|
| **Cover** (this file) | Notion hub page cover, 1500x600 | **Never** | `scripts/banner_generator.py` |
| **Post graphic** | The LinkedIn post, uploaded to the Content Board `Graphic` property | **Always**, in a full-width CTA band | sibling skill `graphics-maker` |

The cover is a title card for the page. The post graphic is the only place the keyword exists. Putting the keyword on the cover does nothing for the DM tool and muddies the one signal the reader is supposed to act on. `banner_generator.py` refuses a `--title` equal to the keyword unless you pass `--allow-keyword`.

Three ways to make a cover:

- `simple`: Pillow render with brand colors and the bundled Inter font. Free, always works, the default (`cover.mode: simple`).
- `ai`: KieAI generation from a prompt plus reference images. $0.03 per run, needs a key. The rest of this file is about doing this well.
- `upload`: a PNG you already have.

**The single most important rule for `ai`: every logo and visual element on the cover must come from a real reference image passed via `--ref-image`.** Without references the model invents logos that look close but wrong. With references it reproduces them.

---

## Reference Images: The Core Mechanism

`--ref-image` is how you control what appears on the banner. KieAI uses these images as visual input alongside your text prompt. This serves two purposes:

1. **Logo accuracy.** Pass the real PNG of a tool's logo and KieAI renders it faithfully. Skip the reference and it invents something that looks wrong.
2. **Style consistency.** Pass a previous banner that the user liked and KieAI matches the visual style (font treatment, composition, spacing, color palette).

### How reference images work

- Up to 5 PNG URLs per generation via the `image_input` parameter
- KieAI fetches them server-side, so they must be publicly accessible direct links to PNG files
- SVGs cause `invalid_image_format` errors. PNG only.
- The prompt tells KieAI what to do with the references ("use the provided logo on the left", "match the style of the reference banner")

### What counts as a reference image

| Type | When to use | How to find |
|------|-------------|-------------|
| **Tool logo** | Every banner that features a tool | Web search: `"[tool name] logo PNG transparent"` |
| **Style reference** | When matching a previous banner's look | Use the Notion page cover URL from the previous guide, or a saved `/tmp/` file URL |
| **Brand mark** | When the tool uses a symbol (e.g., Claude's asterisk) | Search for the specific mark: `"Claude AI asterisk logo PNG"` |

### Finding logo URLs (MANDATORY for every tool)

For each tool mentioned in the guide:
1. **Web search** for the tool's official logo: `"[tool name] logo PNG transparent"`
2. **Verify** the URL points directly to a PNG file (not a landing page, not an SVG)
3. **Test** that the URL is publicly accessible (no auth walls)
4. **Never skip a tool.** If the first search fails, try: `"[tool name] icon PNG"`, `"[tool name] brand assets"`, `"[tool name] press kit PNG"`

Good sources for logos:
- `uxwing.com` — free PNGs, 512x512, transparent backgrounds
- `freepnglogo.com` — PNG with transparent backgrounds
- GitHub repos — `raw.githubusercontent.com` links (PNG files only)
- Official brand/press pages — downloadable PNG assets

### Using a previous banner as style reference

When creating a sequel guide or maintaining visual consistency:

1. Find the previous guide's hub page ID
2. Retrieve the page cover URL via Notion API, or use the saved banner file if available
3. Pass it as the first `--ref-image` alongside the tool logos
4. Add to the prompt: "Match the visual style of the reference banner image (font treatment, layout, color palette)"

This is how you get visual consistency across related guides without manually describing every style detail.

---

## Style Rules

Every banner follows the same visual language:

- **White background.** Never dark backgrounds, gradients, or heavy brand colors.
- **Modern geometric sans-serif font** (Montserrat/Poppins style). Bold weight, black text. No serif fonts, no 3D/pixel effects, no retro metallic styling.
- **Short punchy title** as the main visual focus, centered.
- **Tool logos in a row** below the title, slightly faded (~40% opacity) as a subtle preview. Tight vertical spacing between text and logos.
- **Minimal composition.** Lots of white space. Startup aesthetic. Don't crowd the banner.
- **No heavy branding.** The banner is about the guide's topic, not about your company. Use brand colors sparingly or reference them from config.yaml if needed.

**Exception:** Single-tool technical guides (e.g., Claude Code guides) can use a more stylized approach with the tool's logo prominently featured. But the default for multi-tool guides, sales resources, and frameworks is always the clean modern style above.

---

## The Workflow

### Step 1: Identify What Goes on the Banner

**Single-tool guide** (e.g., "Claude Code Skills", "Claude Code Remote Control"):
- The tool's logo on the left
- The guide's short title on the right in styled text (never the keyword)

**Multi-tool guide** (e.g., "Top 5 Vibe Coding Platforms"):
- All tool logos in a row
- The guide title as text above or below the logos

**Non-tool guide** (e.g., strategic framework, sales resource):
- Relevant conceptual imagery or just styled title text
- Keep it simple, these don't need logos

### Step 2: Check for Style References

Before searching for logos, check if there's a previous banner to match:

- **Sequel guide** (v1 -> v2, same topic new angle): Find the previous guide's banner and use it as a style reference
- **Same series** (all guides in one topic area): Use the most recent banner from the series
- **User provided a reference**: Always use it as the first `--ref-image`
- **No reference exists**: Skip this step, the style rules and prompt templates are enough

### Step 3: Find Logo URLs (MANDATORY)

**Every banner that mentions tools MUST include their real logos as reference images.** This is the difference between a professional banner and one with fake AI-generated logos.

For each tool mentioned in the guide:
1. **Web search** for the tool's official logo: `"[tool name] logo PNG transparent"`
2. **Verify** the URL is a direct link to a PNG file (not a landing page)
3. **Confirm** it's publicly accessible (KieAI fetches server-side)
4. **PNG format only.** SVGs cause `invalid_image_format` errors.

**If you cannot find a PNG logo for a tool, do NOT skip it.** Try alternative search queries: `"[tool name] icon PNG"`, `"[tool name] brand assets"`, `"[tool name] press kit PNG"`.

### Step 4: Craft the Prompt

Use these tested prompt templates:

**Default banner (multi-tool or general guide, use this most of the time):**
```
White background banner. Large centered text reading '[SHORT TITLE]' in a modern geometric sans-serif font like Montserrat or Poppins, bold weight, black color. Directly below the text with only a small gap, a row of [N] small tool logos slightly faded at about 40% opacity. The text and logos should be grouped together vertically in the center, close to each other with minimal spacing between them. Clean, modern, startup aesthetic.
```

**Topic-only banner (no logos, for frameworks or abstract topics):**
```
White background banner. Large centered text reading '[SHORT TITLE]' in a modern geometric sans-serif font like Montserrat or Poppins, bold weight, black color. Clean, modern, startup aesthetic. Generous white space around everything.
```

**Single-tool banner (for dedicated tool guides):**
```
White background banner. The provided [TOOL] logo on the left side, clearly visible and accurately reproduced from the reference image. On the right side, the text '[SHORT TITLE]' in a stylized bold font. Clean layout with plenty of white space.
```

> ⚠️ **The cover never carries the keyword.** This template used to say `'[KEYWORD]'` and that is wrong. The keyword lives in exactly one place, the LinkedIn post graphic's CTA band, built by the `graphics-maker` sibling. Use the guide's short title here. A keyword on the Notion cover does nothing for the DM tool and muddies the one signal the reader is supposed to act on.

**Multi-logo rows: name each logo explicitly and forbid repeats.** With three or more references the model will silently drop one logo and duplicate another, and sometimes convert the row to monochrome. The prompt shape that fixes it:

```
...a row of exactly 3 different small tool logos in their original brand colors, evenly
spaced, each one accurately reproduced from a different reference image: first the
[COLOR] [TOOL A] icon, second the [COLOR] [TOOL B] icon, third the [COLOR] [TOOL C] icon.
Do not repeat any logo. Do not convert the logos to black and white, keep their real colors.
```

Name the logo, name its colour, name its position. Then say "do not repeat" and "keep their real colors" out loud. **Always look at the output before uploading it.** Nothing in the tool's output signals a dropped logo.

**Style-matched banner (when using a previous banner as reference):**
```
White background banner matching the visual style of the reference banner image (same font treatment, layout composition, and color palette). [TOOL] logo on the left, accurately reproduced from the reference image. Text reading '[TITLE]' on the right in the same font style as the reference. Clean layout, same spacing and proportions.
```

### Step 5: Generate

```bash
# Single tool with logo reference
python3 scripts/banner_generator.py ai \
  --prompt "YOUR PROMPT" \
  --ref-image "LOGO_URL" \
  --output /tmp/banner.png \
  --upload-to HUB_PAGE_ID

# Multiple tools with logo references
python3 scripts/banner_generator.py ai \
  --prompt "YOUR PROMPT" \
  --ref-image "LOGO_URL_1" \
  --ref-image "LOGO_URL_2" \
  --ref-image "LOGO_URL_3" \
  --output /tmp/banner.png \
  --upload-to HUB_PAGE_ID

# Style-matched with previous banner + new logo
python3 scripts/banner_generator.py ai \
  --prompt "YOUR PROMPT" \
  --ref-image "PREVIOUS_BANNER_URL" \
  --ref-image "TOOL_LOGO_URL" \
  --output /tmp/banner.png \
  --upload-to HUB_PAGE_ID
```

The `--upload-to` flag generates the image and uploads it as the Notion page cover in one step. If AI generation fails, it automatically falls back to a simple Pillow banner.

---

## Technical Details

- **Model:** nano-banana-2 via KieAI Jobs API (`POST https://api.kie.ai/api/v1/jobs/createTask`)
- **Cost:** $0.03 per generation
- **Aspect ratio:** `3:2` (landscape)
- **Output:** Cropped and resized to 1500x600px (Notion cover optimal size)
- **Reference images:** Up to 5 PNG URLs via `image_input` parameter
- **Generation time:** ~30-35 seconds
- **API key:** `KIEAI_API_KEY`, then `~/.config/kieai/api_key`, then `providers.kieai.api_key` in the config

---

## Common Pitfalls

1. **SVG reference images fail.** Always use PNG. KieAI returns `invalid_image_format` for SVGs.
2. **Don't let the AI invent logos.** Without a reference image, it will generate something that looks close but wrong. Always pass the real logo as `--ref-image`.
3. **Don't skip the logo search.** "I'll just describe the logo in the prompt" does not work. The AI cannot reproduce a specific brand's logo from a text description alone. You need the actual image as a reference.
4. **Keep prompts specific about layout.** "Left side" and "right side" placement instructions work well. Without them, the AI puts things randomly.
5. **Use style references for sequels.** If this guide is a follow-up to a previous one, find the old banner and pass it as `--ref-image`. This maintains visual continuity.
6. **One generation is usually enough.** At $0.03 it's fine to regenerate if the first result isn't great, but the prompts above are tested and consistent.

---

## Checklist Before Generating

Run through this before every banner generation:

- [ ] Did I identify every tool/brand that should appear on the banner?
- [ ] Did I web search for and find a real PNG logo URL for each one?
- [ ] Did I verify each URL is a direct PNG link (not a landing page or SVG)?
- [ ] Is there a previous banner I should match in style? If yes, did I add it as `--ref-image`?
- [ ] Does my prompt explicitly say "reproduced from the reference image" for logos?
- [ ] Am I passing all logos and style references via `--ref-image`?

If any answer is "no", fix it before generating.

---

## Decision Matrix

| Guide Type | Banner Approach | Logos Needed | Style Reference |
|-----------|----------------|--------------|-----------------|
| Multi-tool guide or sales resource | Default: modern font + faded logos row | 3-5 logos | Previous banner if same series |
| Single-tool technical tutorial | Single-tool: logo prominent + short title text | 1 logo | Previous banner if sequel |
| Strategic framework (no specific tools) | Topic-only: modern font, no logos | None | None |
| User explicitly requests style | Follow user direction | Varies | Whatever user provides |
