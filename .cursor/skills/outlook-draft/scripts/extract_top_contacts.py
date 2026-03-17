"""
Parse Outlook.sqlite to extract top N most-contacted email addresses.
Counts appearances across: To, CC, BCC (received) + To, CC (sent by you).

Reads the current user's email from .cursor/rules/project.mdc to filter out self.
Falls back to prompting if project.mdc is not yet configured.

Usage: python3 extract_top_contacts.py [--top 100] [--out contacts.md]
Note: Mac only (reads Outlook local SQLite database)
"""

import argparse
import re
import sqlite3
import sys
from collections import Counter
from pathlib import Path

OUTLOOK_DB = (
    Path.home()
    / "Library/Group Containers/UBF8T346G9.Office/Outlook"
    / "Outlook 15 Profiles/Main Profile/Data/Outlook.sqlite"
)
EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")


def read_user_email_from_mdc() -> str:
    """Read user email from project.mdc to use as self-filter."""
    mdc_path = Path(".cursor/rules/project.mdc")
    if not mdc_path.exists():
        return ""
    text = mdc_path.read_text(encoding="utf-8")
    m = re.search(r"^- Email:\s*(.+)", text, re.MULTILINE)
    if not m:
        return ""
    email = m.group(1).strip()
    if email.startswith("["):  # unconfigured placeholder
        return ""
    return email


def build_self_pattern(user_email: str) -> re.Pattern:
    """Build a regex pattern to filter out the user's own emails."""
    if user_email and "@" in user_email:
        username = user_email.split("@")[0]
        return re.compile(re.escape(username), re.IGNORECASE)
    # Fallback: won't filter anything — user can manually clean contacts.md
    return re.compile(r"^$")  # never matches


def parse_addresses(raw: str) -> list[str]:
    if not raw:
        return []
    return [e.lower().strip() for e in EMAIL_RE.findall(raw)]


def extract_top_contacts(top_n: int, self_pattern: re.Pattern) -> list[tuple[str, int]]:
    if not OUTLOOK_DB.exists():
        raise FileNotFoundError(
            f"Outlook database not found at:\n  {OUTLOOK_DB}\n\n"
            "This script only works on macOS with Outlook installed."
        )

    conn = sqlite3.connect(OUTLOOK_DB)
    cur = conn.cursor()
    cur.execute("""
        SELECT
            Message_SenderAddressList,
            Message_ToRecipientAddressList,
            Message_CCRecipientAddressList
        FROM Mail
        WHERE Message_MarkedForDelete = 0
    """)

    counter: Counter = Counter()
    for sender_raw, to_raw, cc_raw in cur.fetchall():
        all_addresses = (
            parse_addresses(sender_raw)
            + parse_addresses(to_raw)
            + parse_addresses(cc_raw)
        )
        for addr in all_addresses:
            if self_pattern.search(addr):
                continue
            if "@" not in addr or "noreply" in addr or "no-reply" in addr:
                continue
            counter[addr] += 1

    conn.close()
    return counter.most_common(top_n)


def format_markdown(contacts: list[tuple[str, int]]) -> str:
    lines = [
        "# My Contacts",
        "",
        "Extracted from Outlook local database. Use these in email drafts by name or partial match.",
        "",
        "| # | Email | Count |",
        "|---|-------|-------|",
    ]
    for i, (email, count) in enumerate(contacts, 1):
        lines.append(f"| {i} | {email} | {count} |")
    return "\n".join(lines)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Extract top contacts from Outlook (Mac only)"
    )
    parser.add_argument("--top", type=int, default=100, help="Number of contacts to extract")
    parser.add_argument(
        "--out", type=str,
        default=".cursor/skills/outlook-draft/contacts.md",
        help="Output markdown file path",
    )
    args = parser.parse_args()

    user_email = read_user_email_from_mdc()
    if user_email:
        print(f"Filtering out your address: {user_email}")
    else:
        print("Note: user email not found in project.mdc — run /start first to configure.")
        print("Proceeding without self-filter.")

    self_pattern = build_self_pattern(user_email)

    try:
        print("Scanning Outlook database...")
        contacts = extract_top_contacts(args.top, self_pattern)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(contacts)} unique contacts.")

    md = format_markdown(contacts)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(md, encoding="utf-8")
    print(f"Saved to: {out_path}")
