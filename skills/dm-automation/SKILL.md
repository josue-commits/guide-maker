---
name: dm-automation
description: Turn a finished guide into the DM side of a keyword-comment lead magnet. Renders the DM versions from the guide-maker templates, lints them (merge tag, no hard wrap, public link only, no em dashes), and either writes a paste-ready bundle for whatever DM tool you use (default) or schedules the post with its graphic and keyword automation through an adapter (LeadShark ships as the reference). Use when the user says "set the keyword", "schedule the post", "render the DMs", "check if KEYWORD is taken", "pull the leads", "how did Monday's post do", or when guide-maker reaches step 3e.
---

# dm-automation

Optional sibling of guide-maker. guide-maker produces the guide, the copy, the
graphic and the DM text. This skill takes it from there: the keyword, the DM the
tool sends when someone comments it, and the post going out with both attached.

Set `SKILL_DIR` to the absolute path of this folder first and use it in every
command. Never call the scripts through a relative path.

```bash
SKILL_DIR="/absolute/path/to/skills/dm-automation"
python3 "$SKILL_DIR/scripts/dm_cli.py" --help
```

Requirements: Python 3.9+, PyYAML, Pillow (for `image-fit` only). No other
dependency. Config is the guide-maker `config.yaml`; the CLI finds it through
guide-maker's `_config.py` when the two skills sit side by side, and falls back
to `--config`, `GUIDE_MAKER_CONFIG` or `./config.yaml` when they do not.

## Manual by default, adapter when you have one

`dm_tool.provider` in the config decides what `schedule` and `attach` do.

| provider | what happens | network |
|---|---|---|
| `manual` (default) | writes `<out-dir>/dm-bundle/` with `post.txt`, `dm-*.txt`, the graphic, and a `checklist.md` you follow in your own tool | none, ever |
| `leadshark` | schedules the post, uploads the graphic and attaches the keyword automation in one API call | yes, after `--dry-run` |

Every other command (`render`, `image-fit`, `test`) behaves the same under both.
To add a tool, subclass `scripts/adapters/base.py:DMTool` and register it in
`PROVIDERS`. Read `references/manual-workflow.md` for what the bundle is, and
`references/leadshark-notes.md` for the API specifics.

## The four rules the lint enforces

1. **The merge tag is exactly `{{firstName}}`** (or whatever `dm.merge_tag` says).
   `{name}`, `[Name]`, `{first_name}` reach the lead as literal text. The lint
   fails on any of them.
2. **The guide link must be public.** Notion's copy-link button gives you an
   `app.notion.com` or `notion.so` URL that gates on workspace membership; every
   commenter gets a dead link. Publish the page to the web from the Notion app
   first and use the `<workspace>.notion.site` URL. `render` exits 2 on a
   workspace link, and the checklist prints a `curl` line to confirm the public
   one answers 200. Controlled by `dm.guide_link_must_be_public`.
3. **Never hard-wrap.** One paragraph is one line, blank lines between
   paragraphs, a URL may sit alone on its own line. The DM pane wraps text again
   and a pre-wrapped paragraph reads like a broken paste. `dm.hard_wrap: true`
   turns this off if your tool needs it.
4. **No em dashes** in anything that goes out: DM, variants, replies, post copy,
   automation name. The guard runs on every outgoing payload.

Also enforced: `dm.max_lines` (default 7 non-blank lines), no unfilled `{slot}`
left in a rendered DM, the 2000-character LeadShark limit when that adapter is
selected, and the keyword must not appear in the post copy unless
`copy.cta_mode: copy`.

## Commands

Run `--dry-run` first on anything that would touch an account. It prints the
exact payload and never opens a socket, whichever adapter is configured.

### render: DM text from the templates

Fills `skills/guide-maker/templates/dm-{direct,combined,community-only,secondary-channel}.md`
with config values and writes one plain-text file per version.

```bash
python3 "$SKILL_DIR/scripts/dm_cli.py" render \
  --guide-url "https://<workspace>.notion.site/<slug>-<page-id>" \
  --version all \
  --out-dir /absolute/path/to/work/dm-render \
  --config /absolute/path/to/config.yaml
```

Versions and their gates: `direct` always; `combined` and `community_only` when
`community.url` is set; `secondary` when `secondary_channel.url` is set. `all`
renders every version whose gate passes; asking for a gated-off version by name
fails with the missing key. `dm.versions` in the config sets the default.

Placeholders filled from config: `{guide_url}`, `{guide_title}` (`--guide-title`),
`{author_name}`, `{signoff}` (`author.dm_signoff`, else `author.name`),
`{community_name}`, `{community_url}`, `{community_platform}`,
`{secondary_channel_url}`, `{secondary_channel_handle}`, `{secondary_channel_type}`.
Anything else the template leaves as `{slot}` fails lint until you pass
`--set slot="text"` (or `--set slot=@/absolute/path.txt`). The one specific line
about the guide belongs to the writer, not the template; pass it that way.

`--templates-dir /absolute/path` overrides where the templates come from.
`--check-url` GETs the guide URL and requires a 200 (this one opens a socket).

### keywords: is this keyword taken

```bash
python3 "$SKILL_DIR/scripts/dm_cli.py" keywords --config /absolute/path/to/config.yaml --check FLOWS
```

