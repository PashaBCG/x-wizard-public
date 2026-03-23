---
name: data-advisor
description: Single data onboarding guide for Excel, Tableau, and Snowflake. Educates non-technical users on file handling, data conversion, access requests, credential setup, and hands off to /create-skill. Use when the user mentions excel, xlsx, spreadsheet, workbook, tableau, snowflake, dashboard, dataset, data source, metrics, reporting data, client view, live data, automate dashboard, automate reporting, connect to my data, set up Tableau, set up Snowflake, daily numbers, pull my metrics, or asks how to connect to their data. This skill takes priority over create-skill when the data source is not yet connected.
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

## Phase 4 — Guided Discovery

*This phase is for Tableau and Snowflake only.*

The goal is to collect every piece of information needed — with certainty — by guiding the user click-by-click. Do NOT ask whether the user knows something; instead, walk them through finding it.

### Tableau — step-by-step

Present these steps **one at a time**, waiting for the user's response before moving on.

**Step 1 — Dashboard URL:**
> "Open the Tableau dashboard you usually look at — the one you want to automate. Send me the URL from your browser's address bar."

Store this as `DASHBOARD_URL`. This is for reference only (it shows the view the user sees).

**Step 2 — Navigate to Data Sources:**
> "Now look at the top-right area of the page — the same row where you see your user picture / avatar. Click **Data Sources**."

**Step 3 — Open Details:**
> "In the panel that opens, click **Details**."

**Step 4 — Identify the owner:**
> "You should now see the workbook page. Near the workbook name there's an **Owner** — who is listed there? (e.g., `john.smith@email.com`)"

Store as `OWNER_EMAIL`.

**Step 5 — Workbook URL and names:**
> "Send me the URL you're on now (it should look like `tableau.company.com/#/site/Analytics/workbooks/111/datasources`).
> Also tell me: what is the **workbook name** shown at the top, and the **data source name** listed on the page?"

Store as `WORKBOOK_URL`. From this URL, parse automatically:
- **Server URL** — everything before `/#/` (e.g., `https://tableauha.bcg.com`)
- **Site name** — the segment after `/site/` (e.g., `ProductAnalytics`)
- **Workbook ID** — the numeric segment after `/workbooks/` (e.g., `8976`)

Store the user-provided names as `WORKBOOK_NAME` and `DATASOURCE_NAME`.

**Summary:** After these five steps you have: `DASHBOARD_URL`, `WORKBOOK_URL`, server, site, workbook ID, `WORKBOOK_NAME`, `DATASOURCE_NAME`, and `OWNER_EMAIL`. All collected with certainty — no guesswork.

### Snowflake

> "Ask your team's data or analytics contact who manages the Snowflake account your reports use. If you're not sure who that is, ask your team lead — they'll know or can point you to the right person."

Ask the user for:
- Owner / admin name and email
- The name of the database or schema they use

---

## Phase 5 — Draft Access Request Email

*This phase is for Tableau and Snowflake only.*

Read `.cursor/skills/outlook-draft/SKILL.md` and use it to compose a short, direct email to the data owner.

### Tableau email

**Subject:** `Tableau access`

**Body — keep it short:**

1. One-sentence intro: who you are (name + role from `project.mdc`) and what you need.
2. The ask — direct and specific:
   > "Could you give me read and download access to **[DATASOURCE_NAME]** that feeds the **[WORKBOOK_NAME]** dashboard? Here are the links for reference:
   > - Dashboard: [DASHBOARD_URL]
   > - Workbook / data source: [WORKBOOK_URL]"
3. Brief context (1–2 sentences max):
   > "I'm automating the manual lookups I already do in the browser. The access is read + download only — nothing can be modified. The data stays cached locally on my laptop."
4. Closing: "Happy to jump on a quick call if easier. Thanks!"

**Do NOT include:**
- Numbered checklists of items to provide back (we already have server, site, workbook ID from the URLs)
- Lengthy persuasion paragraphs
- Technical jargon about APIs or PATs

### Snowflake email

**Subject:** `Snowflake read access`

**Body:** Same short structure — who you are, what database/schema you need read-only access to, one line on why it's safe, closing.

After drafting, tell the user:
> "I've drafted the email for you. Review it, send it when ready. In the meantime, let's set up your login credentials — we can do that right now while we wait for the access."

---

## Phase 6 — Configure Credentials

*Run this in parallel with the access request — don't wait for the owner to respond.*

