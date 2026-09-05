# How to Set Up an AI Email Assistant

This is a structural example showing the formatting patterns for a Technical Tutorial guide section. Use this as a reference for spacing, code blocks, tables, callouts, and header hierarchy.

---

## ⚙️ Step 3: Configure Your Email Integration

Before the AI assistant can read and respond to emails, you need to connect it to your inbox and set up the processing rules.

### Connect your email provider

Head to the Integrations tab in your dashboard and select your email provider. The setup looks slightly different depending on which one you use.

```json
{
  "provider": "google_workspace",
  "credentials": {
    "client_id": "YOUR_CLIENT_ID_HERE",
    "client_secret": "YOUR_CLIENT_SECRET_HERE",
    "redirect_uri": "https://your-app.com/oauth/callback"
  },
  "settings": {
    "folders_to_monitor": ["INBOX"],
    "auto_label": true,
    "label_prefix": "AI-Processed"
  }
}
```

The `folders_to_monitor` array controls which folders the assistant watches. Start with just INBOX. You can add more later once you've confirmed everything works.

### Set up processing rules

Not every email should get an AI response. You need filters.

| Rule | Action | Example |
|------|--------|---------|
| From known client domain | Auto-draft reply | @acmecorp.com |
| Contains "unsubscribe" link | Skip entirely | Marketing emails |
| Flagged as urgent | Draft + notify you | Subject contains "URGENT" |
| From unknown sender | Classify first | New leads, cold emails |
| Internal team email | Skip | @yourcompany.com |

> 💡 **Pro Tip:** Start with conservative rules. Have the assistant draft replies for review instead of sending automatically. Once you trust its judgment on a category (usually after 50-100 emails), upgrade that rule to auto-send.

### Test the connection

Run a quick test to make sure everything is wired up:

```bash
# Send a test email to your monitored inbox
echo "Test email for AI assistant" | mail -s "Test Subject" your-email@company.com

# Check the processing log (wait 30-60 seconds)
curl -H "Authorization: Bearer YOUR_API_KEY_HERE" \
  https://api.your-tool.com/v1/logs/recent
```

Expected output:

```json
{
  "status": "processed",
  "email_id": "msg_abc123",
  "classification": "test",
  "action_taken": "draft_created",
  "confidence": 0.94
}
```

If you see `"status": "processed"`, the connection is working. If you get `"status": "error"`, check that your OAuth credentials haven't expired. The most common issue is a stale refresh token.

> ⚠️ **Warning:** Never set auto-send on emails going to external contacts during your first week. Keep everything in draft mode until you've reviewed at least 50 AI-generated responses and confirmed the tone matches your expectations.

### What you should see after setup

Once the integration is live, your dashboard will show:
- ✅ Connection status (green = active)
- ✅ Emails processed in the last 24 hours
- ✅ Draft responses waiting for your review
- ✅ Auto-sent responses (if any rules allow it)

The assistant processes new emails within 60 seconds of arrival. Drafts appear in a dedicated "AI Drafts" folder in your inbox, tagged with the confidence score so you can quickly scan which ones need editing.
