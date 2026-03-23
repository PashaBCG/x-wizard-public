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

## Phase 2 — Identify Data Source

**Check context first.** If the user's message already names the data source type (e.g. mentions "Tableau", "dashboard", "Excel file", "spreadsheet", "Snowflake"), skip Q1 — confirm instead:
> "Sounds like you're working with [Tableau / an Excel file / Snowflake] — is that right?"

Only branch after they confirm.

**Q1** — only if the source is ambiguous (use AskQuestion):
> "Where does your data live?"
- Excel file on my laptop (or OneDrive/SharePoint synced locally)
- Tableau dashboard (I open it in a browser)
- Snowflake database
- Not sure / something else

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
> "For X-Wizard to read your Excel file, it needs to be saved on your laptop — in your Documents, Desktop, or inside this project folder. If your file is on SharePoint or OneDrive, that's fine too — most corporate laptops sync those files locally, so they're already on your machine.
>
> X-Wizard uses a built-in connector (think of it like a plug) that can read Excel files directly — but only if they're on your computer, not on a remote website."

**For L3+:**
> "The Excel MCP server reads local files only. OneDrive/SharePoint files work if synced locally. Confirm the file path is accessible from this machine."

Ask the user: "What's the file called, and where is it saved on your laptop?"

> Tip to share with the user: To get the exact path quickly —
> - **Mac:** Right-click the file in Finder → hold Option → click "Copy ... as Pathname"
> - **Windows:** Shift + right-click the file → "Copy as path"
> Or just describe where it is (e.g. "OneDrive, Reports folder") and I'll help locate it.

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

### Step 3 — Scan and understand the data

After conversion, present the discovered schema to the user. The conversion script outputs row count, column names, and file sizes — use these, plus sample values from the first few rows:

