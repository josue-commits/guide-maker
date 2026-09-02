# Step 2: Run It and Read the Digest

<!-- icon: 📬 -->

The second subpage. Shorter, with a numbered list, a checklist and a warning callout.

## 🚀 Run the daemon

1. Start it: `inbox-rules run --daemon`
2. Wait for the first pass (about 90 seconds on a 2,000-message inbox)
3. Open the `reply_today` label and read the drafts

## ✅ What to check on day one

- [ ] Every client email landed in `reply_today`
- [ ] No newsletter landed in `reply_today`
- [ ] The digest arrived at 6 pm with the archive count

> ⚠️ **Warning:** If a client domain is missing from the rule file, their email goes to archive and you will not see it until the digest. Add every client domain before the first run.

## 📊 The digest

```json
{
  "date": "2026-09-01",
  "reply_today": 6,
  "read_this_week": 12,
  "archived": 23,
  "drafts_created": 6,
  "drafts_sent": 0
}
```

→ Next: tune the `read_this_week` rules once you have a week of data.
