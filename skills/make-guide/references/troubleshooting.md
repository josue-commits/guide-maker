# Troubleshooting

## yt-dlp transcript extraction
- **Auto-subs unavailable:** Try `--write-sub` instead of `--write-auto-sub`
- **No subtitles at all:** Ask the user to paste the transcript manually or find an alternative source
- **Garbled transcript:** Auto-generated subs can be messy. Clean up before classifying.

## Notion API errors
- **Rich text too long:** The API limits rich_text to 2000 characters per text object. `md_to_notion.py` handles splitting automatically, but if using raw API calls, split manually.
- **Too many blocks:** Maximum 100 blocks per append request. The script batches automatically.
- **Block append fails:** Check that the parent page ID is correct and that the API key has write access.

## Banner generation
- **invalid_image_format:** The reference image is SVG. KieAI only accepts PNG. Search for a PNG version of the logo.
- **AI generation fails:** The script falls back to a simple Pillow banner automatically. The fallback always works.
- **Bad logo placement:** Be specific about layout in the prompt ("left side", "right side", "centered below text").

## Screenshots
- **Full-page screenshots look zoomed out:** Never capture the whole page. Capture the specific element.
- **Element not found:** List all images on the page first (any browser automation tool can enumerate `img` elements), then pick the right one. Filter out icons by natural width (anything under 200px is decoration).
- **Image is blurry or too small:** Try a larger viewport (`{ width: 1920, height: 1080 }`) or screenshot the parent container instead.

## Content Board entries
- **Curl fails with parentheses:** zsh interprets parentheses. Use /tmp/ JSON files for complex payloads instead of inline curl.
- **Toggle blocks not rendering:** Ensure toggle headings use `is_toggleable: true` and children are nested inside the heading block.

## Config
- **`Config not found`:** There is no `.guide-maker/config.yaml` in the working directory or any parent, nothing in `~/.config/guide-maker/`, and `GUIDE_MAKER_CONFIG` is unset. Run `/setup-guide-maker`, or `python3 {SKILL_DIR}/scripts/doctor.py --init --project /path/to/your/project`. `config.json` with the same keys works when PyYAML is not installed.
- **`config inside the skill folder is deprecated`:** A v2 config still sits in the skill folder. It keeps loading. Move it with `doctor.py --init --project /path/to/project --from /path/to/that/config.yaml`, which also carries the usage log, topic-finder lists and any edited references. Delete the old file when the doctor is green.
- **Which config is in use?** `doctor.py --print-paths --json` prints `config_path` and `config_source` (`arg`, `env`, `project`, `home`, `legacy`, `none`). Every command should get `--config` set to that `config_path`.
- **The writer ignores my voice / examples / banned words:** Overrides live in `<project>/.guide-maker/` as `voice.md`, `examples.md`, `top-performers.md`, `banned-words.md`. Editing files under `references/` is lost on the next skill update. The doctor's `resources` lines show which file is in use.
- **Topic scan says `config_present: false`:** The source lists live in `<project>/.guide-maker/topic-finder/` (`youtube-channels.json`, `subreddits.json`, `x-accounts.json`, `topics.json`); `doctor.py --init` seeds them from the examples. Pass `--config-dir` to `scan_all.py` with that folder.
- **`unrecognized arguments`:** Run the script with `--help`. Every script documents its real flags; the docs in `references/` and `SKILL.md` match them.
- **Fonts look wrong on the cover:** The bundled Inter font in `assets/fonts/` is used unless `brand.fonts.*` points somewhere else. If you see a bitmap font, the assets folder is missing.
