# Guide Type Classification

Read the full source material, then classify into one of four types. Each type has a synthetic example in `references/guides/examples/` that shows the depth, formatting density and tone to match.

## Technical Tutorial
**Signals:** Installation steps, code snippets, terminal commands, API integrations, config files, "first do this, then do that" patterns.
**Example:** `references/guides/examples/technical-tutorial.md`

## Strategic Framework
**Signals:** Methodology, phases, timelines, growth tactics, high-level approach, mental models.
**Example:** `references/guides/examples/strategic-framework.md`

## Comparison/Persuasion
**Signals:** Comparing tools/approaches, cost analysis, before/after, ROI discussions, "why X beats Y."
**Example:** `references/guides/examples/comparison.md`

## Use-case Stack
**Signals:** Several small reusable pieces (agent skills, prompt files, configs, scripts) bundled around one professional role. "Here are the five things a recruiter / marketer / ops lead installs." Each subpage ships one piece with its trigger, its file and a test.
**Example:** `references/guides/examples/use-case-stack.md`

The Guide Database `Type` select must contain every type you use. Add "Use-case Stack" to the select in Notion before publishing one, or the page create fails with an unknown option.

## Detection Process
1. Read the full source before classifying
2. If mixed, default to the type that covers 60%+ of the content
3. Present to the user: "This looks like a **[Type Name]**. Here's my planned outline:" and wait for confirmation
