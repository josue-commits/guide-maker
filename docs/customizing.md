# Customizing

The skill ships with opinions and empty slots. Fill the slots first; change the opinions when your numbers tell you to.

## The three files that change the voice

| File | What it does | What to put there |
|---|---|---|
| `references/writing/voice.md` | Tells the writer who you are | Who you sell to, how long your sentences run, words you use, words you never use, whether you swear, your analogies |
| `references/linkedin/examples.md` | Voice calibration | 5 to 10 of your real posts. The writer reads them for rhythm and vocabulary, not for structure |
| `references/linkedin/top-performers.md` | Structure calibration | Your 3 to 5 best posts with their numbers, and one line each on why they worked. Empty by default; the shipped synthetic examples are used until you fill it |

The shipped `examples.md` contains three synthetic posts in the v2 structure. Replace them; do not add to them.

## Topics

Channel, subreddit and X account lists live in the `topic-finder` sibling: `<skills>/topic-finder/config/*.json`. Copy an `.example.json` preset, edit, drop the `.example`. Give every YouTube channel a `category` of `tool` or `business`; the two tracks are scored separately.

`excluded_topics` in `config.yaml` takes plain strings or `/regex/`. Competitors, subjects you are done with, anything you never want proposed.

`research.depth_gate` sets the bar a topic must clear. `research.auto_accept_patterns` is for your proven winners. `research.hard_reject` is the list of shapes that never become a guide (news, single-feature drops, opinion).

## Copy

Everything under `copy:` in `config.yaml`:

- `cta_mode: graphic | copy`. Read `strategy.md` before switching.
- `structure: prose | arrow_list`. Prose is the default; arrow lists are fine for pure listicles.
- `words: {min, max, target, reject_below, reject_above}`. Editorial default 180 to 250.
- `hooks:` one per variation. Rename or reorder; the writer prompt explains each.
- `closers:` the value lines the post can end on. Add yours; `lint_copy.py rotation` flags a closer repeated three weeks running.
- `extra_banned_words:` your own additions to the humanizer list. To remove a banned word that is part of your natural vocabulary, edit `references/writing/humanizer.md`.

## Accounts

One account is the default. For a team:

```yaml
accounts:
  - name: "Sarah"
    voice: founder
    dm_destination: community
  - name: "Mike"
    voice: team
    dm_destination: direct
workflow:
  one_card_per: account    # one Content Board card per account instead of per guide
```

Each account gets its own three variations in its voice and its own DM version.

## Community and secondary channel

```yaml
community:
  platform: skool | discord | circle | slack | none
  url: ""            # empty = no callout on the hub page, no community DM versions
  callout_line: ""   # never claim a bigger number than you have
secondary_channel:
  type: youtube | newsletter | podcast | none
  url: ""            # empty = no credit line, no secondary DM version
```

## DM tool

`dm_tool.provider: manual` renders the DM texts and a checklist you follow in whatever tool you use. `leadshark` schedules the post, attaches the graphic and the keyword automation in one call. To add another tool, implement `DMTool` in `skills/dm-automation/scripts/adapters/<name>.py` (five methods, see `base.py`) and set `dm_tool.provider: <name>`.

`dm.merge_tag` is whatever your tool substitutes for the first name. `{{firstName}}` for LeadShark. The linter rejects `{name}` and `[Name]` because they reach the lead as literal text.

## Graphics

`graphics.provider: none` gives you a Pillow title card with the CTA bar, free, always works. `kieai` or `openai` unlock the scene pass (two variants, no text) and the text pass.

The CTA bar is composited locally by default (`graphics.cta_bar.renderer: pillow`), so the keyword is typeset, not generated, and cannot come out as `ENGNE`. Set `model` if you want the bar rendered inside the art by the text pass; then read the keyword character by character before shipping.

Your own visual formats: run `ingest_reference.py` on graphics you admire (a screenshot or a URL). It writes a format card from `references/format-library/_TEMPLATE.md` that you finish by hand: scene prompt with content slots, text pass prompt, negative prompt. The library ships empty except for the Pillow card, on purpose: the cards that worked for one brand are that brand's.

To add an image provider, implement `ImageProvider` in `skills/graphics-maker/scripts/providers/<name>.py`: `generate`, `edit`, `needs_public_ref_urls`, `estimate_cost`. About 40 lines; `kieai.py` is the reference, `openai.py` the smaller example.

## Brand

```yaml
brand:
  colors: {dark, light, accent_1, accent_2}
  fonts: {bold: "", regular: ""}     # absolute .ttf/.otf paths; empty = bundled Inter
  typography_prompt: "..."           # injected into every image prompt
  logo: {path: "", on_post_graphic: false, on_cover: false}
```

## Gates

`workflow.gates: two` (default) stops after the outline and again after the content. `one` stops only after the outline and ships the bundle with defaults. Either way you still pick the graphic scene, verify the keyword, publish to the web and post.

## Hub page layout

`references/guides/hub-page-layout.md` is the order of blocks on every hub page. Edit it once, every future guide follows.
