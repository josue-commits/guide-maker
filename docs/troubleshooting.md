# Troubleshooting

Run the doctor first. Most problems below show up there as a FAIL line with the fix.

```bash
python3 <skills>/make-guide/scripts/doctor.py
```

`<skills>` is wherever your skills were installed (`.claude/skills/` in the project, or a user-level folder). `doctor.py --print-paths` prints every path it resolved, including `config_source`, the step in the search order that found your config.

## Setup

**`config not found`.** The loader looks in five places, in order: an explicit `--config` path, `$GUIDE_MAKER_CONFIG`, `.guide-maker/config.yaml` in the current folder or any parent, `~/.config/guide-maker/config.yaml`, and finally the v2 location inside the skill folder. Run `/setup-guide-maker`, or `doctor.py --init` to write the skeleton by hand. `config.json` with the same keys works everywhere `config.yaml` does.

**Config found in the skill folder (deprecated).** One stderr line tells you the config was loaded from inside `make-guide/`. It works for this release and stops working in the next major. Move it: `doctor.py --init --from <skills>/make-guide/config.yaml` copies the config, the usage log, the topic-finder lists and any voice file you edited into `.guide-maker/`. Or run `/setup-guide-maker`, which offers the move as its first question.

**`npx skills update` replaced my edits.** Anything you changed inside a skill folder (a voice file, a config, a format card) was overwritten, because the update replaces the folder. Edits go in `.guide-maker/`: `voice.md`, `examples.md`, `top-performers.md`, `topic-finder/*.json`, `formats/`. [customizing.md](./customizing.md) maps every v2 "edit `references/...`" instruction to its override.

**`/make-guide` not found (it used to be `/guide-maker`).** The skill was renamed in v3 and there is no redirect. Re-run `npx skills@latest add josue-commits/guide-maker` (or `install.sh`) and pick `make-guide`. If both `/guide-maker` and `/make-guide` show up, you installed through both routes or kept a v2 copy next to the v3 one; delete the old folder.

**`PyYAML missing`.** `pip install pyyaml pillow`. Or write `config.json` with the same keys; the loader accepts both.

**Deprecation line about v1 keys.** Your config is the flat v1 shape. It still works. `doctor.py --migrate-config > config.yaml.new` writes the v2 file; review and rename. This is a different line from the one about the skill-folder location above; you can hit both on an old install.

**`topic-finder not installed`.** In v3 it ships inside this repo, so the only way it is missing is that the installer let you pick skills and you did not pick it. Re-run the install and select it. `doctor.py --print-paths --json` lists every sibling it can see under `siblings`.

**Which database is which.** `doctor.py --list-databases` prints every database your integration can see, with its title and id, so you never paste a 32-character id by hand. If it prints nothing, the databases are not shared with the integration yet.

## Notion

**`Could not find database`.** The database is not shared with the integration. Database page, `...`, Connections, add it.

**`Unauthorized`.** Wrong or expired token. Regenerate at notion.so/my-integrations. Check the doctor to see which source the token came from (env var beats key file beats config).

**400 on page create mentioning `language`.** A code fence language outside Notion's enum. `js`, `sh`, `yml`, `text`, `dockerfile`, `console` and friends are normalized. If you hit a new one, add it to `NOTION_CODE_LANG_ALIASES` in `md_to_notion.py` and open an issue.

**`invalid_image_format` on cover upload.** The file is not a PNG or JPEG, or it is over the upload limit. `banner_generator.py` writes PNG; check `--output`.

**A `Page icon:` line shows on a published page.** Directive lines are stripped at conversion since v2. If you published with v1, run `scan_published_leaks.py` to find every affected page, then republish those subpages.

**The public link 404s.** You have not published the page to the web yet. Notion's API cannot do it. Share, Publish, then `md_to_notion.py public-url --page-id <id> --check` turns green.

**`Graphic` property not found.** Add a Files & media property named `Graphic` to the Content Board. See [notion-databases.md](./notion-databases.md).

## Transcripts and topic research

**yt-dlp finds no subtitles.** The video has no captions. Paste the transcript by hand, or transcribe the audio yourself and paste that.

**`--flat` not supported.** yt-dlp older than 2026.07.04. The scanner falls back to the full scan automatically; upgrade with `pip install -U yt-dlp` for the faster path.

