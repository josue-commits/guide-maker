# Skills

Six skills, flat in this folder. Two ways to reach one: **user-invoked** skills run only when you type their name (`disable-model-invocation: true`, a human-facing description); **model-invoked** skills run when the agent decides they fit or when you name them (a trigger-rich description). A user-invoked skill may call a model-invoked one; nothing can call a user-invoked skill.

## Pipeline

The route from a topic to a published guide and a scheduled post.

User-invoked

- **[setup-guide-maker](./setup-guide-maker/SKILL.md)**: connect the skills to your Notion databases, your name and channels, your DM tool and image provider. Run once per project, before the first guide.
- **[ask-guide-maker](./ask-guide-maker/SKILL.md)**: which skill or step fits where you are in the week. A router; it runs nothing.

Model-invoked

- **[make-guide](./make-guide/SKILL.md)**: turn a YouTube video, a transcript or a researched topic into a multi-page Notion guide plus the lead-magnet bundle around it: three copy variations, a cover, the board card, the DM text. The keyword never appears in the copy, and it never posts or publishes a page to the web.
- **[topic-finder](./topic-finder/SKILL.md)**: scan your YouTube channels, subreddits and X accounts, correlate across sources, and rank topics behind a health gate. A dead source is a stop, never a web-search fallback.

## Assets

The two images-and-delivery skills the pipeline calls at the end, each usable on its own.

Model-invoked

- **[graphics-maker](./graphics-maker/SKILL.md)**: the LinkedIn post graphic with the keyword CTA bar typeset across the bottom and Content Credentials stripped. Free Pillow card by default; two-pass generation through an image provider when you have a key.
- **[dm-automation](./dm-automation/SKILL.md)**: the DM side of the keyword comment: render the versions, lint them, and either write a paste-ready bundle for your own tool (default) or schedule the post with the automation through an adapter.
