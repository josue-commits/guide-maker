# Releasing

Versions live in three places that must agree: the `VERSION` file, the top `## x.y.z` heading in `CHANGELOG.md`, and the git tag `vx.y.z`. `scripts/check_version.py --check` enforces the first two on every push (`docs.yml`) and all three on a tag (`release.yml`). There is no Node, no changesets, no version field in any manifest.

## Flow

1. Write the release notes under `## Unreleased` in `CHANGELOG.md` as the work lands. Sections: `### Breaking`, `### Added`, `### Changed`, `### Fixed`, whichever apply.
2. On release day, retitle `## Unreleased` to `## x.y.z - YYYY-MM-DD` and write `x.y.z` into `VERSION`.
3. `python3 scripts/check_version.py --check` locally.
4. Commit: `chore: release x.y.z`.
5. Tag and push: `git tag vx.y.z && git push && git push --tags`.
6. `release.yml` runs on the tag: the version check (tag included), the smoke test, then a GitHub Release whose body is the matching `CHANGELOG.md` section.
7. From a clean folder, `npx skills@latest add josue-commits/guide-maker` must list six skills. Do it once per release; the skills.sh index reads the default branch.

## Versioning

- **Major**: a config location or key rename, a skill rename, an `install.sh` that stops doing something it did.
- **Minor**: a new skill, a new script flag, a new config key with a default.
- **Patch**: a fix that changes no interface.

The `topic-finder` subtree has its own `VERSION` (upstream's). Bumping it is `git subtree pull --prefix skills/topic-finder https://github.com/josue-commits/topic-finder.git vX.Y.Z --squash`, recorded as a `### Changed` line here.
