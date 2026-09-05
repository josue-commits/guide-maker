# Distribute through skills.sh and install.sh; no Claude Code plugin

Decision taken by the maintainer on 2026-09-05.

## Context

The reference architecture this repo borrows its onboarding from ships as a Claude Code plugin listed in the official marketplace, with `npx skills` as the route for every other harness. The question was whether to do the same.

## What a plugin would add

- **Namespaced skill names** (`guide-maker:make-guide`), so bare names could not collide with a skill the user already has.
- **Subscribe and auto-update**: a read-only bundle that follows releases without the user running anything.
- **`${CLAUDE_PLUGIN_ROOT}`**, a stable variable for the plugin folder, so `SKILL.md` files could carry absolute-enough script paths without the "resolve `SKILL_DIR` first" preamble.

## What it would cost

- **A config story for a read-only cache.** A plugin's folder cannot hold `config.yaml`, so the `.guide-maker/` move in [0001](./0001-config-lives-in-the-project.md) becomes mandatory before the plugin can exist, and the legacy location can never be offered.
- **A marketplace.** Either an official listing, which is a review process outside this repo's control, or a self-hosted `marketplace.json` that users must add first, which makes the install two commands.
- **Version sync** between `plugin.json`, `VERSION` and the changelog, plus `claude plugin validate --strict` in CI.
- **Codex gets nothing from it.** The Codex plugin manifest takes one skills path and drops symlinks on install; the reference repo deferred its Codex plugin for exactly this reason. `npx skills` would still be the route there.

## Decision

Two routes, both writing editable files into the user's project:

1. `npx skills@latest add josue-commits/guide-maker` for Claude Code, Codex and any harness on the Agent Skills layout. `npx skills update` is the update path.
2. `git clone` and `./install.sh <project>` for machines without Node.

No plugin manifest, no marketplace, no Codex YAML. Skill names are bare and short (`make-guide`, not `guide-maker:make-guide`), which is why the core skill was renamed: `/make-guide` reads as the action, and `setup-guide-maker` and `ask-guide-maker` keep the suffix because their job is about the set.

## Revisit when

- Users ask for auto-update more than they ask for editable skills.
- A bare name collides with a popular skill in the wild.
- The official marketplace accepts skill-only plugins without a review round trip.

The `.out-of-scope/claude-code-plugin.md` note points here.
