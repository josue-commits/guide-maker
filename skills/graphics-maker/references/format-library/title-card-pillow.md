---
name: title-card-pillow
local_path: (rendered by scripts/graphics_generate.py card, no reference image)
public_url:
tags: [keyword-cta, dark, light, stats, title, zero-cost]
density: low
cost: none
status: active
created: 2026-09-02
---

# Title Card (Pillow)

The one format that ships with the skill. Rendered entirely by Pillow, so it
needs no image API, costs nothing, and cannot misspell anything. It is the
default for every guide type and the fallback when a generated format drifts.

## What you see

Square canvas, 2048x2048. Solid background in `brand.colors.dark` (or
`light` with `--bg light`). Top left: the title in the bold brand font, up to
three lines, auto-sized to fit. Under it the subtitle in the regular face at
about 35 percent contrast. Bottom of the art area: an optional row of up to
four stats, each a large number over a small label, separated by thin vertical
rules with a hairline above the row. Sealing the bottom edge: the CTA bar,
full width, 11 percent of the height, in the accent color on dark art or the
dark color on light art, with the canonical string centered.

No illustration, no icons, no logo unless `brand.logo.on_post_graphic` is on.
The bar is the single accent element.

## When to use

- Any guide whose hook is a short title plus one to four numbers (kits, template packs, workflow bundles)
- No image provider configured, or the budget for this post is zero
- A generated format drifted twice and you need the graphic now
- The keyword is long (10 to 12 letters) and a model-drawn bar would be risky

## When not to use

- The post's whole appeal is visual (a product UI, a diagram, a before/after code diff). Add a format for that and use two-pass.
- You have shipped this card the last three posts in a row. Rotate: the shape is recognizable.

## Content slots

- `[TITLE]`: 2 to 8 words. Auto-shrinks; three lines maximum. Must not equal the keyword.
- `[SUBTITLE]`: 0 to 10 words, optional.
- `[STAT_N]`: up to four `"NUMBER|label"` pairs. Number 1 to 8 characters, label 1 to 3 words.
- `[KEYWORD]`: 3 to 12 uppercase letters, CTA bar only.
- `--bg`: `dark` (default) or `light`.

## Generation

```bash
python3 $SKILL_DIR/scripts/graphics_generate.py card \
  --title "[TITLE]" --subtitle "[SUBTITLE]" \
  --stat "[STAT_1_NUMBER]|[STAT_1_LABEL]" --stat "[STAT_2_NUMBER]|[STAT_2_LABEL]" \
  --keyword [KEYWORD] --bg dark \
  --output /abs/work/[slug]-post.png
```

No scene pass, no text pass. `finalize` runs inside the command: bar, optional
logo, C2PA strip (harmless on a Pillow file, kept for a uniform pipeline).
The command prints the rendered CTA string on its own line; read it against
the keyword in your DM tool.

## Example

- TITLE: "Automate your CRM follow-ups"
- SUBTITLE: "5 workflows"
- STAT_1: "3" / "tools"
- STAT_2: "20 min" / "setup"
- KEYWORD: FLOWS
- BG: dark

## Notes

- Fonts: `brand.fonts.bold` and `regular` if set, else the bundled Inter next to guide-maker, else a platform sans (Arial Bold on macOS and Windows, DejaVu Sans Bold on Linux), else Pillow's built-in face. Set your own for a consistent look across machines.
- Auto contrast for the bar samples the bottom 15 percent of the art. On this card that area is the solid background, so dark art gets the `accent_1` band and light art gets the `dark` band. Override with `graphics.cta_bar.bg` / `fg`.
- A title that equals the keyword is refused. The bar carries the keyword; the title says what the guide is.
- `--size` changes the canvas (default 2048). Keep it square; LinkedIn crops other ratios in the feed.
