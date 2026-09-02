# Troubleshooting

Run `python3 <skills>/guide-maker/scripts/doctor.py` first. Most problems below show up there as a FAIL line with the fix.

## Setup

**`config.yaml not found`.** The skill looks in `GUIDE_MAKER_CONFIG`, then `<skill>/config.yaml`, `<skill>/config.json`, then `~/.config/guide-maker/config.yaml`. Run `install.sh` again or copy `config.example.yaml`.

**`PyYAML missing`.** `pip install -r requirements.txt`. Or write `config.json` with the same keys; the loader accepts both.

**Deprecation line about v1 keys.** Your config is the flat v1 shape. It still works. `doctor.py --migrate-config > config.yaml.new` writes the v2 file; review and rename.

**`topic-finder not installed`.** Phase 0 is disabled until it exists next to guide-maker. `git clone https://github.com/josue-commits/topic-finder <skills>/topic-finder`, or run `install.sh` again.

## Notion

**`Could not find database`.** The database is not shared with the integration. Database page, `...`, Connections, add it.

**`Unauthorized`.** Wrong or expired token. Regenerate at notion.so/my-integrations. Check `doctor.py` to see which source the token came from (env var beats key file beats config).

**400 on page create mentioning `language`.** A code fence language outside Notion's enum. v2 normalizes `js`, `sh`, `yml`, `text`, `dockerfile`, `console` and friends. If you hit a new one, add it to `NOTION_CODE_LANG_ALIASES` in `md_to_notion.py` and open an issue.

**`invalid_image_format` on cover upload.** The file is not a PNG or JPEG, or it is over the upload limit. `banner_generator.py` writes PNG; check `--output`.

**A `Page icon:` line shows on a published page.** Directive lines are stripped at conversion in v2. If you published with v1, run `scan_published_leaks.py` to find every affected page, then republish those subpages.

**The public link 404s.** You have not published the page to the web yet. Notion's API cannot do it. Share, Publish, then `md_to_notion.py public-url --page-id <id> --check` turns green.

**`Graphic` property not found.** Add a Files & media property named `Graphic` to the Content Board. See `notion-databases.md`.

## Transcripts and topic research

**yt-dlp finds no subtitles.** The video has no captions. Paste the transcript by hand, or transcribe the audio yourself and paste that.

**`--flat` not supported.** yt-dlp older than 2026.07.04. The scanner falls back to the full scan automatically; upgrade with `pip install -U yt-dlp` for the 6x faster path.

**Scan health FAIL: channels_with_videos below threshold.** One or more channel URLs are wrong or the channel is members-only. `health.json` lists them under `youtube.errors`. Fix the handle in `topic-finder/config/youtube-channels.json`.

**Scan health FAIL: reddit or x returned nothing.** No `APIFY_TOKEN`, or the Apify actor was renamed. The scanner prints the actor slug it called; check it at apify.com and update the config.

**The writer proposed a topic you shipped last month.** It checks Guide DB titles and Content Board keywords. If the old guide is in neither, add the keyword to `excluded_topics` or backfill the Guide DB.

## Copy and DMs

**`lint_copy.py` fails with `keyword-in-copy`.** The keyword is in the post text and `copy.cta_mode` is `graphic`. Remove it; the graphic carries it. If you really want it in the copy, set `cta_mode: copy` and read `strategy.md`.

**`em-dash`.** Replace with a comma, period or colon. This is a hard rule; the humanizer has no switch for it.

**`word-count`.** Outside `copy.words`. Cut or extend, or widen the range in config.

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

## DM tool

**LeadShark 413 on the attachment.** Over 4 MiB. `dm_cli.py image-fit <png>` re-encodes to JPEG under the ceiling. `schedule` does it for you when `attachment_max_bytes` is exceeded.

**LeadShark 403 with a tier note.** The endpoint needs a higher plan. The note says which. The manual adapter always works.

**Scheduled at the wrong hour.** `--time` is ISO with an offset or `Z`. `dm_tool.leadshark.timezone` is only used by the conversion helper; check the printed UTC time in `--dry-run`.

## Agents

**The writer agent returned nothing, or the work vanished.** It spawned a sub-agent and the sub-agent died silently. Every spawn prompt carries "Do NOT spawn sub-agents"; if you edited `SKILL.md`, put that line back.

**`scripts/... No such file`.** Relative path. The orchestrator uses `SKILL_DIR` from `doctor.py --print-paths`; agents must receive absolute paths.
