# The two-pass pipeline

Why the generated path splits into a scene pass and a text pass, how to write
each prompt, and what to do when the second pass drifts.

## The problem it solves

Image models render layout well and text badly in the same call. Ask for a
dashboard with six labels and a headline and you get a good dashboard with
two misspelled labels and a headline that merges into the card below it.
Regenerating the whole thing to fix one label costs the layout you liked.

Splitting the work fixes both:

1. **Scene pass.** The model renders the composition with no literal text.
   Two variants, cheap, and you pick the one whose layout holds.
2. **Text pass.** An image-to-image edit adds only the text onto the winning
   scene. Short strings, quoted exactly, one instruction: change nothing else.

The CTA bar is the third piece and, by default, it is not drawn by a model at
all. `finalize` composites it with Pillow from real glyphs. See `cta-bar.md`.

## Commands

```bash
# Pass A
python3 $SKILL_DIR/scripts/graphics_generate.py scene \
  --prompt "..." --ref-image /abs/refs/layout.png \
  --output-prefix /abs/work/slug --variants 2

# Pass B
python3 $SKILL_DIR/scripts/graphics_generate.py text \
  --scene /abs/work/slug-v1.png --prompt "..." \
  --fallback-prompt "..." --keyword FLOWS --output /abs/work/slug-post.png
```

`--dry-run` prints the final prompt after the generator's rewrites, which is
the fastest way to see what the band instruction or the injected CTA string
looks like before paying.

## Writing the scene prompt

- Describe the composition, palette (exact hex codes), materials and card
  shapes. Name every zone that will later hold text and say it is empty.
- End with: "No text anywhere in the image. This is a blank template that
  will have text added in a later step."
- With `renderer: pillow` the generator appends a sentence reserving the
  bottom band. Do not describe a footer bar yourself; it would compete.
- With `renderer: model` describe the bar shape (full-width band at the
  bottom edge, empty) so Pass B has a place to write.
- If you pass a reference image, say what to keep from it (layout, spacing)
  and list what to drop (author name, avatar, wordmark, icon row). Name each
  element. Generic "no branding" is ignored by most models.
- Vary at least one non-text component from the reference (stat grid 2x2
  instead of 1x4, emblem position, footer treatment) so the output reads as
  your design rather than a text swap.
- Omit icon-placeholder rows unless you inject real icons. Empty circles
  read as junk.

## Writing the text pass prompt

- First line: "Add text to this image. Change nothing else. Keep the exact
  background, card shapes, colors and layout as given."
- Then one instruction per zone, in reading order, each string in single
  quotes: `In the top card write 'Cold Outreach Kit' as the headline.`
- Keep each string short. Under six words per zone renders reliably; a
  full sentence usually does not.
- Do not mention the keyword or the CTA when `renderer: pillow`. With
  `renderer: model`, write `[KEYWORD]` where the keyword goes and the
  generator substitutes it and appends the canonical string if missing.
- End with your typography line from `brand.typography_prompt` in config
  (font family, tracking, "never touching or overlapping").
- `--fallback-prompt` is the combined scene+text prompt used only if the
  edit fails. Write it as the single-shot version of the two prompts above.

## Reading the result

Before finalize does anything, open the text pass output and check:

- Layout, colors and card positions match the winning scene (no drift)
- Every string is spelled as you typed it
- Nothing new appeared (a second badge, a stray icon row, a caption)
- The reserved bottom band is still empty (pillow) or the bar carries the
  canonical string exactly (model)

## When Pass B drifts

Reference-conditioned editing is not masked inpainting. Some models redraw
regions they were told to leave alone. In order of cost:

1. Re-run `text` with a tighter "change nothing else outside these zones"
   and shorter strings. One retry.
2. `tweak` the drifted output with a delta-only instruction naming the one
   region to fix.
3. `single` with the fallback prompt: one call, scene and text together.
4. `card`: Pillow, no drift possible, zero cost. For a title-and-stats
   guide this is often the better graphic anyway.

Note on the format card which step rescued it. If a format needs step 3 or 4
every week, retire its two-pass templates and mark it single-shot.

## Thinking mode

`--thinking-high` is passed through to providers that support a reasoning
mode (KieAI's nano-banana family). Use it for dense grids, multi-card
dashboards and anything with more than four aligned regions. It costs more
and takes longer; leave it off for hero layouts.

## Cost

Two scene variants plus one text pass is the default spend, roughly $0.12 to
$0.20 depending on provider and resolution. `--estimate` on each command
prints the number without calling anything. The first run of a new format
usually takes two or three text passes while the prompt settles; budget for
that once, then the card stabilizes.
