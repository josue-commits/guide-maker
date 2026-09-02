# Changelog

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
