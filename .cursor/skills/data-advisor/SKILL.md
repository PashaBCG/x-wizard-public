---
name: data-advisor
description: Single data onboarding guide for Excel, Tableau, and Snowflake. Educates non-technical users on file handling, data conversion, access requests, credential setup, and hands off to /create-skill. Use when the user mentions excel, xlsx, spreadsheet, workbook, tableau, snowflake, dashboard, dataset, data source, metrics, reporting data, client view, live data, or asks how to connect to their data.
---

# Data Advisor

A guided skill that helps users connect to their data — whether it's an Excel file on their laptop, a Tableau dashboard, or a Snowflake database. This skill educates, guides access requests, configures credentials, and then hands off to `/create-skill` to build an actual data query skill.

## CRITICAL — Read first

- This skill is an **advisor**. It does not query data itself.
- Adapt all explanations to the user's **AI_LEVEL** from `.cursor/rules/project.mdc`. If not configured, default to L2 (plain English, minimal jargon).
- Follow the phases in order. Do not skip phases unless the plan explicitly says to.
- Ask questions **one at a time**. Never dump all questions at once.

---

## Phase 1 — Detect and Acknowledge

This skill triggers when the user mentions: tableau, snowflake, dashboard, dataset, data source, metrics, reporting data, client view, live data, excel, spreadsheet, xlsx, workbook — or describes a workflow involving any of these.

Open with:

**For L1-L2:**
> "It sounds like you work with data — whether it's an Excel file, a dashboard, or a database. I can help you set things up so you can ask questions about your data in plain English — no code or formulas needed."

**For L3+:**
> "Let's get your data source connected. I'll walk you through setup and then we'll build a query skill around it."

---

## Phase 2 — Discovery Interview and Branching

**Q1** (use AskQuestion):
> "Where does your data live?"
- Excel file on my laptop (or OneDrive/SharePoint synced locally)
- Tableau dashboard (I open it in a browser)
- Snowflake database
- Not sure / something else

**Q2** (free text):
> "What does this data track? What questions do you usually answer with it?"

Wait for both answers before proceeding.

**Branching:**

| Answer | Next phase |
|--------|------------|
| **Excel** | Skip to **Phase 3E** (Excel fast-track) |
| **Tableau** | Continue to **Phase 3** then **Phase 4–7** |
| **Snowflake** | Continue to **Phase 3** then **Phase 4–7** |
| **Not sure** | Ask: "Do you open a website or app to see this data, or is it a file on your computer?" — then branch |

---

## Phase 3 — Education: How Remote Data Connections Work

*This phase is for Tableau and Snowflake only. Excel users skip to Phase 3E.*

Explain in plain English, adapted to AI_LEVEL:

**For L1-L2:**

> "Here's how this works — in simple terms:
>
> Your team already maintains this data and refreshes it on a schedule. X-Wizard will download a cached copy of that data to your laptop — like saving a snapshot. Then you can ask me questions about it in plain English, and I'll look up the answers instantly.
>
> A few important things:
> - **Zero extra work for your team.** They already refresh this data. We're just reading what's already there — like opening the dashboard, but automated.
> - **No risk to the data.** X-Wizard only downloads and reads. It cannot change, delete, or break anything on the server. You get read and download access only — no write access, ever.
> - **Everything stays on your laptop.** Your cached data and login credentials never leave your machine. There's a built-in safety rule that prevents them from being uploaded anywhere."

**For L3+:**

> "X-Wizard downloads a local cache of the dataset via API (PAT for Tableau, credentials for Snowflake). Queries run against the local cache — no live server hits during analysis. Read + download only, no write access. Credentials and cached data stay local (`.env.local` is git-ignored)."

---

## Phase 3E — Excel Fast-Track

*This phase is for Excel users only. No access request or credentials needed.*

### Step 1 — File placement

**For L1-L2:**
> "For X-Wizard to read your Excel file, it needs to be saved on your laptop — in your Documents, Desktop, or inside this project folder. If your file is on SharePoint or OneDrive, that's fine too — most BCG laptops sync those files locally, so they're already on your machine.
>
> X-Wizard uses a built-in connector (think of it like a plug) that can read Excel files directly — but only if they're on your computer, not on a remote website."

