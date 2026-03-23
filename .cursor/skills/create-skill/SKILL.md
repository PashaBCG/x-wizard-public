---
name: create-skill
description: Build a new custom X-Wizard skill from a plain-English description of a task or workflow. No coding required. Use when the user wants to automate something, create a skill, build a tool, teach x-wizard to do a new task, or says "I want to automate", "build me a skill", "create a skill", or describes a repetitive task they do manually.
---

# Create a Custom X-Wizard Skill

A skill is a simple instruction file (SKILL.md) that teaches X-Wizard to do a specific task on demand. You describe the task in plain English — I'll build the skill file for you.

## Step 1 — Gather Requirements

Ask the user these questions (use AskQuestion tool where available, or conversationally):

**Q1 — Context** (free text)
> "Tell me about yourself and your team. What do you work on?"

**Q2 — The task** (free text)
> "What task do you want to automate? Describe it like you're explaining it to a new colleague."

**Q3 — How you do it today** (free text)
> "Walk me through the manual steps you currently follow. What files do you open? What do you produce?"

**Q4 — Output format** (AskQuestion)
> "What should the output look like?"
- A table or summary in chat
- A saved file (Word, Excel, PDF, PowerPoint)
- A sent or drafted email
- Multiple of the above
- I'm not sure yet

**Q5 — Data source** (AskQuestion)
> "Where does the data come from?"
- I'll paste or type it in
- A file on my computer (Excel, CSV, PDF)
- Outlook emails or calendar
- I'll describe it and you can ask
- Not sure

After gathering answers, say:
> "Got it. Let me design your skill."

---

## Step 2 — Design the Skill

Based on the answers, determine:

1. **Skill name** — lowercase, hyphens, max 64 chars (e.g. `monthly-offer-summary`, `deal-tracker`, `team-update-email`)
2. **Trigger phrases** — what the user will type to invoke it
3. **Core workflow** — ordered steps the agent should follow
4. **Output format** — what gets produced and how
5. **Data handling** — how input data enters the workflow
6. **Supporting scripts** — if needed (Python for data processing, shell for file operations)

Present a brief design summary to the user and ask for confirmation before writing:
> "Here's what I'll build:
> - **Skill:** [name]
> - **Triggered by:** [phrases]
> - **What it does:** [2-sentence summary]
> - **Output:** [description]
>
> Does this sound right? Anything to adjust?"

Wait for confirmation before proceeding to Step 3.

---

## Step 3 — Write the Skill Files

Create the skill under `.cursor/skills/[skill-name]/`:

```
[skill-name]/
├── SKILL.md          # required
├── reference.md      # optional — detailed docs the agent reads on demand to de-bloat the SKILL file
└── scripts/          # optional — Python or shell helpers
    └── [name].py
```

Put essential instructions in `SKILL.md`. Move lengthy reference material or examples to `reference.md` and link to it — the agent will read it only when needed. Keep all links one level deep.

### SKILL.md structure

```markdown
---
name: [skill-name]
description: [See description rules below]
---

# [Skill Display Name]

## When to use
[Trigger scenarios — what the user says to invoke this]

## Workflow

1. [Step 1]
2. [Step 2]
3. [Step 3]

## Output format
[Exact description of what gets produced]

## Data requirements
[What input the skill needs and how to provide it]
```

### Writing the description (critical)

The description is how the agent decides to load this skill. Write in **third person**, include both **WHAT** it does and **WHEN** to use it:

- ✅ `"Generates a monthly offer summary table from an Excel file. Use when the user asks to summarise offers, review pipeline, or says 'monthly report'."`
- ❌ `"Helps with the monthly report"` — too vague, won't trigger reliably

### Degrees of freedom

Match how prescriptive the skill is to how fragile the task is:

| Task type | Approach |
|---|---|
| Multiple valid approaches | Plain-English instructions |
| Preferred pattern with some flexibility | Template or pseudocode |
| Must be exact every time | Specific script with fixed steps |

### Supporting scripts (if needed)

Create `scripts/[name].py` or `scripts/[name].sh` with:
- Clear docstring explaining purpose and usage
- Error handling with helpful messages
- Exit codes (0 = success, non-zero = failure)

Pre-written scripts are preferred over having the agent generate code on the fly — they're faster, more reliable, and save context.

