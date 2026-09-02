# Migrating from guide-maker v1 to v2

v1 (March 2026) was one skill folder with a flat `config.yaml`. v2 is three skills plus a cloned sibling, a nested config, and a different CTA. Your v1 config keeps loading; the behavior defaults do not.

## 1. The config file

The v1 flat keys still load through a shim in `scripts/_config.py`. You will see one line on stderr:

```
[guide-maker] .../config.yaml uses the deprecated v1 flat config format; loading through the compatibility shim. Run scripts/doctor.py --migrate-config to print the v2 file.
```

Print the v2 version and replace your file:

```bash
python3 skills/guide-maker/scripts/doctor.py --migrate-config --config skills/guide-maker/config.yaml > /tmp/config.v2.yaml
# read it, then
mv /tmp/config.v2.yaml skills/guide-maker/config.yaml
python3 skills/guide-maker/scripts/doctor.py
```

| v1 key | v2 key |
|--------|--------|
| `notion_api_key` | `notion.api_key` (or env `NOTION_API_KEY`, or `~/.config/notion/api_key`) |
| `guide_database_id` | `notion.guide_database_id` |
| `content_board_database_id` | `notion.content_board_database_id` |
| `author_name`, `linkedin_url` | `author.name`, `author.linkedin_url` |
| `community_name`, `community_url`, `community_description` | `community.name`, `community.url`, `community.callout_line` |
| `accounts[].cta_type: community\|direct` | `accounts[].dm_destination: community\|direct\|secondary\|auto` |
| `kieai_api_key` | `providers.kieai.api_key` (or env `KIEAI_API_KEY`) |
| `brand_colors` | `brand.colors` |
| `ytdlp_path` | `tools.ytdlp_path` (empty means "whatever is on PATH") |

Everything else in `config.example.yaml` is new and has a default. The six most people change: `copy.cta_mode`, `copy.words`, `workflow.gates`, `community.*`, `secondary_channel.*`, `excluded_topics`.

## 2. Behavior defaults that changed

| What | v1 | v2 default | Key |
|------|----|------------|-----|
| Where the keyword goes | in the copy, as a Like / Comment block | in the post graphic's CTA band, never in the copy | `copy.cta_mode: graphic` |
| Post length | 250-350 words | 180-250 words, target 215 | `copy.words` |
| Post structure | hook + arrow list + CTA block | prose 8-beat essay, arrows only for a framework | `copy.structure: prose` |
| Variation names | Story / Problem-Pain / Data-Framework | contrarian / problem_pain / quantity_build | `copy.hooks` |
| Closer | fixed 4-line block with a thumbs-up | one value line + pointing-down emoji, seven rotating closers | `copy.closers` |
| DM merge tag | `{name}` | `{{firstName}}` (what LeadShark substitutes) | `dm.merge_tag` |
| DM versions | community + direct | direct, combined, community_only, secondary, gated by config | `dm.versions` |
| DM guide link | whatever Notion's copy-link gave you | the public `notion.site` URL, checked with `public-url --check` | `dm.guide_link_must_be_public` |
| Approval gates | outline, then content | same (`two`); `one` ships after the outline | `workflow.gates` |
| Content Board cards | one per account | one per guide; `account` restores the fan-out | `workflow.one_card_per` |
| Cover | could carry the keyword | never carries the keyword; `--keyword` makes the script refuse | `cover.*` |
| Sources | no video at all | official + institutional; creator videos refused | `sources.cite_creator_videos: false` |
| Topic research | `channels.json` + `scan_channels.py` in this skill | sibling `topic-finder` with three sources and `health.json` | `topic_finder.*` |

Why the CTA moved: `skills/guide-maker/references/strategy/cta-evidence.md`. If you want the old behavior on your own account, set `copy.cta_mode: copy`; the linter and the doctor will warn every time.

## 3. Notion databases

**Content Board** (only if you use it):
- Add a `Graphic` property of type **files**. The post graphic is attached there, never as a body image.
- `Status` must have a `Draft` option; cards are created as Draft.
- `Type` no longer receives `sales-resource`; every card is `guide`. Leave the old option in place for old cards.

**Guide DB**:
- Optionally add `Use-case Stack` to the `Type` select if you plan to write that guide type.
- Nothing else changes. `doctor.py` checks both databases and lists what is missing.

## 4. Files that moved or went away

| v1 | v2 |
|----|----|
| `channels.json` | `skills/topic-finder/config/youtube-channels.json`, with a `category: tool\|business` per channel. Clone the sibling with `install.sh` or `git clone https://github.com/josue-commits/topic-finder skills/topic-finder`. |
| `scripts/scan_channels.py` | `skills/topic-finder/scripts/scan_all.py` (YouTube + Reddit + X, writes `health.json`) |
| `templates/dm-community.md` | `templates/dm-combined.md` + `templates/dm-community-only.md` |
| `templates/dm-direct.md` | rewritten; `{{firstName}}`, no hard-wrap, public URL |
| the skill at the repo root | `skills/guide-maker/` (so `skills/graphics-maker/` and `skills/dm-automation/` can sit next to it) |

If you installed v1 by copying the folder into `.claude/skills/guide-maker`, copy `skills/guide-maker` over it and add the two optional siblings next to it. `_config.py` finds them by directory, or through `GUIDE_MAKER_SKILLS_DIR`.

## 5. Scripts whose flags changed

- `md_to_notion.py create-content-entry`: `--variation` and `--dm` are both repeatable `"Label|text-or-@file"`; `--graphic PATH`; `--status` defaults to Draft; `--type` defaults to guide (`--content-type` still accepted); `--dry-run`.
- `md_to_notion.py blocks FILE` (new): prints the converted block JSON. `public-url --page-id ID [--check]` (new).
- `banner_generator.py simple`: `--keyword` and `--allow-keyword` (new); `--config` on every script.
- `publish_guide_hub.py`: same flags; `--source "youtube|..."` is refused by default.
- New scripts: `doctor.py`, `lint_copy.py`, `keyword_check.py`, `scan_published_leaks.py`.

## 6. The one-minute check

```bash
pip install -r requirements.txt
python3 skills/guide-maker/scripts/doctor.py --migrate-config --config skills/guide-maker/config.yaml
python3 skills/guide-maker/scripts/doctor.py
python3 skills/guide-maker/scripts/lint_copy.py copy skills/guide-maker/references/linkedin/examples.md
```

Doctor green, linter exit 0, and you are on v2.
