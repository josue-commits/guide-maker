# Config lives in the project, not in the skill folder

## Context

v2 kept `config.yaml` inside `skills/guide-maker/`, next to the scripts that read it, and told the operator to edit `references/linkedin/examples.md` and `references/writing/voice.md` in place. Five things read or wrote inside a skill folder at run time: the config, the graphics usage log, `ingest_reference.py` writing format cards into `references/format-library/`, topic-finder's `config/*.json`, and every "edit `references/...`" instruction.

Under `npx skills` the skill folder is a copy that `npx skills update` replaces. Everything the operator had put inside it goes with the update. Under a plugin the folder would be read-only from the start.

## Decision

The operator's project owns a `.guide-maker/` folder: `config.yaml`, optional overrides of the three voice files, the topic-finder JSON lists, user format cards, and a gitignored `state/`. `_config.py` finds it by walking up from the working directory, so any subfolder of the project resolves the same home. `~/.config/guide-maker/` stays as a user-level home for one operator across many folders. The v2 location still loads for one release with a deprecation line.

Nothing under `skills/` is written at run time. That is an invariant the smoke test asserts.

## Consequences

- One config for six skills, found the same way by all three loaders.
- The skill folders are identical on every machine and can be replaced wholesale.
- The operator can read every file the setup skill wrote and change it by hand.
- Notion ids stay out of `docs/` and out of the skill tree.
- `doctor.py --init --from <old>` moves a v2 installation in one command; `/setup-guide-maker` offers it as its first question.

Why `.guide-maker/` and not `docs/agents/`: the operator's project is usually a content folder, not a code repo; the folder holds JSON source lists and state, not a single markdown file.