**For L3+:**
> "The Excel MCP server reads local files only. OneDrive/SharePoint files work if synced locally. Confirm the file path is accessible from this machine."

Ask the user: "What's the file called, and where is it saved on your laptop?"

### Step 2 — Conversion guidance

**For L1-L2:**
> "Before we start querying your data, I need to convert your Excel file to a simpler format. Here's why:
>
> Excel files contain a lot of hidden complexity — formatting, colors, merged cells, formulas. When AI reads a raw Excel file, all that extra stuff can cause mistakes. By converting to a clean data format first, the answers are much more accurate and faster.
>
> I'll handle the conversion automatically — you don't need to do anything."

**For L3+:**
> "Raw .xlsx carries formatting overhead that causes hallucinations. Converting to CSV or Parquet gives clean tabular data with better query accuracy."

**Conversion rules (apply automatically):**

| File size | Target format | Why |
|-----------|---------------|-----|
| Under 20 MB | CSV | Simpler, human-readable, good for smaller datasets |
| 20 MB and above | Parquet | Compressed, columnar, handles large datasets without memory issues |

**Action:** Write and run a conversion script for the user. The script should:
1. Read the Excel file with `pandas` + `openpyxl` engine
2. Ask the user which sheet to use if there are multiple
3. Drop completely empty columns
4. Cast numeric columns explicitly with `pd.to_numeric(errors="coerce")`
5. Write to CSV or Parquet based on source file size
6. Print a summary: row count, column names, file sizes before/after

Read [reference.md](reference.md) for the extraction script template and best practices.

### Step 3 — Confirm Excel MCP

Check `~/.cursor/mcp.json` for the `excel` entry. If present, confirm:
> "Your Excel connector is already set up. It lets me read your raw .xlsx for quick lookups. For data analysis though, we'll use the converted file — it's faster and more accurate."

If missing, set it up by merging this into `~/.cursor/mcp.json`:
```json
{
  "mcpServers": {
    "excel": {
      "command": "npx",
      "args": ["-y", "excel-mcp-server"],
      "env": {}
    }
  }
}
```
Then tell the user to restart Cursor.

### Step 4 — Hand off to /create-skill

Tell the user:
> "Your data is ready. Now let's build a skill so you can query it anytime by just asking in plain English."

Read `.cursor/skills/create-skill/SKILL.md` and launch the skill creation flow **in this same chat**, pre-loading:
- Data source type: Excel (local file)
- The converted file path (CSV or Parquet)
- The column names and dataset description from the conversion output
- The user's questions from Phase 2
- Pointer to [reference.md](reference.md) for Excel query patterns

**This skill is complete after the handoff. The create-skill flow takes over.**

---

## Phase 4 — Find the Admin and What to Ask

*This phase is for Tableau and Snowflake only.*

### Finding the data owner

**Tableau:**
> "Open the dashboard in your browser. Look at the top for the workbook name, then look for a 'Data Sources' tab — the owner is listed there. If you can't find it, your team lead or the person who built the dashboard will know."

**Snowflake:**
> "Ask your team's data or analytics contact who manages the Snowflake account your reports use. If you're not sure who that is, ask your team lead — they'll know or can point you to the right person."

### What to request — checklist

Present this checklist to the user so they know exactly what to ask for. Tell them to copy or screenshot it.

**Tableau — ask the data source owner for:**

- [ ] Read and download access to the **published data source** (not the workbook — the underlying data). Download is needed to cache the data locally for querying.
- [ ] The **Tableau server URL** (e.g., `https://tableau.yourcompany.com`)
- [ ] The **site name** (visible in the URL after `/site/`)
- [ ] The **data source ID** (from the URL when viewing the data source page, or the admin can share it)

**Snowflake — ask the database admin for:**

- [ ] A **read-only user account** or service account
- [ ] The **account identifier** (e.g., `abc12345.us-east-1`)
- [ ] The **warehouse name** to use for queries
- [ ] The **database and schema names** where the data lives

