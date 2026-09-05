# topic-finder is vendored as a git subtree

## Context

`topic-finder` is its own repository with its own README, tests and release cadence, usable by anyone who wants topic research without a guide pipeline. v2 of this repo did not track it: `install.sh` cloned it at install time, the smoke test skipped when it was absent, and `.gitignore` excluded the folder. Under `npx skills`, which reads `SKILL.md` files from this repo's tree, an absent folder is an absent skill.

## Decision

`skills/topic-finder/` is a git subtree of `https://github.com/josue-commits/topic-finder.git`, pinned to a tag and squashed:

```
git subtree add --prefix skills/topic-finder https://github.com/josue-commits/topic-finder.git v2.0.0 --squash
git subtree pull --prefix skills/topic-finder https://github.com/josue-commits/topic-finder.git v2.1.0 --squash
```

The separate repo stays the source of truth. Fixes go upstream first, then a `subtree pull`. Nothing in `skills/topic-finder/` is edited here.

## Consequences

- `npx skills add` lists six skills, including `topic-finder`.
- `install.sh` no longer clones anything; it copies `skills/*`.
- The smoke test drops its "not installed" skip.
- `.gitignore` drops `skills/topic-finder/`.
- The upstream `VERSION` file travels with the subtree and is the version to quote in the changelog.
- A submodule was rejected: `npx skills` and a plain clone both leave a submodule empty until the user runs a second command.
