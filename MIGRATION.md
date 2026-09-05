# Migrating

## v2 to v3

v3 moves the config out of the skill folder, renames the core skill, and adds two skills. Nothing about Notion, the script CLIs or the config keys changed. Your v2 installation keeps working on upgrade day; the deprecation lines tell you what to move.

### The config moved to `.guide-maker/`

v2 read `config.yaml` from inside the skill folder. Under `npx skills` that folder is replaced on every update, so v3 reads from a `.guide-maker/` folder in your project, found by walking up from wherever you run. The search order is: an explicit `--config`, `$GUIDE_MAKER_CONFIG`, `<project>/.guide-maker/config.yaml`, `~/.config/guide-maker/config.yaml`, and last the v2 location inside the skill folder, which still loads with one stderr line.

Move it in one command:

```bash
python3 <skills>/make-guide/scripts/doctor.py --init --from <skills>/make-guide/config.yaml
```

That copies the config, the graphics usage log, the topic-finder JSON lists and any of `voice.md`, `examples.md`, `top-performers.md` you had edited (detected by diff against the shipped file) into `.guide-maker/`, and writes its `.gitignore`. `/setup-guide-maker` offers the same move as its first question. Overrides and state have new homes:

| v2 | v3 |
|---|---|
| `references/writing/voice.md` (edited in place) | `.guide-maker/voice.md` |
| `references/linkedin/examples.md` (edited in place) | `.guide-maker/examples.md` |
| `references/linkedin/top-performers.md` (edited in place) | `.guide-maker/top-performers.md` |
| `topic-finder/config/*.json` | `.guide-maker/topic-finder/*.json` |
| `graphics-maker/references/format-library/<yours>.md` | `.guide-maker/formats/<yours>.md` |
| `graphics-maker/format-usage-log.jsonl` | `.guide-maker/state/format-usage-log.jsonl` |
| `<work dir>/../closer-log.jsonl` | `.guide-maker/state/closer-log.jsonl` |

Schema stays 2. `paths:` is a new optional block (`paths.state` moves the state folder). No key was renamed.

### `/guide-maker` is `/make-guide`

The folder is `skills/make-guide/`, the frontmatter name is `make-guide`, and the slash command follows. There is no redirect skill: under `npx skills` a redirect is a second entry in your list. `sibling("guide-maker")` in the two shims still resolves for this release. The description no longer carries the "find me a topic" triggers; `topic-finder` owns them.

### `install.sh` users

Either `npx skills@latest add josue-commits/guide-maker` over the top and delete the old `guide-maker/` folder, or `git pull` and re-run `./install.sh /path/to/project`. `install.sh` no longer clones `topic-finder`; it is inside the tree now, as a subtree.

### Two new skills

`setup-guide-maker` (run once per project; writes `.guide-maker/` and an `## Agent skills` block in your `CLAUDE.md` or `AGENTS.md`) and `ask-guide-maker` (the map). Both are user-invoked. Pick them when the installer asks.

### Nothing else

Notion databases: unchanged. Script flags: unchanged; two new doctor flags, `--init` and `--list-databases`. Config keys: unchanged.

### The one-minute check

```bash
pip install pyyaml pillow
python3 <skills>/make-guide/scripts/doctor.py --init --from <skills>/make-guide/config.yaml
python3 <skills>/make-guide/scripts/doctor.py
python3 <skills>/make-guide/scripts/doctor.py --print-paths
```

Doctor green, `config_source` pointing at `.guide-maker/`, and you are on v3.

## v1 to v2

v1 (March 2026) was one skill folder with a flat `config.yaml`. v2 is three skills plus a cloned sibling, a nested config, and a different CTA. Your v1 config keeps loading; the behavior defaults do not.

### 1. The config file

The v1 flat keys still load through a shim in `scripts/_config.py`. You will see one line on stderr:

```
[guide-maker] .../config.yaml uses the deprecated v1 flat config format; loading through the compatibility shim. Run scripts/doctor.py --migrate-config to print the v2 file.
```

Print the v2 version and replace your file:

```bash
python3 skills/make-guide/scripts/doctor.py --migrate-config --config skills/make-guide/config.yaml > /tmp/config.v2.yaml
# read it, then
mv /tmp/config.v2.yaml skills/make-guide/config.yaml
python3 skills/make-guide/scripts/doctor.py
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

### 2. Behavior defaults that changed

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

Why the CTA moved: `skills/make-guide/references/strategy/cta-evidence.md`. If you want the old behavior on your own account, set `copy.cta_mode: copy`; the linter and the doctor will warn every time.

### 3. Notion databases

**Content Board** (only if you use it):
- Add a `Graphic` property of type **files**. The post graphic is attached there, never as a body image.
- `Status` must have a `Draft` option; cards are created as Draft.
- `Type` no longer receives `sales-resource`; every card is `guide`. Leave the old option in place for old cards.

**Guide DB**:
- Optionally add `Use-case Stack` to the `Type` select if you plan to write that guide type.
- Nothing else changes. `doctor.py` checks both databases and lists what is missing.

### 4. Files that moved or went away

| v1 | v2 |
|----|----|
| `channels.json` | `skills/topic-finder/config/youtube-channels.json`, with a `category: tool\|business` per channel. Clone the sibling with `install.sh` or `git clone https://github.com/josue-commits/topic-finder skills/topic-finder`. |
| `scripts/scan_channels.py` | `skills/topic-finder/scripts/scan_all.py` (YouTube + Reddit + X, writes `health.json`) |
| `templates/dm-community.md` | `templates/dm-combined.md` + `templates/dm-community-only.md` |
| `templates/dm-direct.md` | rewritten; `{{firstName}}`, no hard-wrap, public URL |
| the skill at the repo root | `skills/make-guide/` (so `skills/graphics-maker/` and `skills/dm-automation/` can sit next to it) |

If you installed v1 by copying the folder into `.claude/skills/guide-maker`, copy `skills/guide-maker` over it and add the two optional siblings next to it. `_config.py` finds them by directory, or through `GUIDE_MAKER_SKILLS_DIR`.

### 5. Scripts whose flags changed

- `md_to_notion.py create-content-entry`: `--variation` and `--dm` are both repeatable `"Label|text-or-@file"`; `--graphic PATH`; `--status` defaults to Draft; `--type` defaults to guide (`--content-type` still accepted); `--dry-run`.
- `md_to_notion.py blocks FILE` (new): prints the converted block JSON. `public-url --page-id ID [--check]` (new).
- `banner_generator.py simple`: `--keyword` and `--allow-keyword` (new); `--config` on every script.
- `publish_guide_hub.py`: same flags; `--source "youtube|..."` is refused by default.
- New scripts: `doctor.py`, `lint_copy.py`, `keyword_check.py`, `scan_published_leaks.py`.

### 6. The one-minute check

```bash
pip install -r requirements.txt
python3 skills/make-guide/scripts/doctor.py --migrate-config --config skills/make-guide/config.yaml
python3 skills/make-guide/scripts/doctor.py
python3 skills/make-guide/scripts/lint_copy.py copy skills/make-guide/references/linkedin/examples.md
```

Doctor green, linter exit 0, and you are on v2.
