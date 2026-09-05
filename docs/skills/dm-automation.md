# dm-automation

## What it does

`dm-automation` takes a finished guide from the keyword onward: it renders every DM version your config allows from the templates, lints them, and then either writes a paste-ready bundle with a checklist for whatever tool you use, or schedules the post with its graphic and keyword automation through an adapter. It also answers "is this keyword taken", "pull the leads" and "how did Monday's post do" when an adapter is configured.

Manual is the default; an adapter is an upgrade. With `dm_tool.provider: manual` nothing ever opens a socket: you get `post.txt`, one `dm-*.txt` per version, the graphic and `checklist.md`, and you do the steps in your own tool. `leadshark` ships as the reference adapter and does the same through one API call, after a `--dry-run` that prints the exact payload.

## When to reach for it

Type `/dm-automation`, or the agent reaches for it when you say "set the keyword", "schedule the post", "render the DMs", "check if KEYWORD is taken", "pull the leads", "how did Monday's post do", or when `make-guide` reaches step 3e.

| Your situation | Command |
|---|---|
| The guide is published, you need the DM texts | `render`, with the public guide URL |
| Picking a keyword | `keywords --check`; `make-guide`'s `keyword_check.py` covers the Notion side |
| The post, the graphic and the DM are ready | `schedule --dry-run`, read it, then `schedule` |
| The post is already live and needs an automation | `attach`, created paused |
| The graphic is over the attachment ceiling | `image-fit` |
| Numbers for last week | `stats`, adapter only |

## Prerequisites

`/setup-guide-maker` has to have run: the DM versions depend on `community` and `secondary_channel`, and the link check on `notion.public_domain`.

| It needs | Notes |
|---|---|
| From `config.yaml` | `author` (name, `dm_signoff`), `community`, `secondary_channel`, `notion.public_domain`, `workflow.work_dir`, `copy.cta_mode`, `dm` (versions, `merge_tag`, `max_lines`, `hard_wrap`, `guide_link_must_be_public`), `dm_tool` (provider, timezone, the `leadshark` block), `providers.leadshark` |
| The templates | Shipped in `make-guide/templates/`; `--templates-dir` points elsewhere when `make-guide` is not installed next to it |
| An adapter key | `LEADSHARK_API_KEY` or `~/.config/leadshark/api_key`, only with `provider: leadshark` |
| Pillow | Only for `image-fit` |

## The bundle, and the four rules

The word to hold onto is **bundle**. Whatever the provider, the deliverable is a folder you can hand to anyone: the post text, every DM version, the graphic, and a checklist that prints the posting time in your zone and in UTC so an off-by-one on the date is visible.

Before anything lands in it, four lint rules run on every outgoing text:

| Rule | Why |
|---|---|
| The merge tag is exactly `{{firstName}}` (or `dm.merge_tag`) | `{name}`, `[Name]` and `{first_name}` reach the lead as literal text |
| The guide link is public | Notion's copy-link button gives an `app.notion.com` or workspace `notion.so` URL that gates on membership; every commenter gets a dead link. `render` exits 2 on one |
| No hard wrap | The DM pane wraps again; a pre-wrapped paragraph reads like a broken paste. One paragraph is one line |
| No em dashes | Anywhere in a payload: DM, variants, replies, automation name |

Also enforced: `dm.max_lines` (seven non-blank lines by default), no unfilled `{slot}`, the adapter's character limit, and the keyword must not appear in the post copy unless `copy.cta_mode: copy`.

## Common questions

**`name-tag` on a DM.**

`{name}` or `[Name]` is in the text. Use the tag your tool substitutes, `{{firstName}}` for LeadShark, set in `dm.merge_tag`.

**`public-url` on a DM.**

The guide link is an in-app link. Publish the page to the web from the Notion app, then use the `<workspace>.notion.site` URL; `md_to_notion.py public-url --page-id <id>` computes it and `--check` confirms it answers.

**`hard-wrap` on a DM.**

A paragraph has internal line breaks. One paragraph per line, blank lines between paragraphs, a URL may sit alone.

**LeadShark answers 413 on the attachment.**

The ceiling is 4 MiB. A PNG post graphic at 1080 by 1350 is often over it. `image-fit` re-encodes to JPEG under the ceiling with no visible loss; `schedule` does it for you when `attachment_max_bytes` is exceeded.

**LeadShark answers 403 with a tier note.**

The endpoint needs a higher plan; the note says which. The manual adapter always works.

**It scheduled at the wrong hour.**

`--time` is ISO 8601 with an offset or `Z`. `dm_tool.timezone` only drives the checklist's local column; read the UTC line in `--dry-run` before dropping the flag.

**Does it send the DMs?**

No. Your tool watches the comments and sends; this skill prepares what it sends and, with an adapter, creates the automation paused so you read the DM once more before flipping it on. Never create one as `Running` on a post whose DM you have not read.

## It's working if

- `render` writes one file per version, each carrying `{{firstName}}` and the public `notion.site` link, and refuses an in-app link with exit 2.
- `checklist.md` shows the posting time in your zone and in UTC on adjacent lines.
- `schedule --dry-run` prints the full payload and opens no socket, whichever provider is configured.
- `public-url --check` is green before anything goes live.
- With an adapter, the automation shows as paused in the tool until you flip it.

## Where it fits

`dm-automation` is the last step of the chain, 3e, and the one you come back to on posting day. [graphics-maker](./graphics-maker.md) is its closest neighbour, because the keyword on the graphic and on the automation must be identical; [make-guide](./make-guide.md) owns the templates it renders and the `public-url` check it relies on. When you are unsure which step you are on, [ask-guide-maker](./ask-guide-maker.md) routes you.