---

## Phase 5 — Draft Access Request Email

*This phase is for Tableau and Snowflake only.*

Read `.cursor/skills/outlook-draft/SKILL.md` and use it to compose a professional email to the data owner.

The email should include:

**Subject:** "Request: Read & download access to [dataset name] for automated reporting"

**Body structure:**

1. **Who you are and what you need** — one sentence intro referencing the user's name and role from `project.mdc`

2. **Three persuasion points:**
   - "I'm requesting read and download access to data your team already refreshes. This adds zero work to your pipeline — I just need to cache a local copy for automated lookups."
   - "I already have dashboard access to view this data. Download access lets me cache it locally and automate the same lookups I do manually today."
   - "The access is read and download only — no write capability. The data cannot be modified or corrupted. My cached copy stays on my laptop and is never re-uploaded anywhere."

3. **Specific ask** — the checklist items from Phase 4, written as a numbered list of what the recipient needs to provide or enable

4. **Closing** — offer to discuss on a quick call if easier

After drafting, tell the user:
> "I've drafted the email for you. Review it, send it when ready, and come back to this conversation once you have the access details. We'll pick up right where we left off."

---

## Phase 6 — Configure Credentials

*When the user returns with access granted.*

### Step 1 — Explain secrets and .gitignore

**MANDATORY** — always explain this before creating any credential files.

**For L1-L2:**
> "Before we save your credentials, let me explain how this stays secure.
>
> Your passwords and tokens will go into a file called `.env.local` — think of it as a private sticky note on your laptop. This file is listed in something called `.gitignore`, which is a simple rule that tells the system: **never upload this file anywhere.** It stays on your machine only — it won't appear on GitHub, in shared folders, or anywhere else. Even if you sync or share the rest of your project, `.env.local` is automatically excluded.
>
> In short: your credentials live only on your laptop, and there's a built-in safety net that prevents them from accidentally leaking."

**For L3+:**
> "Credentials go in `.env.local` at the workspace root. It's already in `.gitignore` — never committed, never pushed. Local to your machine only."

Then read `.gitignore` and show the user the relevant lines so they can see the safety net with their own eyes.

### Step 2 — Create the credentials file

**Tableau:**

First, guide PAT creation:
> "Go to your Tableau profile (click your avatar in the top-right corner) → Settings → Personal Access Tokens. Create a new token and name it `x-wizard-api`. Copy both the token name and the token secret — you'll need them in the next step."

Then create `.env.local` at the workspace root:
```
TABLEAU_TOKEN_NAME="x-wizard-api"
TABLEAU_TOKEN_SECRET="paste-your-token-secret-here"
```

**Snowflake:**

Create `.env.local` at the workspace root:
```
SNOWFLAKE_ACCOUNT="your-account-id"
SNOWFLAKE_USER="your-username"
SNOWFLAKE_PASSWORD="your-password"
SNOWFLAKE_WAREHOUSE="your-warehouse"
SNOWFLAKE_DATABASE="your-database"
SNOWFLAKE_SCHEMA="your-schema"
```

### Step 3 — Verify

Read `.gitignore` and confirm `.env.local` is listed. Show the user the line. Then say:

**For L1-L2:**
> "Your credentials are saved and protected. The `.gitignore` file confirms that `.env.local` will never be uploaded anywhere. You're all set."

**For L3+:**
> "`.env.local` created and confirmed in `.gitignore`. Credentials are local-only."

---

## Phase 7 — Handoff to /create-skill

Tell the user:
> "Your data connection is ready. Now let's build a skill so you can query this data anytime by just asking in plain English."

Read `.cursor/skills/create-skill/SKILL.md` and launch the skill creation flow **in this same chat**, pre-loading:
- The platform (Tableau or Snowflake)
- The dataset description from Phase 2
- The questions the user said they answer with this data
- A pointer to [reference.md](reference.md) for architecture patterns

**This skill is complete after the handoff. The create-skill flow takes over.**