**Scan health FAIL: channels_with_videos below threshold.** One or more channel URLs are wrong or the channel is members-only. `health.json` lists them under `youtube.errors`. Fix the handle in `.guide-maker/topic-finder/youtube-channels.json`.

**Scan health FAIL: reddit or x returned nothing.** No `APIFY_TOKEN`, or the Apify actor was renamed. The scanner prints the actor slug it called; check it at apify.com and update `.guide-maker/topic-finder/subreddits.json` or `x-accounts.json`.

**The writer proposed a topic you shipped last month.** It checks Guide DB titles and Content Board keywords. If the old guide is in neither, add the keyword to `excluded_topics` or backfill the Guide DB.

## Copy and DMs

**`lint_copy.py` fails with `keyword-in-copy`.** The keyword is in the post text and `copy.cta_mode` is `graphic`. Remove it; the graphic carries it. If you really want it in the copy, set `cta_mode: copy` and read [strategy.md](./strategy.md).

**`em-dash`.** Replace with a comma, period or colon. This is a hard rule; the humanizer has no switch for it.

**`word-count`.** Outside `copy.words`. Cut or extend, or widen the range in config.

**`rotation` says a closer repeated.** The same value line ended the post three weeks running (`copy.closer_rotation_weeks`). Pick another from `copy.closers`. The log it reads is `.guide-maker/state/closer-log.jsonl`.

**`name-tag` on a DM.** `{name}` or `[Name]` reaches the lead as literal text. Use `dm.merge_tag` (`{{firstName}}` for LeadShark).

**`hard-wrap` on a DM.** A paragraph has internal line breaks. LinkedIn wraps again and it looks like a broken paste. One paragraph per line.

**`public-url` on a DM.** The guide link is `app.notion.com` or a workspace `notion.so` link. Use the `notion.public_domain` URL.

## Graphics

**`graphics.provider is none: use the card subcommand`.** You called `scene`, `text` or `single` without a provider. Either set `graphics.provider` and a key, or use `graphics_generate.py card` (Pillow, free).

**Text in the generated graphic is fuzzy or misspelled.** That is why the two-pass split and the Pillow bar exist. Shorten the text, quote it exactly in the prompt, or let `cta_bar.py` typeset the bar (`graphics.cta_bar.renderer: pillow`).

**The text pass changed the scene.** Reference-conditioned generation, not masked inpainting. Tighten "change nothing outside the text zones" in the prompt; if a format keeps drifting, use `single`.

**LinkedIn still badges the image as AI-generated.** `finalize` strips C2PA by default. If you passed `--no-strip`, do not. If the badge persists on a stripped file, run `strip_credentials.py --scan <file>` and open an issue with the output.

**A stranger's logo, headshot or app icons appeared in the scene.** Name what you do not want in `graphics.negative_prompt_extra` ("no third-party wordmark, no author photo, no app-icon strip").

**`cta_bar.py` refuses the keyword.** Keywords are `[A-Z]{3,12}`: one word, capitals, derived from the guide name. `ENGINE`, not `Lead-Engine`.

**`ingest_reference.py` wrote the card somewhere I did not expect.** `.guide-maker/formats/` in your project. It stopped writing into the skill's format library in v3.

## DM tool

**LeadShark 413 on the attachment.** Over 4 MiB. `dm_cli.py image-fit <png>` re-encodes to JPEG under the ceiling. `schedule` does it for you when `attachment_max_bytes` is exceeded.

**LeadShark 403 with a tier note.** The endpoint needs a higher plan. The note says which. The manual adapter always works.

**Scheduled at the wrong hour.** `--time` is ISO with an offset or `Z`. `dm_tool.timezone` is only used by the checklist; check the printed UTC time in `--dry-run`.

## Agents

**The writer agent returned nothing, or the work vanished.** It spawned a sub-agent and the sub-agent died silently. Every spawn prompt carries "Do NOT spawn sub-agents"; if you edited `SKILL.md`, put that line back.

**`scripts/... No such file`.** Relative path. The orchestrator uses the paths from `doctor.py --print-paths`; agents must receive absolute paths.

**Something changed under `skills/` after a run.** That is a bug, not a feature: nothing writes there at run time. `git status --porcelain skills/` shows what moved; open an issue with the list.
