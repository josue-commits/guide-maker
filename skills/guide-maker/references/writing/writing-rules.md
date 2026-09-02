# Guide Writing Rules

Read these before writing any guide content:
- Full guide spec: `references/writing/guide-spec.md`
- Humanizer filter: `references/writing/humanizer.md`
- Voice/personality: `references/writing/voice.md`
- Example guides matching your detected type (in `references/guides/examples/`)

## Structure
- H1 = title only (one per guide)
- H2 = major sections with emoji prefix
- H3 = subsections, no emoji required
- Code blocks with language tags, copy-paste ready
- Tables for comparisons, pricing, settings
- Callout blockquotes for pro tips, warnings, key insights
- `---` dividers between major sections
- Short paragraphs: 2-4 sentences max

## Tone
- Professional casual, like a knowledgeable friend teaching you
- "You/your" direct address throughout
- Specific over generic (real numbers, named tools, exact steps)
- Active voice, confident statements, no hedging

## Guide Length by Type
- Technical Tutorial: 3,000-9,000 words across all subpages
- Strategic Framework: 1,200-2,000 words
- Comparison/Persuasion: 1,500-3,000 words

## Subpage Structure
Break guides into 4-7 subpages (steps), per `research.depth_gate.min_subpages` and `max_subpages`. Each subpage is a self-contained section stored as a separate markdown file under `workflow.work_dir`. Name files descriptively: `01-getting-started.md`, `02-configuration.md`, etc.
