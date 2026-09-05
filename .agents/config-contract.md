# The config contract

`skills/make-guide/scripts/_config.py` is imported by three loaders: itself (every `make-guide` script and the doctor), `skills/graphics-maker/scripts/_cfg.py` and `skills/dm-automation/scripts/_config_shim.py`. The two shims re-export the names below and add a standalone fallback for when `make-guide` is not installed next to them. Change a signature in one place and the other two break, so every change to this surface lands in one commit with the smoke test green.

## Search order

`load_config(path=None)` tries, in order, and stops at the first hit:

| Step | Where | Notes |
|---|---|---|
| 1 | The explicit `path` (`--config` on every script) | The smoke test uses this |
| 2 | `$GUIDE_MAKER_CONFIG` | One operator, many folders, one env var |
| 3 | `<dir>/.guide-maker/config.yaml` or `.json`, for `dir` in cwd, cwd's parent, up to `/` | The project home; found from any subfolder |
| 4 | `~/.config/guide-maker/config.yaml` or `.json` | A user-level home for one operator across projects |
| 5 | `skill_dir()/config.yaml` or `.json` | v2 location. Loads, and prints one stderr line: config inside the skill folder is deprecated; run `doctor.py --init` or `/setup-guide-maker` |

`doctor.py --print-paths --json` reports `config_source` as the step number that won, or `null`.

## `.guide-maker/` layout

```
<project>/.guide-maker/
  config.yaml            schema_version 2, the same keys as v2, plus an optional paths: block
  voice.md               override of make-guide/references/writing/voice.md
  examples.md            override of make-guide/references/linkedin/examples.md
  top-performers.md      override of make-guide/references/linkedin/top-performers.md
  topic-finder/          youtube-channels.json, subreddits.json, x-accounts.json, topics.json
  formats/               your own graphic format cards (ingest_reference.py writes here)
  state/                 closer-log.jsonl, format-usage-log.jsonl   (gitignored)
  .gitignore             state/, and config.yaml only when a secret was inlined
```

Every override is optional. A missing override means the shipped default is used, and nothing in the skill folder is edited to get there.

## Public surface

```
load_config(path=None) -> dict     the search order above; v1 flat keys still load through the shim
project_dir() -> Path              the first ancestor of cwd holding .guide-maker/, else cwd
project_file(name) -> Path         project_dir() / ".guide-maker" / name
resource(cfg, key) -> Path         the project override if it exists, else the shipped default
state_path(cfg, name) -> Path      cfg paths.state, else project_file("state") / name; parent created on demand
sibling(name) -> Path              the sibling skill folder; "guide-maker" is accepted as an alias of "make-guide" for one release
skill_dir() -> Path                the make-guide folder
skills_root() -> Path              its parent, or $GUIDE_MAKER_SKILLS_DIR
cfg_get(cfg, dotted, default)      nested read
secret(cfg, name) -> str           env var, then ~/.config/<name>/api_key, then the config
validate(cfg) -> list[str]         the messages the doctor prints as FAIL or WARN
```

### The override map

`resource(cfg, key)` knows four keys:

| Key | Override in `.guide-maker/` | Shipped default |
|---|---|---|
| `voice` | `voice.md` | `references/writing/voice.md` |
| `examples` | `examples.md` | `references/linkedin/examples.md` |
| `top_performers` | `top-performers.md` | `references/linkedin/top-performers.md` |
| `banned_words` | the path in `copy.banned_words_file` when it is absolute or project-relative | `references/writing/humanizer.md` |

A new override is a new row here, a new entry in the map, a line in `config.example.yaml`, a test, and a line on the [customizing page](../docs/customizing.md).

### State paths

Anything a script appends to at run time goes through `state_path`:

| State | Written by | Default |
|---|---|---|
| `closer-log.jsonl` | the orchestrator after Phase 3; read by `lint_copy.py rotation` | `.guide-maker/state/closer-log.jsonl` |
| `format-usage-log.jsonl` | `graphics_generate.py log`; read by `rotation` | `.guide-maker/state/format-usage-log.jsonl` (`graphics.usage_log` overrides) |
| format cards | `ingest_reference.py` | `.guide-maker/formats/` (`project_file("formats")`) |
| topic-finder configs | `/setup-guide-maker`, `doctor.py --init --from` | `.guide-maker/topic-finder/`, passed to `scan_all.py --config-dir` |

`paths.state` in `config.yaml` moves the state folder anywhere. Nothing else about state is configurable.

## The invariant

**A script that opens a file for writing under `skill_dir()` is a bug.** Under `npx skills` the skill folder is a copy that `npx skills update` replaces; under a plugin it would be read-only. The smoke test asserts `git status --porcelain skills/` is empty after a full run.
