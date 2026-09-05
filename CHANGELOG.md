# Changelog

## 3.0.0 - 2026-09-05

### Breaking

- The config moved out of the skill folder. It lives in `<project>/.guide-maker/config.yaml` (found by walking up from wherever you run) or `~/.config/guide-maker/config.yaml`. The v2 location inside the skill folder still loads for this release, with one deprecation line on stderr. `doctor.py --init --from <old-config>` moves the config, the logs, the topic-finder lists and any edited voice file in one command. See `MIGRATION.md`.
- `skills/guide-maker` is `skills/make-guide`, and `/guide-maker` is `/make-guide`. No redirect skill. `sibling("guide-maker")` in the two shims still resolves for one release.
- `install.sh` no longer clones `topic-finder`. It copies the six folders under `skills/` into `<project>/.claude/skills/`.
- Nothing is written under `skills/` at run time. The graphics usage log, the format cards `ingest_reference.py` writes, the closer log and the real topic-finder configs moved to `.guide-maker/state/`, `.guide-maker/formats/` and `.guide-maker/topic-finder/`.
- `make-guide`'s description no longer carries the "find me a topic" triggers; `topic-finder` owns them.

### Added

- `setup-guide-maker`: user-invoked, prompt-driven setup. Picks the Notion databases from a list, asks about author, community, secondary channel, DM tool, image provider, gates and topic sources, writes `.guide-maker/` and an `## Agent skills` block in `CLAUDE.md` or `AGENTS.md`, and ends with a green doctor. Folds `docs/setup.md`.
- `ask-guide-maker`: user-invoked router. The main flow, the on-ramps for entering the chain in the middle, the standalone runs, the gates you hold, and the setup precondition.
- `.guide-maker/` overrides of the shipped voice files: `voice.md`, `examples.md`, `top-performers.md`. An optional `paths.state` key moves the state folder. Schema stays 2; no key was renamed.
- `doctor.py --init [--project DIR | --home] [--from OLD]` writes the folder skeleton and migrates a v2 installation; `doctor.py --list-databases` lists the databases the integration can see; `--print-paths --json` reports `project_dir`, `config_source` and every sibling.
- `topic-finder` vendored as a git subtree pinned to v2.0.0, so `npx skills add` lists six skills and the smoke test no longer skips it.
- Distribution through skills.sh: `npx skills@latest add josue-commits/guide-maker`, with `npx skills update` as the update path. `install.sh` remains for machines without Node.
- One docs page per skill under `docs/skills/`, with a fixed frame: what it does, when to reach for it, prerequisites, common questions, it's working if, where it fits.
- Maintainer conventions: `CLAUDE.md` with twelve invariants (`AGENTS.md` is a symlink to it), `.agents/` (install block, invocation, writing docs, config contract, release), four ADRs, `.out-of-scope/`, `skills/README.md`, `scripts/list-skills.sh`.
- Versioning: `VERSION`, `scripts/check_version.py --check`, `release.yml` (tag `v*` creates the GitHub Release from the matching changelog section), `docs.yml` (README install block byte-equal to `.agents/install-block.md`, every relative markdown link resolves, version check).

### Changed

- README rewritten: a 30-second install with two exclusive routes, the five failure modes the skills fix, Reference grouped Pipeline / Assets and User-invoked / Model-invoked, an eight-row pipeline table, the `.guide-maker/` tree.
- `docs/customizing.md` rewritten around the `.guide-maker/` overrides; `docs/troubleshooting.md` covers the five-step search order, the deprecated skill-folder config, edits lost to `npx skills update`, and the rename. `docs/setup.md` deleted.
- The smoke test covers the project config from a nested working directory, `GUIDE_MAKER_CONFIG`, the legacy config with its deprecation line, override lookup and state paths, and asserts `git status --porcelain skills/` is empty after a full run.

## 2.0.0 - 2026-09-02

### Breaking

- The keyword moved out of the post copy into the post graphic's CTA bar (`copy.cta_mode: graphic`, the default). The evidence and the rule are in `docs/strategy.md`. `copy.cta_mode: copy` keeps the old pattern with a warning.
- Config schema v2 is nested. v1 flat keys still load with one deprecation line; `doctor.py --migrate-config` prints the v2 file. See `MIGRATION.md`.
- `channels.json` and `scripts/scan_channels.py` are gone. Topic research runs through the `topic-finder` sibling skill (three sources, health gate). `install.sh` fetches it.
- The skill moved to `skills/guide-maker/`; two sibling skills were added next to it. Install with `install.sh` instead of `cp -r`.
- Content Board entries default to `Status: Draft`, `Type: guide`, one card per guide, and need a `Graphic` files property.
- DM templates use `{{firstName}}` (configurable in `dm.merge_tag`). `{name}` is rejected by the linter.
- Copy target is 180 to 250 words in the prose structure. Old default was 250 to 350 with an arrow list.
- `templates/dm-community.md` was replaced by `dm-combined.md` and `dm-community-only.md`.

### Added

- `skills/graphics-maker`: the LinkedIn post graphic. Pillow title card with the CTA bar at zero cost, or a two-pass scene + text pipeline through an image provider (KieAI reference implementation, OpenAI best-effort). C2PA credentials stripped from every final so LinkedIn does not badge it.
- `skills/dm-automation`: renders the DM bundle from the templates and either hands you a checklist (manual, default) or schedules through an adapter (LeadShark reference implementation).
- `doctor.py`: one command that validates config, Notion databases and properties, yt-dlp, sibling skills, provider keys and fonts.
- `lint_copy.py`: banned vocabulary, em dashes, keyword-in-copy, banned CTA phrases, word count, closer rotation, DM merge tag, hard wrap, public URL.
- `keyword_check.py`: keyword shape and collisions across the Content Board, Guide DB titles and your DM tool.
- `scan_published_leaks.py`: walks every published page for authoring directives and banned words.
- Three-source topic research with a scan-health gate, depth gate, gap analysis, `excluded_topics`, institutional sources policy, and no cross-guide references.
- A fourth guide type, Use-case Stack, with a synthetic example. A synthetic Comparison example too.
- Secondary channel credit line and DM version (YouTube, newsletter, podcast).
- Bundled OFL font (Inter) with Linux and Windows fallbacks.
- Smoke test that runs on a fresh machine with no tokens, and CI on Ubuntu and macOS that also fails on any private string or em dash.

### Fixed

- Notion returned 400 on ```js, ```sh, ```yml and other fence languages outside its enum. Languages are normalized now.
- Authoring directives (`**Page icon:** X`) leaked into published pages. Stripped at conversion, and `scan_published_leaks.py` audits what is live.
- The Pillow banner used the wrong HelveticaNeue face (index 4 is Condensed Bold, not Bold).
- A missing output directory threw away a paid banner generation.
- The documented `publish_guide_hub.py` and `banner_generator.py` commands in SKILL.md did not match the scripts' flags.
- `create-content-entry` had no way to write the DM toggles the docs promised, and wrote `Status: Review` while the docs said Draft.
- `scan_channels.py` crashed on channels with a scheduled premiere (`null` view_count). Fixed in topic-finder v2.
- Relative script paths in AGENT.md broke when the skill was invoked from the project root.

## 1.0.0 - 2026-03-24

Initial public release.
