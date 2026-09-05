# Customizing

The skill ships with opinions and empty slots. Fill the slots first; change the opinions when your numbers tell you to.

Everything you change lives in `.guide-maker/` in your project (or in `~/.config/guide-maker/` if you chose the user-level home). The skill folders are never edited: `npx skills update` replaces them, and anything you had put inside is gone with the update. If you find yourself opening a file under `skills/`, stop and look for the override below.

```
.guide-maker/
  config.yaml            every key, commented
  voice.md               who you are, for the writer
  examples.md            your real posts, for rhythm
  top-performers.md      your best posts with numbers, for structure
  topic-finder/          the source lists the scanners read
  formats/               your own graphic format cards
  state/                 logs the linters read (gitignored)
```

## The three files that change the voice

| Override | Replaces | What to put there |
|---|---|---|
| `.guide-maker/voice.md` | `make-guide/references/writing/voice.md` | Who you sell to, how long your sentences run, words you use, words you never use, whether you swear, your analogies |
| `.guide-maker/examples.md` | `make-guide/references/linkedin/examples.md` | 5 to 10 of your real posts. The writer reads them for rhythm and vocabulary, not for structure |
| `.guide-maker/top-performers.md` | `make-guide/references/linkedin/top-performers.md` | Your 3 to 5 best posts with their numbers, and one line each on why they worked |

An override replaces the shipped file entirely; nothing is merged. Start from the shipped one when you want its shape: `doctor.py --print-paths --json` prints `skill_dir`, and the defaults sit under it at `references/writing/voice.md`, `references/linkedin/examples.md` and `references/linkedin/top-performers.md`. Copy the one you want into `.guide-maker/` under the short name and edit it there.

Or say yes when `/setup-guide-maker` offers to write `voice.md` and `top-performers.md` from three questions. The shipped `examples.md` holds three synthetic posts in the v2 structure; your override should replace them, not add to them.

## Topics

The source lists live in `.guide-maker/topic-finder/`: `youtube-channels.json`, `subreddits.json`, `x-accounts.json` and an optional `topics.json`. Setup copies the examples in; the templates stay in the skill folder as `config/*.example.json`. Give every YouTube channel a `category` of `tool` or `business`; the two tracks are scored separately. Keep the lists scoped: 8 to 15 channels, 8 to 15 subreddits, 5 to 10 X accounts.

In `config.yaml`:

- `excluded_topics` takes plain strings or `/regex/`. Competitors, subjects you are done with, anything you never want proposed.
- `research.depth_gate` sets the bar a topic must clear. `research.auto_accept_patterns` is for your proven winners. `research.hard_reject` lists the shapes that never become a guide (news, single-feature drops, opinion).
- `topic_finder.scan_health` sets the thresholds below which the writer refuses to rank.

## Copy

Everything under `copy:` in `config.yaml`:

- `cta_mode: graphic | copy`. Read [strategy.md](./strategy.md) before switching.
- `structure: prose | arrow_list`. Prose is the default; arrow lists are fine for pure listicles.
- `words: {min, max, target, reject_below, reject_above}`. Editorial default 180 to 250.
- `hooks:` one per variation. Rename or reorder; the writer prompt explains each.
- `closers:` the value lines the post can end on. Add yours; `lint_copy.py rotation` reads `.guide-maker/state/closer-log.jsonl` and flags a closer repeated three weeks running.
- `extra_banned_words:` your own additions to the humanizer list. To remove a banned word that is part of your natural vocabulary, copy the shipped `references/writing/humanizer.md` into your project, edit it, and point `copy.banned_words_file` at the copy.

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

`dm_tool.provider: manual` renders the DM texts and a checklist you follow in whatever tool you use. `leadshark` schedules the post, attaches the graphic and the keyword automation in one call.

`dm.merge_tag` is whatever your tool substitutes for the first name. `{{firstName}}` for LeadShark. The linter rejects `{name}` and `[Name]` because they reach the lead as literal text.

## Graphics

`graphics.provider: none` gives you a Pillow title card with the CTA bar, free, always works. `kieai` or `openai` add the scene pass (two variants, no text) and the text pass.

The CTA bar is composited locally by default (`graphics.cta_bar.renderer: pillow`), so the keyword is typeset, not generated, and cannot come out as `ENGNE`. Set `model` if you want the bar rendered inside the art by the text pass; then read the keyword character by character before shipping.

Your own visual formats: run `ingest_reference.py` on graphics you admire (a screenshot or a URL). It writes a format card into `.guide-maker/formats/` from the shipped `_TEMPLATE.md`, which you finish by hand: scene prompt with content slots, text pass prompt, negative prompt. The shipped library holds one card (the Pillow title card) on purpose: the cards that worked for one brand are that brand's. The rotation log lives at `.guide-maker/state/format-usage-log.jsonl`, or wherever `graphics.usage_log` points.

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

## State

Everything the skills append to at run time goes under `.guide-maker/state/`: the closer log and the format usage log. `paths.state` in `config.yaml` moves that folder. Nothing else about state is configurable, and nothing is ever written under `skills/`.

## Not overridable yet

`references/guides/hub-page-layout.md` (the block order on every hub page), `references/writing/guide-spec.md` and the DM templates are shipped references without a project override. Edit them in a fork if you must, knowing `npx skills update` will overwrite the edit, or open an issue describing the change; a new override is a small addition to the loader's map.

## For tinkerers: providers and adapters

These are code changes inside the skill folders. Under `npx skills` your edit lives until the next `npx skills update`; make it in a fork of the repo and send a pull request if it is generally useful.

**An image provider**: implement `ImageProvider` in `skills/graphics-maker/scripts/providers/<name>.py` (`generate`, `edit`, `needs_public_ref_urls`, `estimate_cost`; about 40 lines), add the name to `KNOWN_PROVIDERS` in `providers/base.py`, and set `graphics.provider: <name>`. `kieai.py` is the reference, `openai.py` the smaller example.

**A DM tool**: implement `DMTool` in `skills/dm-automation/scripts/adapters/<name>.py` (five methods, see `base.py`), register it in `PROVIDERS`, and set `dm_tool.provider: <name>`. Every adapter must honour `--dry-run` by printing the payload and opening no socket.
