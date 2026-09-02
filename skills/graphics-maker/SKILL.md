---
name: graphics-maker
description: Generate the LinkedIn post graphic for a lead-magnet guide, with the keyword CTA bar composited across the bottom edge and Content Credentials stripped. Use when the user asks to "make a graphic for this post", "generate a post image", "create the visual for the guide", or right after guide-maker publishes a guide and the post needs its image. Zero-cost Pillow card by default; optional two-pass generation through an image provider (KieAI or OpenAI).
---

# graphics-maker

Produces the one image that goes with a lead-magnet post. The image carries the
keyword; the post copy does not. That split is what keeps the post's reach, so
this skill treats the CTA bar as a release gate, not decoration.

Sibling of `guide-maker`. Reads the shared config (`config.yaml` from the
guide-maker skill, or `GUIDE_MAKER_CONFIG`). Runs standalone if guide-maker is
absent; the config loader falls back to `./config.yaml`.

## What you get

| Path | Cost | Needs | Output |
|---|---|---|---|
| `card` | $0 | Pillow only | 2048x2048 title card: title, subtitle, up to 4 stats, CTA bar |
| `scene` + `text` | ~$0.10 to $0.20 | image provider key | Two-pass generated graphic, bar composited locally or drawn by the model |
| `single` | ~$0.05 to $0.12 | image provider key | One-shot generated graphic |
| `tweak` | ~$0.05 | image provider key | Delta edit of any local PNG |

Every path ends in `finalize`: CTA bar, optional logo, C2PA strip.

## Requirements

- Python 3.9+, Pillow, PyYAML (`pip install -r requirements.txt` at the repo root)
- Optional: `graphics.provider: kieai` with `KIEAI_API_KEY`, or `graphics.provider: openai` with `OPENAI_API_KEY` and `pip install -r requirements-optional.txt`
- Fonts: `brand.fonts.bold` / `regular` if set, else the bundled Inter next to guide-maker, else a platform sans, else Pillow's built-in face

## Config keys this skill reads

```yaml
brand:
  colors: {dark: "#1A1A1C", light: "#F7F7F7", accent_1: "#A6CB17", accent_2: "#8033F4"}
  fonts: {bold: "", regular: ""}          # empty = bundled Inter
  logo: {path: "", on_post_graphic: false}
graphics:
  provider: none                          # none | kieai | openai
  scene_model: ""                         # provider default when empty
  text_model: ""
  aspect_ratio: "1:1"
  resolution: "2K"
  cta_bar:
    renderer: pillow                      # pillow | model
    string: primary                       # primary | compact
    height_pct: 0.11
    bg: ""                                # empty = auto contrast
    fg: ""
  strip_c2pa: true
  format_rotation_days: 7
  negative_prompt_extra: ""
  usage_log: ""                           # empty = <skill>/format-usage-log.jsonl
  upload_endpoint: ""                     # empty = catbox.moe (kieai references only)
  logo_corner: top-left
  logo_width_pct: 0.12
  logo_on_dark: ""                        # light logo variant for dark art
```

## Path convention

Every command below uses `$SKILL_DIR`, the absolute path of this folder
(for example `/home/you/.claude/skills/graphics-maker`). Resolve it once and
use absolute paths for every input and output. Work files go in
`workflow.work_dir` from config, or any absolute scratch folder.

## Pipeline

```
0. rotation check   graphics_generate.py rotation
1. format pick      references/format-library/INDEX.md decision tree
2. scene pass       graphics_generate.py scene (2 variants, no text)      [provider]
3. winner           you or the user picks v1 or v2
4. text pass        graphics_generate.py text (title, labels; bar reserved)  [provider]
   or Pillow card   graphics_generate.py card (steps 2 to 4 collapsed, $0)
5. finalize         CTA bar + optional logo + C2PA strip (automatic)
6. log              graphics_generate.py log
```

### When to use `card` versus two-pass

Use `card` when any of these is true: no provider configured, the guide's hook
is a number or a short title (most tutorials and kits), you need the image in
under a minute, or the last two-pass attempt drifted. It is the default and the
only path the smoke test exercises.

