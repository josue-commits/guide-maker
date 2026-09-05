# skills/ stays flat; grouping lives in docs

## Context

The reference architecture sorts skills into bucket folders (`engineering/`, `productivity/`, `misc/`) with a README per bucket, and promotes only some buckets to the plugin. This repo has six skills that fall into two natural groups: the pipeline (`setup-guide-maker`, `ask-guide-maker`, `make-guide`, `topic-finder`) and the assets (`graphics-maker`, `dm-automation`).

## Decision

`skills/` stays flat: six folders, one `SKILL.md` each. The two groups exist in `README.md` Reference, in `skills/README.md` and in the router, and nowhere in the filesystem.

## Why

- **Sibling resolution.** `_config.skills_root()` is `skill_dir().parent`; `_cfg.py` and `_config_shim.py` resolve `make-guide` as `parents[2] / "make-guide"`. A bucket layer breaks all three loaders and the smoke test for no functional gain.
- **No promotion to buy.** Buckets earn their keep when a plugin manifest ships some and hides others. With `npx skills` the user picks skills one by one from a flat list anyway, and there is nothing to hide: all six ship.
- **Six is not enough to need folders.** A bucket README for two skills is furniture.

## Revisit when

There are more than ten skills, or a group that should not be installed by default appears. At that point the loaders need a `skills_root()` that walks up until it finds a folder holding `make-guide/`, and that change lands first.
