---
name: {slug}
local_path: references/format-library/{slug}.png
public_url: {public_url}
tags: [keyword-cta]
density: unknown
cost: two-pass
status: pending-review
created: {today}
---

# {title}

<!-- Fill this card from THIS image only. Open references/format-library/{slug}.png,
     describe what is actually there, then write the sections. Do not write from
     memory of a batch of images. -->

## What you see

<!-- Background, layout, hero element, supporting zones, cards, pills, cursor,
     icons. Be specific: positions, proportions, colors as hex. -->

## When to use

<!-- 3 to 5 bullets. Which guide type (Technical Tutorial, Strategic Framework,
     Comparison / Persuasion, Use-case Stack)? What content shape fits? -->

## When not to use

<!-- 2 to 4 bullets. Which guide shapes fail in this format? -->

## Content slots

<!-- Every variable piece of text or visual, with a word-count range. -->

- `[TITLE]`: 2 to 5 words
- `[SUBTITLE]`: 3 to 8 words
- `[KEYWORD]`: 3 to 12 uppercase letters, CTA bar only

## Generation

### Scene prompt template (Pass A, no literal text)

<!-- Describe the composition with exact hex colors. Name each text zone and say
     it is empty. Name what to drop from the reference (author name, avatar,
     wordmark, icon row). End with the no-text line. Do NOT describe a footer bar:
     with renderer pillow the generator reserves the band for you; with renderer
     model describe an empty full-width band at the bottom edge instead. -->

```
Recreate the composition and proportions of the reference image with every
text zone left blank. Keep ... Drop ...

No text anywhere in the image. This is a blank template that will have text
added in a later step.
```

**Reference images to pass, in order:**
1. `{public_url}` or the local path

**Params:** `--variants 2`, resolution 2K, aspect 1:1, `--thinking-high` if the layout has more than four aligned regions

### Text pass prompt template (Pass B, reference = the winning scene)

<!-- One instruction per zone, strings in single quotes, short. Do not mention
     the CTA under renderer pillow. Under renderer model write [KEYWORD] where the
     keyword goes. End with your brand.typography_prompt line. -->

```
Add text to this image. Change nothing else. Keep the exact background, card
shapes, colors and layout as given.

In the ... write '[TITLE]' ...
Below it write '[SUBTITLE]' ...

Do not redraw or recolor anything outside these text zones.
[brand.typography_prompt]
```

**Params:** resolution 2K, aspect 1:1

### Fallback

<!-- The single-shot prompt: scene and text templates merged, every blank
     instruction replaced with the real content. Passed as --fallback-prompt. -->

## Example

<!-- One worked example with every slot filled. Invented product, invented numbers. -->

## Notes

<!-- What drifted, which negative prompt fixed it, which step of the drift ladder
     rescued the last run. Color-bleed warnings. Whether icons or mascots stand
     for real platforms and how you source them. -->
