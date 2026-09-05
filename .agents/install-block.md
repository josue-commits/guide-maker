# The canonical install block

One install story, one wording. `README.md` carries the block below byte for byte between `<!-- install-block:start -->` and `<!-- install-block:end -->`; `.github/workflows/docs.yml` extracts the two and fails on any difference. Change it here first, then paste it into the README. Pages under `docs/` carry no install commands of their own (see [writing-docs.md](./writing-docs.md)); they link to the README.

## Two routes, exclusive

- **skills.sh**: `npx skills@latest add josue-commits/guide-maker`. The recommended route for Claude Code, Codex and every other agent that reads the Agent Skills layout. The CLI copies editable skill files into the project and `npx skills update` refreshes them. It needs Node.
- **`install.sh`** from a clone: the same six skill folders copied into `<project>/.claude/skills/`, no Node at all. Re-running it after `git pull` is the update path.

Both routes put the same six skills in the project. Installing through both leaves every skill twice, so the block always says "pick one".

Why there is no Claude Code plugin route: [adr/0002](./adr/0002-distribute-through-skills-sh-and-install-sh-no-plugin.md).

## The block

Everything between the markers is what the README carries.

<!-- install-block:start -->
Two ways in, one result: six skills in your project, as files you own. **[skills.sh](https://skills.sh/josue-commits/guide-maker)** copies them in and updates them with one command; it needs Node. **`install.sh`** does the same from a clone, with no Node. Pick one: installing both leaves every skill twice.

### 1. Get the skills

<details>
<summary><strong>Claude Code, Codex and other agents</strong></summary>

```bash
npx skills@latest add josue-commits/guide-maker
```

The installer lets you choose which skills to take. Take all six, or at least `setup-guide-maker` and `make-guide`. Then the two Python dependencies:

```bash
pip install pyyaml pillow
```

Update later with `npx skills update`.

</details>

<details>
<summary><strong>No Node</strong></summary>

```bash
git clone https://github.com/josue-commits/guide-maker.git
cd guide-maker && ./install.sh /path/to/your/project
pip install pyyaml pillow
```

`install.sh` copies the six skills into `/path/to/your/project/.claude/skills/`. Re-run it after `git pull` to update.

</details>

### 2. Run `/setup-guide-maker`

In your agent, inside the project, once. It asks about your Notion databases (picked from a list, never pasted as ids), your name and LinkedIn URL, your community and secondary channel, your DM tool, your image provider and your topic sources. It writes `.guide-maker/` in the project and an `## Agent skills` block in your `CLAUDE.md` or `AGENTS.md`, then runs the doctor and stops only when every line is green.

### 3. Say it

```
make a guide from this video: <url>
make a guide about <topic>, here is the transcript: <paste>
find me a topic
```

Bam. The skill runs the pipeline, stops for your approval at the outline and again at the content, and hands you the bundle.
<!-- install-block:end -->

## Spelling rules

- `skills@latest` is the pinned spelling. Never a bare `npx skills add`.
- `pip install pyyaml pillow`, not `-r requirements.txt`: the skills.sh route does not ship the requirements file.
- The setup step is `/setup-guide-maker`, run once per project, before the first guide.
- The three entry sentences are the ones `ask-guide-maker` and `setup-guide-maker` print. Change them in all three places or in none.
