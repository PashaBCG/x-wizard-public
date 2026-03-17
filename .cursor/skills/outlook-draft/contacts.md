# My Contacts

Add names and email addresses here so X-Wizard can resolve names automatically when drafting emails.

**Format:** `First Last | email@bcg.com | Optional notes`

---

<!-- Add your contacts below this line -->

---

## Auto-populate from Outlook history (Mac only)

Run this command to extract your top 100 most-emailed contacts automatically:

```bash
python .cursor/skills/outlook-draft/scripts/extract_top_contacts.py --top 100 --out .cursor/skills/outlook-draft/contacts.md
```

This reads your local Outlook database — no data leaves your machine.
