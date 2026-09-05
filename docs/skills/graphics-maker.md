# graphics-maker

## What it does

`graphics-maker` produces the one image that goes with a lead-magnet post: the graphic that carries the keyword in a full-width CTA bar across its bottom edge. It has a free path (a Pillow title card: title, subtitle, up to four stats, the bar) and a paid path (a scene pass and a text pass through an image provider), and every path ends the same way: the bar composited, an optional logo, Content Credentials stripped so LinkedIn does not badge the image.

The CTA bar is typeset locally, never generated. With the default renderer the keyword is real glyphs from a real font, so it cannot come out as `ENGNE`; the model, when one is used, is told to leave the bottom band empty. The bar is a release gate, not decoration, because the copy is forbidden from carrying the keyword and there is no second carrier.

## When to reach for it

Type `/graphics-maker`, or the agent reaches for it when you say "make a graphic for this post", "generate a post image", "create the visual for the guide", or when `make-guide` reaches step 3c.

| Your situation | Path |
|---|---|
| No provider key, or a hook that is a number or a short title | `card` (Pillow, free, under a minute) |
| The format calls for illustration, a mock UI, a terminal, a diagram, and you have a key and a format card | `scene` then `text` (two passes) |
| A format built around your own assets (a product screenshot, a rights-cleared photo) | `single`, with the assets as references |
| A finished graphic that needs one change | `tweak` |
| A graphic made elsewhere that needs the bar and the strip | `finalize` |
| The Notion hub cover | Not this skill. The cover never carries the keyword; `make-guide`'s `banner_generator.py` makes it |

## Prerequisites

| It needs | Notes |
|---|---|
| From `config.yaml` | `brand` (colors, fonts, logo), `graphics` (provider, models, aspect ratio, `cta_bar`, `strip_c2pa`, rotation window, negative prompt, usage log), `providers.kieai` or `providers.openai` |
| Pillow | Always. `card` needs nothing else |
| A provider key | `KIEAI_API_KEY` or `OPENAI_API_KEY`, only for `scene`, `text`, `single`, `tweak`; `pip install -r requirements-optional.txt` for OpenAI |
| Format cards | The shipped library holds one (`title-card-pillow`); yours go in `.guide-maker/formats/`, written by `ingest_reference.py` |

Setup is a soft dependency: without it `card` renders on the shipped brand colors and the bundled Inter.

## Two passes and one bar

Two words: **two-pass**, and **bar**.

Image models draw text badly and drift when asked to draw a scene and its labels at once. So the scene pass produces two variants with no text at all, you pick one, and the text pass adds the title and labels while being told to change nothing else. The bar is not part of either pass: `cta_bar.py` paints it after, from the canonical string (`COMMENT "KEYWORD" TO GET IT FOR FREE`, or the compact form), samples the bottom of the art for contrast, and prints the exact string it rendered so you can read it against the image.

The release gate the skill holds, and you confirm at feed scale: the bar is present, full width, at the bottom edge with nothing below it; the keyword is spelled right and legible zoomed out; it matches the Content Board card and the DM tool exactly; no third-party wordmark or headshot came over from a reference; the file has no Content Credentials. A NO on any line and the graphic does not ship, because there is no fallback.

Costs are printed before any call (`--estimate`): the card is free, a full two-pass run is roughly fifteen cents, and a new format costs under a dollar to dial in.

## Common questions

**The text in the generated graphic is fuzzy or misspelled.**

That is why the two-pass split and the local bar exist. Shorten the text, quote each string exactly in the prompt, or fall back to `card`. The keyword itself cannot misspell while `graphics.cta_bar.renderer` is `pillow`.

**The text pass changed the scene.**

Reference-conditioned editing is not masked inpainting. Tighten "change nothing outside the text zones" in the prompt; if a format keeps drifting, use `single` for it.

**LinkedIn still badges the image as AI-generated.**

`finalize` strips C2PA by default. If you passed `--no-strip`, do not. If the badge persists on a stripped file, `strip_credentials.py --scan <file>` shows what survived; open an issue with the output.

**A stranger's logo, headshot or app icons appeared in the scene.**

The reference carried them. Name each element in `graphics.negative_prompt_extra` ("no author name, no avatar, no app icon row"); a generic "no branding" is ignored. Only ingest references you made or have rights to.

**`cta_bar.py` refuses my keyword.**

Keywords are one word, three to twelve capitals, derived from the guide name: `ENGINE`, not `Lead-Engine`.

**Where do my format cards and the usage log live now?**

In v2 both were written inside the skill folder. In v3 `ingest_reference.py` writes cards to `.guide-maker/formats/` and the rotation log goes to `.guide-maker/state/format-usage-log.jsonl` (or wherever `graphics.usage_log` points), because the skill folder is replaced on update.

## It's working if

- Every command prints the exact CTA string it rendered on its own line.
- The bar spans the full width at the bottom edge, and the keyword is readable with the image zoomed out to feed size.
- LinkedIn's upload preview shows no AI-content badge on the file.
- After `log`, nothing new appears in the skill folder; the log line landed under `.guide-maker/state/`.

## Where it fits

`graphics-maker` is step 3c of the chain and a standalone for any old post that needs its image. [dm-automation](./dm-automation.md) is its closest neighbour, because the keyword in the bar and the keyword on the automation have to match or nothing fires; [make-guide](./make-guide.md) supplies the title, subtitle, stats and keyword, and owns the other image asset, the cover, which never carries the keyword. When you are unsure which step you are on, [ask-guide-maker](./ask-guide-maker.md) routes you.