### Step 1 — Create .env.local and explain

Create `.env.local` at the workspace root with placeholder values (see Tableau or Snowflake template below). Then explain:

**For L1-L2:**
> "I've created a file called `.env.local` in your project folder. Think of it as a private sticky note on your laptop — it holds your login credentials. It's protected by a built-in safety rule (`.gitignore`) that prevents it from ever being uploaded or shared anywhere. Your credentials stay on your machine only."

**For L3+:**
> "Created `.env.local` at the workspace root. It's in `.gitignore` — never committed, never pushed."

Read `.gitignore` and confirm `.env.local` is listed. Mention this to the user briefly.

### Step 2 — Tableau: PAT creation walkthrough

Guide the user through creating a Personal Access Token, **one step at a time:**

> 1. Open Tableau in your browser — any dashboard or workbook page is fine.
> 2. Click on your **user avatar** (top-right corner of the page).
> 3. Click **My Account Settings**.
> 4. Scroll down the page until you see **Personal Access Tokens**.
> 5. In the **Token Name** field, type: `x-wizard-api`
> 6. Click **Create token**.
> 7. **Important — copy the Secret immediately.** It's only shown once. Paste it into `.env.local` on the line `TABLEAU_TOKEN_SECRET="..."` (replace the placeholder).
> 8. Copy the **Token Name** value and paste it into `.env.local` on the line `TABLEAU_TOKEN_NAME="..."`.

Tableau `.env.local` template:
```
TABLEAU_TOKEN_NAME="x-wizard-api"
TABLEAU_TOKEN_SECRET="PASTE_YOUR_TOKEN_SECRET_HERE"
```

After the user confirms both values are pasted, say:
> "Your credentials are saved and protected. Once the owner grants download access, we're ready to connect."

### Step 2 — Snowflake: credential entry

Ask the user for each credential value and populate `.env.local`:
```
SNOWFLAKE_ACCOUNT="your-account-id"
SNOWFLAKE_USER="your-username"
SNOWFLAKE_PASSWORD="your-password"
SNOWFLAKE_WAREHOUSE="your-warehouse"
SNOWFLAKE_DATABASE="your-database"
SNOWFLAKE_SCHEMA="your-schema"
```

### Step 3 — Verify

Read `.gitignore` and confirm `.env.local` is listed. Then:

> "Credentials saved. `.gitignore` confirms `.env.local` will never be uploaded. You're all set."

---

## Phase 7 — Discovery and Handoff to /create-skill

*Once the user has credentials configured (Phase 6) and access granted (Phase 5 response received).*

### Step 1 — Auto-discover the data

Tell the user:
> "Let me connect to Tableau and see what data is available."

Build and run the discovery script (see [reference.md](reference.md) — "Tableau Discovery Pattern") with the `--discover` flag. The script:

1. Signs in via PAT
2. Queries the Tableau REST API using the workbook ID to list data sources
3. Downloads each data source as `.tdsx`, extracts the `.hyper` file
4. Opens the `.hyper` with `tableauhyperapi` and reads all tables, columns, types, and sample rows
5. Outputs a JSON summary of the discovered schema

### Step 2 — Scaffold reference.md

Use the discovery output to auto-populate the skill's `reference.md` with:
- Table names
- Column name, type, and example values (first 5 rows)
- Data source metadata (server, site, workbook, datasource name)

### Step 3 — Ask interpretation questions

Present the discovered schema to the user in plain English and ask:
> "Here's what I found in the data: [list of column names with sample values]. Can you tell me:
> 1. What do these columns mean in your day-to-day work?
> 2. Which ones are the key metrics you care about?
> 3. What questions do you typically answer with this data?"

### Step 4 — Hand off to create-skill

Tell the user:
> "Your data connection is ready. Now let's build a skill so you can query this data anytime by just asking in plain English."

Read `.cursor/skills/create-skill/SKILL.md` and launch the skill creation flow **in this same chat**, pre-loading:
- The platform (Tableau or Snowflake)
- All discovered metadata: server, site, workbook ID, workbook name, datasource name, `DASHBOARD_URL`, `WORKBOOK_URL`
- The full column schema with types and sample values from discovery
- The user's interpretation of the data and their key questions from Step 3
- A pointer to [reference.md](reference.md) for architecture patterns and the `--discover` code template

**This skill is complete after the handoff. The create-skill flow takes over.**