Use `scene` + `text` when the format calls for illustration, a mock UI, a
terminal or a diagram, and you have a provider key and a format card with
scene and text templates. Read `references/two-pass-pipeline.md` first.

Use `single` for formats built around real assets passed as references (your
own product screenshot, a rights-cleared photo). Never let a model invent a UI.

### Step 0. Rotation

```bash
python3 $SKILL_DIR/scripts/graphics_generate.py rotation
```

If a format was used inside `graphics.format_rotation_days` and another format
fits, pick the other one.

### Step 1. Format

Walk `references/format-library/INDEX.md` by guide type. State the pick and
the reason before generating. The shipped catalog has one card
(`title-card-pillow`); add your own with `ingest_reference.py`.

### Step 2 to 4a. Pillow card

```bash
python3 $SKILL_DIR/scripts/graphics_generate.py card \
  --title "Automate your CRM follow-ups" --subtitle "5 workflows" \
  --stat "3|tools" --stat "20 min|setup" \
  --keyword FLOWS --bg dark \
  --output /abs/work/flows-post.png
```

Prints the rendered CTA string on its own line. Compare it character by
character with the keyword configured in your DM tool.

### Step 2 to 4b. Two-pass

```bash
python3 $SKILL_DIR/scripts/graphics_generate.py scene \
  --prompt "SCENE PROMPT, no literal text" \
  --ref-image /abs/refs/my-layout.png \
  --output-prefix /abs/work/flows --variants 2 --estimate     # cost only, no call

python3 $SKILL_DIR/scripts/graphics_generate.py scene \
  --prompt "SCENE PROMPT, no literal text" \
  --ref-image /abs/refs/my-layout.png \
  --output-prefix /abs/work/flows --variants 2

python3 $SKILL_DIR/scripts/graphics_generate.py text \
  --scene /abs/work/flows-v1.png \
  --prompt "TEXT PASS PROMPT: what to write where, change nothing else" \
  --fallback-prompt "COMBINED SINGLE-SHOT PROMPT" \
  --keyword FLOWS --output /abs/work/flows-post.png
```

With `cta_bar.renderer: pillow` (default) the prompt is rewritten to leave the
bottom band empty and the bar is composited from real glyphs. With
`renderer: model` the canonical string is injected into the prompt and the
model draws it; `finalize` then prints the expected string for you to read
against the image.

Add `--thinking-high` for dense grids if the provider supports it.
`--dry-run` on any of these prints the exact prompt and references without
calling anything.

### Step 5. Finalize (runs automatically)

Standalone, for a graphic that did not come through this script:

```bash
python3 $SKILL_DIR/scripts/graphics_generate.py finalize \
  --image /abs/work/other.png --keyword FLOWS
```

Order inside finalize: CTA bar, logo (only with `--logo` or
`brand.logo.on_post_graphic: true`), C2PA strip (fails loud if a marker
survives).

### Step 6. Log

```bash
python3 $SKILL_DIR/scripts/graphics_generate.py log \
  --format title-card-pillow --keyword FLOWS --title "Automate your CRM follow-ups"
```

Log only the shipped graphic, not rejected attempts.

### Tweak loop

```bash
python3 $SKILL_DIR/scripts/graphics_generate.py tweak \
  --image /abs/work/flows-post.png --instruction "make the headline 20 percent larger" \
  --keyword FLOWS --output /abs/work/flows-post-v2.png
```

## Release gate

A NO on any line means the graphic does not ship. There is no fallback,
because the copy is forbidden from carrying the keyword.

- [ ] The CTA bar is present, full width, at the bottom edge, nothing below it
- [ ] The keyword is spelled correctly. Read it character by character against the printed string
- [ ] The keyword is legible at feed scale (zoomed out, not at 100 percent)
- [ ] The keyword matches the Content Board entry and the DM tool exactly
- [ ] The wording is one of the two canonical strings in `references/cta-bar.md`
- [ ] No third-party wordmark, name, headshot or app-icon strip carried over from a reference
- [ ] No em dashes, no hashtags in rendered text
- [ ] C2PA stripped (automatic; run `strip_credentials.py` on anything sourced elsewhere)

## Cost table (approximate, check your provider's pricing)

