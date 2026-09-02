# Hub Page Layout

The main/hub page for every guide follows this exact block structure. This is the canonical format for all guide hub pages.

---

## Block Order (Top to Bottom)

### 1. Community Callout (FIRST, only when `community.url` is set)
Highest priority CTA when you have a community. Skipped entirely otherwise.

```
Callout block:
  Icon: 💬
  Text: community.callout_line, e.g. "Join 100+ people automating their inbox: "
  Link: community.name (bold) -> community.url
```

Keep the count in `callout_line` honest and bump it as the community grows; never let it read smaller than reality.

### 2. Guide Description Callout
One-sentence summary of what the reader will learn/build.

```
Callout block:
  Icon: 🚀
  Text: "[Description of the guide and what it delivers]"
```

### 3. Author Byline
Gray paragraph. The name links to `author.linkedin_url`.

```
Paragraph:
  "By " (gray) + author.name (bold, gray, linked to author.linkedin_url)
```

### 3b. Secondary-Channel Credit Line (only when `secondary_channel.url` is set)
Directly under the byline, same gray, understated. It is a credit, not a second CTA: it must not compete with the community callout and it never says "Subscribe!".

```
Paragraph:
  secondary_channel.credit_line (gray), e.g. "YouTube: " + secondary_channel.handle (bold, gray, linked to secondary_channel.url)
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
H2 with emoji: "📚 Sources"

Then for each source:
```
Paragraph: "→ " + "[Source type]: [Title]" (linked to URL)
```

**Creator videos are never sources. Institutional lectures are.** Full policy in `references/research/sources-policy.md`. The reader sees official docs, changelogs, repos, blog posts, and first-party or institutional talks. `publish_guide_hub.py` refuses `--source "youtube|..."` unless `sources.cite_creator_videos` is true, and accepts `institutional` as a type.

When the guide rests on an institutional lecture, say so in the body (institution and role, not the speaker's name) and link it here as the optional deep-dive.

**No cross-guide references anywhere on the page.** Readers arrive cold from one post. Gap analysis stays in the agent's return block.

### 15. Final Divider

---

## Rules

1. **No Index section.** Child pages display automatically in Notion. Don't duplicate them as manual links.
2. **No footer.** Author byline at the top is enough. No "Built by" or "Questions? DM me" at the bottom.
3. **Community CTA first.** If `community.url` is set, always above the guide description callout, never below. Otherwise skip the block entirely. Same for the credit line: present only with `secondary_channel.url`.
4. **Page icon.** Set a relevant emoji as the page icon (e.g., 🛠️ for a tools guide, 🤖 for an AI guide).
5. **Subpage icons.** Each subpage gets an emoji icon matching its step emoji.
6. **Cover image.** Generated via `scripts/banner_generator.py` and uploaded automatically as the page cover. See `references/banner-guide.md` for prompt templates, logo workflow, and style rules.

---

## Notion API Notes

- Hub page is created first with empty children (so it gets its page ID)
- Subpages are created next (they need the hub page ID as parent)
- Hub content is appended last (it needs subpage URLs for the step links)
- Use `scripts/publish_guide_hub.py` which handles this three-phase process automatically
