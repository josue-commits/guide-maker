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
- **Full-page screenshots look zoomed out:** Never use `page.screenshot()` for the whole page. Use `element.screenshot()` on the specific element.
- **Element not found:** Use `page.$$('img')` to list all images first, then pick the right index. Check `naturalWidth > 200` to filter out icons.
- **Image is blurry or too small:** Try a larger viewport (`{ width: 1920, height: 1080 }`) or screenshot the parent container instead.
- **dev-browser server won't start:** Run `./skills/dev-browser/server.sh &` and wait for `Ready`. If Playwright isn't installed, run `npx playwright install chromium` first.

## Content Board entries
- **Curl fails with parentheses:** zsh interprets parentheses. Use /tmp/ JSON files for complex payloads instead of inline curl.
- **Toggle blocks not rendering:** Ensure toggle headings use `is_toggleable: true` and children are nested inside the heading block.