| Operation | KieAI | OpenAI |
|---|---|---|
| `card` | $0 | $0 |
| `scene` x2 | 2 x $0.05 | 2 x $0.04 (medium) |
| `text` | $0.06 | $0.04 |
| `single` | $0.05 | $0.04 |
| `tweak` | $0.06 | $0.04 |
| Two-pass total | ~$0.16 | ~$0.12 |

Budget $0.50 to $0.75 for the first run of a new format while you dial in
its prompts. `--estimate` prints the number before any call.

## Failure modes

| Symptom | Fix |
|---|---|
| Text pass redraws or recolors part of the locked scene | Reference-conditioned edits are not masked inpainting. Tighten "change nothing else outside these text zones". If a format keeps drifting, use `single` or `card` for it. |
| Keyword misspelled by the model | Keep `cta_bar.renderer: pillow`. The bar is then real glyphs and cannot misspell. |
| Model draws something inside the reserved band | Raise `cta_bar.height_pct` slightly, or add "the bottom band is solid and empty" to the negative prompt. The Pillow bar paints over it anyway. |
| Bar color clashes with the art | Set `cta_bar.bg` / `fg`, or pass `--bg` / `--fg` to `cta_bar.py`. Auto mode samples the bottom 15 percent for contrast. |
| A pre-colored badge keeps the wrong color after the text pass | Leave it neutral grey in the scene prompt so the text pass owns the color. |
| Text fuzzy or merged | Shorten the text, quote each string exactly, or fall back to `card`. |
| Grid or card layout uneven | `--thinking-high` where supported; copy spatial wording from the format card verbatim. |
| Colors drifted | Put exact hex codes in the prompt. Models invent shades without them. |
| Someone else's wordmark, name, headshot or icon strip appears | The reference carried it. Name each element in the negative prompt ("no author name, no avatar, no app icon row"). A generic "no branding" is ignored. Only ingest references you made or have rights to. |
| Reference upload fails (412, timeout) | Only KieAI needs public URLs. Host the image yourself and pass the URL, set `graphics.upload_endpoint`, or switch to `single` with URL references. |
| `graphics.provider is none` error | Expected without a key. Use `card`, or configure a provider. |
| `openai` import error | `pip install -r requirements-optional.txt`. The OpenAI adapter is best effort; community testing wanted. |

## Providers

- `none` (default): refuses to generate, points at `card`.
- `kieai`: reference adapter, ported from a production pipeline. Models default to `nano-banana-pro` (scene) and `gpt-image-2-image-to-image` (text, tweak). Fetches references by URL, so local references are uploaded first.
- `openai`: `images.generate` / `images.edit`, reads local files, no upload. Best effort, community-tested wanted. Set `graphics.scene_model` to the image model your account has.

Adding one: copy `scripts/providers/openai.py`, implement `generate` and
`edit`, return a URL or local path, add the name to `KNOWN_PROVIDERS` in
`providers/base.py`.

## Files

```
SKILL.md
references/cta-bar.md                  canonical strings, placement, verification
references/two-pass-pipeline.md        why scene/text split, prompt rules, drift
references/format-library/INDEX.md     decision tree + catalog
references/format-library/_TEMPLATE.md card schema for new formats
references/format-library/title-card-pillow.md
scripts/graphics_generate.py           card | scene | text | single | tweak | finalize | log | rotation
scripts/cta_bar.py                     standalone bar compositor
scripts/strip_credentials.py           C2PA strip, fail-loud scan
scripts/logo_corner.py                 optional logo, off by default
scripts/ingest_reference.py            add a reference image to the library
scripts/_upload.py                     public URL upload (kieai references only)
scripts/_cfg.py                        config shim with standalone fallback
scripts/providers/{base,kieai,openai}.py
format-usage-log.jsonl                 created at runtime, gitignored
```

## Integration

- guide-maker's Phase 3c calls `card` or the two-pass commands with the guide's title, subtitle, stats and keyword, then attaches the PNG to the Content Board card's `Graphic` property.
- The hub cover (guide-maker's `banner_generator.py`) is a different asset and never carries the keyword. Do not reuse one for the other.
- dm-automation reads the same keyword. If the bar and the DM tool disagree, nothing fires.