Exit 1 when the keyword is already on an automation. The manual adapter has no
registry and returns an empty list; check your tool and your Content Board
(guide-maker's `keyword_check.py` covers the Notion side). Keywords are one
word, 3 to 12 upper-case characters, derived from the guide name.

### schedule: post + graphic + keyword automation

```bash
python3 "$SKILL_DIR/scripts/dm_cli.py" schedule \
  --content @/absolute/path/to/work/post.txt \
  --image /absolute/path/to/work/graphic-final.png \
  --time "2026-09-14T13:00:00Z" \
  --keyword FLOWS \
  --dm @/absolute/path/to/work/dm-render/dm-direct.txt \
  --dm-variant @/absolute/path/to/work/dm-render/dm-combined.txt \
  --comment-reply "Sent!" --comment-reply "Sent over, check your DMs" \
  --auto-connect \
  --out-dir /absolute/path/to/work \
  --config /absolute/path/to/config.yaml \
  --dry-run
```

`--time` is ISO 8601 with a timezone suffix; the CLI warns under 15 minutes ahead
or over 90 days. Convert from your posting window with the zone in
`dm_tool.timezone`; the manual checklist prints both local and UTC so an
off-by-one on the date is visible. A keyword with no `--dm` and a `--dm` with
no keyword both fail: the first sends commenters nothing, the second fires on
every comment including "nice post". `--image` is not enforced but a lead
magnet post without it asks the reader for nothing, since the keyword lives in
the graphic. Comment replies, the non-first-degree reply and auto-connect
default to `dm_tool.leadshark.*` in the config; flags override per call.

Drop `--dry-run` to write the bundle (manual) or create the scheduled post
(adapter).

### attach: automation on a post that is already live

```bash
python3 "$SKILL_DIR/scripts/dm_cli.py" attach \
  --post-url "https://www.linkedin.com/feed/update/urn:li:activity:7150000000000000000/" \
  --keyword FLOWS \
  --dm @/absolute/path/to/work/dm-render/dm-direct.txt \
  --status Paused \
  --config /absolute/path/to/config.yaml \
  --dry-run
```

Creates the automation `Paused` by default (`dm_tool.leadshark.create_as`) so
you read the DM once more before it fires. The manual adapter writes the same
bundle without `post.txt`.

### stats, test, image-fit

```bash
python3 "$SKILL_DIR/scripts/dm_cli.py" stats --range weekly --config /absolute/path/to/config.yaml
python3 "$SKILL_DIR/scripts/dm_cli.py" test --config /absolute/path/to/config.yaml
python3 "$SKILL_DIR/scripts/dm_cli.py" image-fit /absolute/path/to/work/graphic-final.png
```

`stats` returns comments, DMs sent and connections per automation on an
adapter; the manual adapter says where to look instead. The gap between
comments and DMs sent is mostly people outside your network who have not
connected yet.

`image-fit` matters because **the attachment ceiling is 4 MiB (4,194,304
bytes)**, measured on the LeadShark API which answers a bare 413 above it. A
PNG post graphic at 1080x1350 is often 4 to 5 MB. `image-fit` re-encodes to
JPEG at quality 95 with `subsampling=0`, which takes flat art with type from
about 4.5 MB to about 1 MB with no visible loss; LinkedIn re-encodes every
upload anyway. It does nothing when the file already fits. The LeadShark
adapter refuses an oversized image before uploading and points you here.
Ceiling from `dm_tool.leadshark.attachment_max_bytes` or `--max-bytes`.

## Where this sits in the weekly pipeline

1. guide-maker publishes the guide hub and produces the post copy, the post
   graphic with the keyword bar, and the DM text.
2. **You publish the guide to the web from the Notion app.** No script does
   this. Until you do, every link in the DM is dead.
3. `render` (or take the DMs the writer produced), then `keywords --check`.
4. `schedule --dry-run`, read the payload, then `schedule`.
5. Manual: open `dm-bundle/checklist.md` and do the steps in your tool.
6. After the first comment: confirm the DM fired and the link opened.

## Config keys this skill reads

```yaml
author:            name, dm_signoff
community:         platform, name, url
secondary_channel: type, handle, url
notion:            public_domain
workflow:          work_dir            # default parent for dm-render/ and dm-bundle/
copy:              cta_mode            # "copy" disables the keyword-in-copy guard
dm:                versions, merge_tag, max_lines, hard_wrap, guide_link_must_be_public
dm_tool:
  provider:        manual | leadshark
  timezone:        IANA zone for the checklist (falls back to dm_tool.leadshark.timezone)
  leadshark:       auto_connect, comment_replies, non_first_degree_reply,
                   attachment_max_bytes, create_as, timezone,
                   base_url, post_as, organization_id
providers:
  leadshark:       api_key             # env LEADSHARK_API_KEY and ~/.config/leadshark/api_key win over this
```

## Rules

- `--dry-run` before every `schedule` and `attach`. No exceptions.
- Never create an automation as `Running` on a post you have not read the DM for.
- Never delete an automation from a script; pause it. The stats go with it.
- One keyword per guide, unique across the account, derived from the guide name.
- The keyword goes in the graphic. Never in the copy.
- The DM link is the public one, and it resolves before the post goes out.
- No em dashes anywhere in an outgoing payload.
