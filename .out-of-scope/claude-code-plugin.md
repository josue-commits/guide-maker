# A Claude Code plugin

This repo ships no `.claude-plugin/plugin.json`, no marketplace entry and no Codex plugin manifest. Requests to add one are out of scope for now.

## Why

The decision and the trade-offs are recorded in [ADR 0002](../.agents/adr/0002-distribute-through-skills-sh-and-install-sh-no-plugin.md). In short: a plugin buys namespaced names and auto-update, and costs a config story for a read-only folder, a marketplace, and a version sync, while giving Codex nothing. Two routes that write editable files into the project cover every harness today.

## What to do instead

- `npx skills@latest add josue-commits/guide-maker`, then `npx skills update` when you want the latest.
- `git clone` and `./install.sh <project>` without Node.

## Revisit when

The triggers are listed at the end of the ADR. Open an issue that names one of them.
