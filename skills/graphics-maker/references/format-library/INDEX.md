# Format library

The catalog of graphic formats. Read this before generating: it tells you
which format fits the guide, and which one to skip this week.

The library ships with one format, the Pillow title card. It needs no image
API and it cannot misspell the keyword. Add your own formats from your own
past graphics with `scripts/ingest_reference.py`; the schema is in
`_TEMPLATE.md`.

## Before picking: check rotation

```bash
python3 $SKILL_DIR/scripts/graphics_generate.py rotation
```

Do not repeat a format used inside `graphics.format_rotation_days` (default 7)
if another format fits. The same shape twice in a week, even with different
words, reads as a template in the feed.

## Decision tree by guide type

guide-maker classifies every guide into one of four types
(`skills/guide-maker/references/guides/guide-types.md`). Start there, then
narrow by the shape of the content. CTA presence is not a criterion; every
format carries the bar.

### Technical Tutorial

- Ships a countable kit (X templates, Y prompts, N agents): `title-card-pillow` with 2 to 4 stats
- Deliverable is a folder or file structure: a file-tree format (add your own)
- Centers on a before/after code or config change: a code-diff format (add your own)
- Single tool with a real UI worth showing: a screenshot-hero format, `single` with your own screenshot as the reference
- Anything else: `title-card-pillow`

### Strategic Framework

- Exactly 3 to 5 named phases, pillars or principles: `title-card-pillow` with one stat per pillar, or a grid format you add
- Big resource list where scale is the hook (20+ items): a dense numbered-list format (add your own); until then `title-card-pillow` with the count as the first stat
- Anything else: `title-card-pillow`

### Comparison / Persuasion

- Ranked list of 6 to 12 options: a ranked-list format (add your own)
- "N options, here is the one": `title-card-pillow`, title names the winner, subtitle names the field
- Authority argument citing named people: only with rights-cleared photos you own, via `single`. Never generate a likeness.

### Use-case Stack

- Several tools chained into one outcome: `title-card-pillow` with a stat per tool, or an icon-chain format you add
- Outcome is a number (time saved, leads booked): `title-card-pillow`, the number is the title

### Nothing matches

`title-card-pillow`. It is the fallback for every type. Rotate away from it
once your library has a second format.

## Catalog

| Slug | Cost | Bg | When to use |
|---|---|---|---|
| [title-card-pillow](title-card-pillow.md) | $0 | dark or light | Title + subtitle + up to 4 stats. Default for every guide type. |
<!-- ingest: new rows go above this line -->

## Adding a format

1. Pick an image you have the rights to: one of your own shipped graphics,
   or a layout you built. Not a screenshot of someone else's post; their
   name, avatar and wordmark ride into your output.
2. `python3 $SKILL_DIR/scripts/ingest_reference.py /abs/path/image.png --slug my-format`
   (add `--upload` only when your provider needs public reference URLs).
3. Open the stub card. Look at that one image and fill every section from
   what you see. One image, then its card, then the next. Cards written from
   memory of several images get cross-assigned.
4. Split the prompt into scene and text pass templates per
   `../two-pass-pipeline.md`. Every card needs a `[KEYWORD]` slot.
5. Generate once, review, record what needed fixing in the card's Notes.
6. Add the slug to the decision tree above.

## Rotation log schema

`format-usage-log.jsonl` in the skill folder (or `graphics.usage_log`), one
JSON object per line, written by `graphics_generate.py log`:

```json
{"date": "2026-07-14", "guide_title": "The Agent Upgrade Kit", "keyword": "AGENTS", "format_slug": "title-card-pillow"}
```

Log the shipped graphic only, never rejected attempts.
