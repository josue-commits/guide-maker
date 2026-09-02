# The CTA bar

**Every post graphic carries the keyword. There are no exceptions and there is no fallback.**

With `copy.cta_mode: graphic` (the default in guide-maker v2) the post copy is
forbidden from containing any engagement instruction. LinkedIn suppresses reach
on posts whose copy says "comment X", "like this post" or "repost this". The
keyword lives in exactly one place: the graphic.

That makes this bar the only capture mechanism the post has. A graphic without
it is a post that asks for nothing. The evidence behind the rule is in
guide-maker's `references/strategy/cta-evidence.md`.

---

## The canonical wording

**Primary.** Use this unless the layout physically cannot fit it.

```
COMMENT "[KEYWORD]" TO GET IT FOR FREE
```

All caps, full-width bar, keyword in double quotes. This exact string sits on
the two highest-performing lead-magnet posts in the public record we could
verify, each above 450 comments.

**Compact.** For layouts where the primary string wraps or shrinks below
legibility, typically terminal-style formats that also render a cursor block.

```
Comment "[KEYWORD]" for the guide
```

Do not invent new phrasings. Two sanctioned strings, nothing else.
`cta_bar.py` and `graphics_generate.py finalize` only render these two.

---

## Placement rules

**The bar is a band across the bottom edge of the image. Always. No format is
exempt.** This rule exists because a graphic once shipped with the CTA as a
line of text inside a terminal card, floating mid-image, and read as part of
a screenshot.

- **Bottom edge of the IMAGE, not of a card.** The band touches the bottom
  border of the canvas. It is never a line inside a terminal window, a card,
  a panel or any other container in the artwork. If the format has an inner
  card, the bar goes below and outside it.
- **Full width, edge to edge.** Not a centered chip, not a rounded pill with
  side margins, not a text line with padding around it. A reader scrolling
  the feed sees a distinct strip sealing the bottom of the image.
- **Last element. Nothing below it.** No avatar, no author name, no wordmark,
  no attribution row. An earlier version of this rule allowed "an attribution
  row that already existed in the format", and that is how a reference
  image's third-party branding rode into a finished graphic. Strip whatever
  the reference has down there.
- **High contrast against the art.** Dark band on light formats, accent band
  on dark formats. The Pillow compositor samples the bottom 15 percent of the
  art and picks this automatically; `graphics.cta_bar.bg` / `fg` override it.
- **Accent budget.** The band counts as the format's single accent element.
  Do not also render an accent pill or chip elsewhere in the art.

The reason is mechanical, not aesthetic. A CTA tucked inside a card competes
with the artwork for attention. A band sealing the bottom edge reads as an
instruction.

---

## Two renderers

`graphics.cta_bar.renderer` picks who draws the band.

| | `pillow` (default) | `model` |
|---|---|---|
| Who draws it | `scripts/cta_bar.py`, real font glyphs | the image model, from the prompt |
| Can misspell the keyword | no | yes |
| Cost | $0 | included in the text pass |
| Look | flat band, brand colors, your font | matches the art's rendering |
| Prompt handling | prompt is rewritten to leave the band empty | canonical string is injected into the prompt |

Start with `pillow`. Switch to `model` only if the flat band fights a format
you care about, and then read every keyword character by character.

---

## Choosing the keyword

The keyword is derived from the guide or asset name, never arbitrary. It
should read as a natural shorthand a human would type, not a tracking code.

| Guide | Keyword |
|---|---|
| The Founder-Led Lead Engine | ENGINE |
| 13 Automation Workflows | FLOWS |
| 100x Your Lead Magnet Reach | LEAD |

One word, 3 to 12 uppercase ASCII letters (`[A-Z]{3,12}`, enforced by
`cta_bar.py`). Unique per guide, since it is the tracking key across your
Content Board and your DM tool. Run guide-maker's `keyword_check.py` before
assigning one.

---

## Verification, non-negotiable

**Read the rendered keyword character by character before shipping.** Not
"looks right", actually read it. `cta_bar.py` prints the exact string it drew
on its own line so you can compare.

A misspelled keyword in the image silently breaks the DM trigger. `ENGNE`
instead of `ENGINE` means the auto-DM never fires, every commenter gets
nothing, and the copy cannot save it because the copy no longer mentions the
keyword at all. The post looks fine and captures zero leads.

This is a build failure, not a warning:

- Keyword missing from the image: does not ship
- Keyword misspelled: does not ship
- Keyword illegible at feed scale: does not ship
- Keyword does not match the Content Board and the DM tool: does not ship

Check it at the size LinkedIn actually renders it, not zoomed in.

---

## For format authors

Every card in `format-library/` must define a `[KEYWORD]` content slot and
carry the bar through both passes:

- **Scene prompt (Pass A):** with `renderer: pillow`, the scene leaves the
  bottom band empty (the generator appends this instruction for you). With
  `renderer: model`, the blank template includes the bar shape, empty of
  text. If the scene has no bar, the text pass has nowhere to write and will
  invent a placement.
- **Text pass (Pass B):** with `renderer: model`, writes the canonical string
  into that shape. With `renderer: pillow`, writes nothing there.
- **Tags:** include `keyword-cta`.

"No CTA zone by design" is not a valid stance for a card. It describes a card
that cannot be used.
