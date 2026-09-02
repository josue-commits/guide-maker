# Step 1: Set Up the Rule File

**Page icon:** 🛠️

This subpage exists to exercise the markdown converter. It carries every code fence alias the converter has to normalize, an authoring directive above (which must never render), and a paragraph below that starts with the word "Icons" and must survive.

Icons: here is why they matter for scannability. A reader skimming on a phone sees the emoji before the heading text, so the emoji has to say what the section is about.

## ⚙️ Install the client

```sh
pip install inbox-rules
inbox-rules init --provider gmail
```

```console
$ inbox-rules doctor
config: ok
token:  ok
```

## 📋 Write the rule file

```yml
queues:
  reply_today:
    match: ["from:client", "subject:urgent"]
  read_this_week:
    match: ["list:newsletter"]
  archive:
    match: ["*"]
draft_reply:
  queue: reply_today
  send: false
```

## 🔧 Wire the draft step

```js
export async function draft(email, rules) {
  const queue = rules.route(email);
  if (queue !== "reply_today") return null;
  return rules.draft(email, { send: false });
}
```

```dockerfile
FROM python:3.12-slim
RUN pip install inbox-rules
CMD ["inbox-rules", "run", "--daemon"]
```

```text
Expected output:
routed 41 emails: 6 reply_today, 12 read_this_week, 23 archive
drafted 6 replies, sent 0
```

```
This bare fence has no language tag and must come out as plain text.
```

> 💡 **Pro Tip:** Keep `send: false` for the first week. Read fifty drafts before you let it send one.

| Queue | Rule | Volume on day one |
|-------|------|-------------------|
| reply_today | client domains, urgent subjects | 6 |
| read_this_week | newsletters, digests | 12 |
| archive | everything else | 23 |