> "Here's what I found in your file:
> - **Sheet:** [sheet name] ([row count] rows)
> - **Columns:** [column names with sample values — e.g. Office (London, NYC, Boston) · Grade (C, A, JC)]
> - **My read:** [your interpretation — e.g. 'Office = location, Grade = seniority level — the others I'm less sure about']
>
> Does that look right? Anything I've labelled wrong?"

Then generate **tailored** follow-up questions based on the actual columns — not generic templates:
- If there's a Status column with multiple values: "Which Status values matter to you — all of them, or just Active?"
- If there's a date column: "Do you usually look at this for a specific time period, or the latest snapshot?"
- If columns are ambiguous (e.g. `Col_A`, `Metric_2`): "Can you tell me what this represents?"
- Use AskQuestion for questions with a clear set of options.

Finally, ask: "What questions do you usually answer with this file? Give me 2–3 examples — write them like you'd ask a colleague."

Store the confirmed schema and the user's answers for the handoff.

### Step 4 — Confirm Excel MCP

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

### Step 5 — Hand off to /create-skill

Tell the user:
> "Your data is ready. Now let's build a skill so you can query it anytime by just asking in plain English."

Read `.cursor/skills/create-skill/SKILL.md` and launch the skill creation flow **in this same chat**, pre-loading:
- Data source type: Excel (local file)
- The converted file path (CSV or Parquet)
- The confirmed column schema with types, sample values, and the user's plain-English descriptions from Step 3
- The user's key questions and metrics from Step 3
- Pointer to [reference.md](reference.md) for Excel query patterns

**This skill is complete after the handoff. The create-skill flow takes over.**

---

## Phase 4 — Credential Setup (PAT First)

*This phase is for Tableau and Snowflake only.*

### Tableau

Present the roadmap upfront so the user knows what to expect:

**For L1-L2:**
> "Here's what we'll do — it takes about 5 minutes:
> 1. Give me read access to your Tableau (quick one-time setup)
> 2. I'll explore the database behind your dashboard automatically
> 3. Check if you already have download access
> 4. If not — request it from the data owner
> 5. Build the skill foundation
> 6. Once access is confirmed — customize everything automatically"

**For L3+:**
> "We'll set up a PAT, run API discovery against your dashboard URL, check access rights, and scaffold the skill."

#### Step 1 — Create .env.local

Create `.env.local` at the workspace root with placeholder values. Then explain:

**For L1-L2:**
> "I've created a file called `.env.local` in your project folder. Think of it as a private sticky note on your laptop — it holds your login credentials. It's protected by a built-in safety rule (`.gitignore`) that prevents it from ever being uploaded or shared anywhere. Your credentials stay on your machine only."

**For L3+:**
> "Created `.env.local` at the workspace root. It's in `.gitignore` — never committed, never pushed."

Read `.gitignore` and confirm `.env.local` is listed. Mention this to the user briefly.

Tableau `.env.local` template:
```
TABLEAU_TOKEN_NAME="x-wizard-api"
TABLEAU_TOKEN_SECRET="PASTE_YOUR_TOKEN_SECRET_HERE"
```

#### Step 2 — PAT creation walkthrough

Guide the user through creating a Personal Access Token, **one step at a time:**

> 1. Open Tableau in your browser — any dashboard or workbook page is fine.
> 2. Click on your **user avatar** (top-right corner of the page).
> 3. Click **My Account Settings**.
> 4. Scroll down the page until you see **Personal Access Tokens**.
> 5. In the **Token Name** field, type: `x-wizard-api`
> 6. Click **Create token**.
> 7. **Important — copy the Secret immediately.** It's only shown once. Paste it into `.env.local` on the line `TABLEAU_TOKEN_SECRET="..."` (replace the placeholder).
> 8. Copy the **Token Name** value and paste it into `.env.local` on the line `TABLEAU_TOKEN_NAME="..."`.

After the user confirms both values are pasted:
> "Your credentials are saved and protected. Now send me the URL of the Tableau dashboard you work with — the one you want to automate."

### Snowflake

Follow the same guided approach as Tableau, adapted to the user's specific Snowflake setup. Since Snowflake configurations vary widely, discover the details by asking questions and giving tailored instructions:

1. Ask how they currently access Snowflake (Snowsight, a desktop tool, dbt, etc.)
2. Guide them through finding their account ID, warehouse, database, and schema — one value at a time
3. Populate `.env.local` as you go (same security explanation as Tableau — private, git-ignored, never leaves their machine)
4. Once credentials are set, test the connection and explore the schema (list databases, schemas, tables)

The goal is the same: read-only credentials in `.env.local` so a skill can connect and cache data locally.

---

## Phase 5 — API-Driven Discovery

*This phase is for Tableau only. For Snowflake, the connection test and schema exploration in Phase 4 serves the same purpose.*

### Tableau

Once the user provides their dashboard URL, run the discovery script:

```bash
python3 .cursor/skills/data-advisor/scripts/discover.py "USER_URL_HERE"
```

Read [tableau-setup.md](tableau-setup.md) for full technical details on what the script does.

The script automatically:
1. Parses the URL (works with view URLs, workbook URLs, and datasource URLs — any Tableau link the user shares)
2. Signs in via PAT to the correct site
3. Resolves the URL to the parent workbook via the Metadata GraphQL API
4. Discovers: workbook name, owner, all datasources, connection types, extract status
5. Tests download access on the workbook and any published datasources
6. Tests CSV export capability
7. Returns structured JSON with a recommendation

Present the output to the user in plain English:

**For L1-L2:**
> "Here's what I found:
> - **Dashboard:** [workbook name]
> - **Owner:** [owner name]
> - **Data source:** [datasource name] ([embedded/published])
> - **Your access:** [summary — e.g., 'You can view but not download yet']"

**For L3+:**
> "Discovery complete: [workbook name] | Owner: [owner] | DS: [name] ([type]) | Download: [yes/no] | CSV export: [yes/no]"

Store all discovered values: `WORKBOOK_NAME`, `DATASOURCE_NAME`, `OWNER`, `DASHBOARD_URL` (the URL the user provided), server, site, workbook LUID, datasource LUID, access rights.

---

## Phase 6 — Access Check and Email (if needed)

*This phase is for Tableau and Snowflake only.*

### Tableau — branch based on discovery output

Read the `recommendation` field from the discovery JSON and the `access` object. Then branch:

**If download access is already available** (published DS with download, or workbook download works):
> "Great news — you already have download access. Let's move straight to building the skill."

Skip to Phase 7.

**If published datasource exists but no download access:**

Read `.cursor/skills/outlook-draft/SKILL.md` and draft an email to the owner.

**Subject:** `Tableau access`

**Body:**
> "Hi [OWNER], could you give me download access to the "[DATASOURCE_NAME]" datasource on Tableau ([site] site)? I'm automating the lookups I already do manually in the browser — read + download only, nothing gets modified. The data stays cached locally on my laptop. Happy to jump on a quick call if easier. Thanks!"

Include the dashboard URL the user shared.

**If datasource is embedded only (not published) and no workbook download:**

Read `.cursor/skills/outlook-draft/SKILL.md` and draft an email with the appropriate recommendation from [tableau-setup.md](tableau-setup.md) — "Email Templates" section. Pick the template that matches the scenario (publish DS separately, grant workbook download, or send hyper file).

**Subject:** `Tableau access`

Include the dashboard URL the user shared.

**Do NOT include** lengthy persuasion paragraphs, technical jargon about APIs or PATs, or numbered checklists.

After drafting:
> "I've drafted the email for you. Review it, send it when ready. In the meantime, let me start building the skill foundation — we can finish customizing once access lands."

### Snowflake

If the connection test in Phase 4 failed due to missing access, guide the user to identify the right contact (data team, analytics lead, or team lead) and draft a short access-request email via the outlook skill:

**Subject:** `Snowflake read access`
**Body:** Who you are, what database/schema you need read-only access to, one line on why it's safe, closing.

---

## Phase 7 — Scaffold and Handoff to /create-skill

### If download access is available now

Tell the user:
> "Let me connect and explore the data."

The discovery script already identified the datasources. If a downloadable datasource was found (published DS or workbook), proceed to download the data, read the `.hyper` schema with `tableauhyperapi`, and auto-populate the skill's `reference.md` with:
- Table names
- Column name, type, and example values (first 5 rows)
- Data source metadata (server, site, workbook, datasource name, dashboard URL)

Present the discovered schema to the user in plain English and ask:
> "Here's what I found in the data: [list of column names with sample values]. Can you tell me:
> 1. What do these columns mean in your day-to-day work?
> 2. Which ones are the key metrics you care about?
> 3. What questions do you typically answer with this data?"

### If waiting for access

Scaffold the skill skeleton now (config.yaml, empty reference.md, query.py with `--discover` built in) and tell the user:
> "I've built the skill foundation. When you get the access confirmation, just come back and say 'I have access' — I'll finish the setup automatically."

### Handoff to /create-skill

Tell the user:
> "Your data connection is ready. Now let's build a skill so you can query this data anytime by just asking in plain English."

Read `.cursor/skills/create-skill/SKILL.md` and launch the skill creation flow **in this same chat**, pre-loading:
- The platform (Tableau or Snowflake)
- All discovered metadata: server, site, workbook LUID, workbook name, datasource name, `DASHBOARD_URL`
- The full column schema with types and sample values from discovery (if available)
- The user's interpretation of the data and their key questions
- A pointer to [reference.md](reference.md) for architecture patterns and [tableau-setup.md](tableau-setup.md) for Tableau-specific API reference

**This skill is complete after the handoff. The create-skill flow takes over.**
