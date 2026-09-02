# DM Guide

A reader comments the keyword under the post. Your DM tool (or you, by hand) sends them one message. This file says what that message is, which versions exist, and the rules every version follows. The templates in `templates/dm-*.md` are shapes; the writer agent rewrites the specific lines for every guide.

## The versions and where they send people

| Version | Template | Generated when | Destination |
|---------|----------|----------------|-------------|
| direct | `dm-direct.md` | always | the guide |
| combined | `dm-combined.md` | `community.url` set | the guide, community as an aside |
| community_only | `dm-community-only.md` | `community.url` set | the community only |
| secondary | `dm-secondary-channel.md` | `secondary_channel.url` set | the guide, then the secondary channel |

`dm.versions: auto` generates every version its config gates allow. A list (`[direct, combined]`) generates exactly those. Every generated version goes on the Content Board card as its own toggle, and the operator picks per campaign which one the DM tool sends.

**One destination per DM.** The combined version carries the community link as an aside; the secondary version carries the channel ask. Never both in one message. Two "go here next" instructions means most people go nowhere.

## The merge tag

The first-name placeholder is `dm.merge_tag`, default `{{firstName}}`, which is what LeadShark substitutes. Keep the exact spelling, double braces included. `[Name]`, `{name}`, `{first_name}` and `{firstName}` with single braces are not recognized by any tool and reach the lead as literal text. `lint_copy.py dm` fails on all of them.

If your tool uses a different tag, change `dm.merge_tag` and every template renders with it.

## Never hard-wrap

Each paragraph is **one continuous line**, however long. Blank lines separate paragraphs; that is the only place a newline belongs. The single exception is a bare URL, which may sit on its own line so it does not break mid-sentence.

LinkedIn's DM pane wraps text itself at whatever width the reader's window happens to be. Baking in your own line breaks at 72 characters means the reader sees the text wrapped twice, with short ragged lines that look like a broken paste. The linter fails a paragraph that spans more than one non-URL line.

## The guide link must be the public one

Notion's copy-link button gives you `app.notion.com/...` or `notion.so/...`. Both serve the workspace app and gate on membership. A lead is not in your workspace, so that link is a dead end for every single recipient.

The public URL is `https://<notion.public_domain>/<slug>-<page-id>` and it resolves only after you publish the page to web from the Notion UI, by hand. The pipeline never does this for you. Before a DM goes live:

```bash
python3 {SKILL_DIR}/scripts/md_to_notion.py public-url --page-id HUB_PAGE_ID --check
```

Exit 0 means the public page answers. Exit 1 means it is not published yet, and the DM would send a 404.

`dm.guide_link_must_be_public: true` makes the linter fail on any in-app link.

## Human voice (kill the formula)

DMs that read as a sequence step get ignored or reported. Write each one like a person firing off a quick message to one reader, not a template with the name swapped in.

**Kill these tells:**
- The formula opener: "Hey {{firstName}}! Thanks for commenting on my post." Every DM starting identically is the surest sign of automation.
- The pitch block: "I also run a free community where we share stuff like this every week. Workflows, automations, setups that move the needle." That sentence is the most obviously templated line a DM can carry.
- Announcing the link ("Here's the guide:" as its own paragraph). Drop it mid-thought.
- The collaborative sign-off: "Let me know if you have any questions!" and its cousins ("Hope this helps!", "Happy to chat"). The humanizer bans them everywhere and the linter fails them here.
- Formal language: "I appreciate your interest", "Please find the guide below".

**Do instead:**
- Open differently every week (`dm.vary_opener_weekly`). React to the specific thing, or just get to the point.
- Say one real, specific thing about the guide like a person who built it: a number, a gotcha, the part that surprised you.
- Weave any second link in casually, as an aside ("I keep all of these in [community] too if you want the rest:").
- Sign off with the bare first name (`author.dm_signoff`, falling back to `author.name`). Not "Cheers, Name", not "Best regards".
- Read it out loud. If it sounds like a funnel, rewrite it.

## Length and shape

- `dm.max_lines` non-blank lines, default 7. People do not read long DMs from strangers.
- Zero em dashes. Commas and periods.
- Match the language of the post.
- No AI vocabulary (the banned list in `references/writing/humanizer.md` applies).

## Linting

```bash
python3 {SKILL_DIR}/scripts/lint_copy.py dm WORK_DIR/dm/*.txt --config config.yaml
```

Rules: `name-tag`, `hard-wrap`, `app-url`, `em-dash`, `max-lines` (warn), `formula-opener`, `collab-signoff`, `banned-word`, `missing-merge-tag` (warn). Exit 0 clean, 1 failures, 2 warnings only.

## Rendering and scheduling

The optional `dm-automation` sibling renders these templates with the config values filled in and either writes a paste-ready bundle (`dm_tool.provider: manual`) or creates the keyword automation in LeadShark. From this skill:

```bash
python3 {DM_AUTOMATION_DIR}/scripts/dm_cli.py render --guide-url URL --guide-title "Title" --set specific_line="..." --out WORK_DIR/dm/
python3 {DM_AUTOMATION_DIR}/scripts/dm_cli.py schedule --keyword KEYWORD --dm WORK_DIR/dm/combined.txt --dry-run
```

Without the sibling, paste the rendered toggle from the Content Board into your DM tool by hand.