### Excel skill requirements (apply when data source is an Excel file)

When building a skill that reads an Excel file, the skill MUST include all of the following. For conversion logic, extraction script templates, query patterns, and the two-wave workflow, follow `.cursor/skills/data-advisor/reference.md` — it is the single source of truth for Excel data handling.

**1. File verification**
The skill's first step on any run must verify the file is accessible:
- Open it via the Excel MCP and confirm it loads
- If the file is not found: fail immediately with a clear error showing the exact path that was tried and how to fix it
- Never silently proceed with a missing file

**2. Schema reference in `reference.md`**
Create (or update) the skill's `reference.md` with a confirmed column schema:
- Column name | Example values | Plain-English meaning
- Source: use the schema from the context block (`CONTEXT FROM DATA ADVISOR` or `CONTEXT FROM ONBOARDING`) if available, or discover it now using the scan script at `.cursor/skills/data-advisor/scripts/scan_excel.py`

**3. Data query script: `scripts/query_data.py`**
Create a Python script following the extraction template and query patterns in `.cursor/skills/data-advisor/reference.md`. The script must:
- Convert the Excel file to CSV (under 20 MB) or Parquet (20 MB+) before querying
- Accept the file path and sheet name as arguments
- Clean up temp files after the result is returned

**4. Mandatory test run (Step 4 — non-optional for Excel skills)**
After writing all files:
1. Run `.cursor/skills/data-advisor/scripts/scan_excel.py` or the Excel MCP to confirm the file opens without error
2. Run `scripts/query_data.py` with one of the example questions from the context — confirm it executes and returns a result
3. Present the result to the user and ask: "Does this look right? Is this the kind of output you'd expect?"
4. Iterate if needed. Do not declare the skill complete until the user confirms the output is correct.

### Update project.mdc routing

Add a row to the Skill Routing table in `.cursor/rules/project.mdc`:

```
| [User intent description] | `.cursor/skills/[skill-name]/SKILL.md` |
```

---

## Step 4 — Test & Hand Off

After writing the files, say:

> "Your **[skill-name]** skill is ready. To use it, open a new chat (Cmd+N / Ctrl+N) and type:
>
> `/[skill-name]`
>
> Or just describe the task naturally — I'll recognise it and use the skill automatically.
>
> Want me to walk through an example run right now?"

If the user says yes, simulate a run of the skill with example inputs they provide.

---

## Quality Checklist

Before finalising, verify:
- [ ] Skill name is lowercase with hyphens only
- [ ] Description says WHAT it does and WHEN to use it (third person)
- [ ] SKILL.md body is under 500 lines
- [ ] Workflow steps are specific and ordered
- [ ] Output format is explicitly described
- [ ] project.mdc routing table is updated
- [ ] "Generated by X-Wizard" footer is included in any output template
- [ ] File references are one level deep (SKILL.md → reference.md, not deeper)

**Excel skills only:**
- [ ] File verification step is the first action in the workflow
- [ ] Column schema exists in `reference.md` with example values and plain-English meaning
- [ ] `scripts/query_data.py` exists, handles both CSV and Parquet paths based on file size, and cleans up temp files
- [ ] Test run was completed: script executed without error and user confirmed output is correct

---

## Tips for great skills

- **Narrow scope wins.** One skill, one job. Better to have three focused skills than one bloated one.
- **Describe the output exactly.** "A table with columns: Offer, NCC, YoY%" is better than "a summary".
- **Reference file paths.** If the skill reads a specific file, say so explicitly (e.g. `data/monthly-report.xlsx`).
- **Progressive complexity.** Start simple — you can always add more steps later.
- **Give a default, not a menu.** "Use pdfplumber — if the PDF is scanned, use pdf2image instead" beats listing five libraries.

## Anti-patterns to avoid

- **Vague names** — `helper`, `utils`, `tools` won't be discovered. Use `monthly-offer-summary`, not `report-tool`.
- **Vague descriptions** — if the description doesn't contain the trigger phrase the user will type, the skill won't load.
- **Too many options** — pick the best approach and note the exception, don't list every alternative.
- **Time-sensitive wording** — avoid "as of Q1 2025, do X" — it goes stale. State the current method only.
- **Inconsistent terms** — pick one word per concept and use it throughout (`field` not `field/box/element`).
