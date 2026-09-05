# Per-user writing preferences in config.yaml

`config.yaml` holds facts about the operation: databases, names, channels, tools, gates, word range. It does not hold instructions about tone, sentence length, humour, or how the writer should react to feedback. Requests to add keys like `tone:`, `formality:` or `avoid_phrases_like:` are out of scope.

## Why

- Voice is prose, not enums. Every attempt to encode it as keys produces a worse voice than three paragraphs written by the operator.
- The config is read by scripts. A key nobody's code reads is documentation pretending to be configuration, and it drifts.
- The writer already reads free-form voice material at Phase 0.5; adding a second channel for the same information means two places to keep in sync.

## What to do instead

- `.guide-maker/voice.md`: who you sell to, how long your sentences run, words you use, words you never use, whether you swear, your analogies. `/setup-guide-maker` offers to create it from three questions.
- `.guide-maker/examples.md`: five to ten of your real posts, for rhythm and vocabulary.
- `.guide-maker/top-performers.md`: your best posts with their numbers and one line each on why they worked.
- Your project's `CLAUDE.md` or `AGENTS.md`: anything that applies to every skill, in plain instructions.
- `copy.extra_banned_words` is the one exception, because the linter enforces it.
