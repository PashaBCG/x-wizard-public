---
name: outlook-draft
description: Compose and save emails as Outlook drafts, or send directly, on macOS or Windows. No API keys or IT approval required. Use when the user asks to draft an email, save a draft, compose a message, write an email, send a note, or send an email directly via Outlook.
---

# Outlook Email Skill (cross-platform)

Two modes — **draft** (default) or **send directly** (only when explicitly requested).
- **macOS** — AppleScript via `osascript`
- **Windows** — `win32com` via Python (`pip install pywin32`)

## Mode selection

| User says | Mode |
|-----------|------|
| "draft", "save draft", "compose" | **Draft** — opens window, user saves manually |
| "send", "send directly", "send straight away" | **Confirm first, then send** — see below |

### Send confirmation (ALWAYS required before sending)

Before firing any `send`, ALWAYS ask:

> "Just to confirm — send this straight away, or open as a draft to review first?"

- If user confirms **send** → proceed with send mode + signature
- If user says **draft** → switch to draft mode, no signature
- Never send without this confirmation, even if the original request said "send"

## Read user details from project.mdc

Before building the signature or resolving contacts, read the user's details from `.cursor/rules/project.mdc`:

```python
import re
import pathlib

mdc_path = pathlib.Path(".cursor/rules/project.mdc")
mdc = mdc_path.read_text(encoding="utf-8")

def _extract(pattern: str, text: str, default: str = "") -> str:
    m = re.search(pattern, text)
    return m.group(1).strip() if m else default

user_name  = _extract(r"^- Name:\s*(.+)", mdc, fallback="[Your Name]")
user_email = _extract(r"^- Email:\s*(.+)", mdc, fallback="")
user_phone = _extract(r"^- Phone:\s*(.+)", mdc, fallback="")
```

If `user_name` contains `[run /start` (i.e. not yet configured), ask the user to run `/start` first.

## Workflow

1. Extract from user input: `to`, `subject`, `body`, and optionally `cc`, `bcc`
2. Resolve any names to email addresses using [contacts.md](contacts.md) — match on first name, last name, or partial
3. Convert body to clean HTML (preserve paragraphs, apply bold for numbered points/headers)
4. **Draft mode**: do NOT add signature (Outlook auto-appends it)
5. **Send mode**: append the signature block (see below) — Outlook won't add it automatically

## HTML body rules

- Wrap entire body in `<html><body style='font-family: Calibri, sans-serif; font-size: 11pt;'>`
- Each paragraph → `<p>...</p>`
- Line breaks within a paragraph → `<br>`
- Numbered items (1/, 2/, etc.) or section headers → wrap label in `<b>...</b>`
- Escape `&` as `&amp;` in body text

## Signature (send mode only)

Read the logo and user details, then build the signature block in Python:

```python
import base64
import pathlib

logo_path = pathlib.Path(".cursor/skills/outlook-draft/bcgx-logo.png")

if logo_path.exists():
    with open(logo_path, "rb") as f:
        logo_b64 = base64.b64encode(f.read()).decode()
    logo_html = f"<div style='margin-top: 8px;'><img src='data:image/png;base64,{logo_b64}' width='80' style='display:block;'></div>"
else:
    logo_html = ""

phone_html = f"<div style='color: #666;'>{user_phone}</div>" if user_phone else ""

signature = f"""<br>
<div style='font-family: Calibri, sans-serif; font-size: 9pt; color: #999; font-style: italic; margin-bottom: 6px;'>Generated and sent via X-Wizard</div>
<hr style='border: none; border-top: 1px solid #ccc; margin: 8px 0;'>
<table style='font-family: Calibri, sans-serif; font-size: 10pt; color: #333; border-collapse: collapse;'>
  <tr><td style='vertical-align: top;'>
    <div style='font-weight: bold; font-size: 11pt;'>{user_name}</div>
    {phone_html}
    {logo_html}
  </td></tr>
</table>"""
```

Append `signature` to the HTML body before passing to AppleScript/win32com.

## macOS — Draft (AppleScript)

```applescript
tell application "Microsoft Outlook"
    set htmlBody to "<html>...</html>"
    set newDraft to make new outgoing message with properties {subject:"SUBJECT", content:htmlBody}
    make new recipient at newDraft with properties {email address:{address:"TO"}}
    make new cc recipient at newDraft with properties {email address:{address:"CC"}}
    open newDraft
    -- window opens pre-filled; user hits Cmd+W → Save → lands in Exchange Drafts
end tell
```

## macOS — Send directly (AppleScript)

```applescript
tell application "Microsoft Outlook"
    set htmlBody to "<html>...BODY + SIGNATURE...</html>"
    set newMsg to make new outgoing message with properties {subject:"SUBJECT", content:htmlBody}
    make new recipient at newMsg with properties {email address:{address:"TO"}}
    send newMsg
end tell
```

## Windows — Draft (win32com)

```python
import win32com.client
outlook = win32com.client.Dispatch("Outlook.Application")
draft = outlook.CreateItem(0)
draft.Subject = "SUBJECT"
draft.HTMLBody = "<html>...</html>"  # no signature
draft.To = "recipient@bcg.com"
draft.Save()  # saves to Drafts silently — do NOT call .Send()
```

## Windows — Send directly (win32com)

```python
draft.HTMLBody = "<html>...BODY + SIGNATURE...</html>"
draft.Send()  # sends immediately
```

## What NOT to do

- Draft mode: do NOT add signature — Outlook auto-appends it, adding it here duplicates it
- macOS draft: do not use `save newDraft` — errors; do not omit `open newDraft` — message lands in local Drafts only
- Send mode: do NOT call `open` — fires the window; use `send` directly
- Do not attempt Graph API or MSAL auth — blocked by BCG conditional access (error 53003)

## Contact extraction (optional)

To auto-populate `contacts.md` from your Outlook history (Mac only):

```bash
python .cursor/skills/outlook-draft/scripts/extract_top_contacts.py --top 100 --out .cursor/skills/outlook-draft/contacts.md
```
