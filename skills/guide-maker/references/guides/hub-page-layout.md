# Hub Page Layout

The main/hub page for every guide follows this exact block structure. This is the canonical format for all guide hub pages.

---

## Block Order (Top to Bottom)

### 1. Community Callout (FIRST)
Highest priority CTA. Always the first content block. Only include this block if a community URL is configured in config.yaml.

```
Callout block:
  Icon: 💬
  Text: "Join [MEMBER_COUNT]+ [COMMUNITY_DESCRIPTION]: "
  Link: "[Community Name]" → community URL (from config.yaml, optional) (bold)
```

### 2. Guide Description Callout
One-sentence summary of what the reader will learn/build.

```
Callout block:
  Icon: 🚀
  Text: "[Description of the guide and what it delivers]"
```

### 3. Author Byline
Paragraph with gray text. Links to the author's LinkedIn profile.

```
Paragraph:
  "By " (gray) + "[Author Name]" (bold, gray, linked to LinkedIn URL (from config.yaml))
```

### 4. Empty Line
Paragraph with empty rich_text.

### 5. Child Pages
These render automatically as native Notion child_page blocks. Do NOT create an Index section or manually link to them here. Notion handles this natively.

### 6. Empty Line

### 7. Divider

### 8. What You'll Build
H2 with emoji: "🎯 What You'll Build"
Bulleted list of 4-6 key deliverables/outcomes.

### 9. Who This Is For
H2 with emoji: "👤 Who This Is For"
Bulleted list of 3-5 audience descriptions.

### 10. Empty Line

### 11. Divider

### 12. The Guide
H2 with emoji: "📖 The Guide"

Followed by a navigation callout:
```
Callout block:
  Icon: ⚡
  Text: "[Guidance on where to start, e.g., skip to Step X if you already know Y]"
```

Empty line.

Then for each step (repeat N times):
```
H3: "[emoji] Step N: [Short Title]"
Paragraph: [1-2 sentence description of what this step covers]
Paragraph: "→ " + "Read Step N: [Short Title]" (linked to subpage URL)
Divider (between steps, not after the last one)
```

### 13. Divider (before sources)

### 14. Sources
H2 with emoji: "🎬 Sources"

Paragraph: Brief attribution line.

Then for each source:
```
Paragraph: "→ " + "[Source type]: [Title]" (linked to URL)
```

### 15. Final Divider

---

## Rules

1. **No Index section.** Child pages display automatically in Notion. Don't duplicate them as manual links.
2. **No footer.** Author byline at the top is enough. No "Built by" or "Questions? DM me" at the bottom.
3. **Community CTA first.** If configured, always above the guide description callout, never below. If no community URL is set in config.yaml, skip this block entirely.
4. **Page icon.** Set a relevant emoji as the page icon (e.g., 🛠️ for a tools guide, 🤖 for an AI guide).
5. **Subpage icons.** Each subpage gets an emoji icon matching its step emoji.
6. **Cover image.** Generated via `scripts/banner_generator.py` and uploaded automatically as the page cover. See `references/banner-guide.md` for prompt templates, logo workflow, and style rules.

---

## Notion API Notes

- Hub page is created first with empty children (so it gets its page ID)
- Subpages are created next (they need the hub page ID as parent)
- Hub content is appended last (it needs subpage URLs for the step links)
- Use `scripts/publish_guide_hub.py` which handles this three-phase process automatically
