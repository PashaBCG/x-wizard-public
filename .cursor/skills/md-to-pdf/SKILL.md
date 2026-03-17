---
name: md-to-pdf
description: Convert any Markdown file to a BCG X branded PDF (dark theme, JetBrains Mono, teal/purple accents). Use when the user asks to export, save, generate, or convert a .md file to PDF — or says "save as PDF", "generate a PDF", "export to PDF", "resave as PDF", or asks to share/distribute a Markdown file as a document.
---

# md-to-pdf

Converts any Markdown file to a styled PDF using the BCG X dark theme:
- Background `#232326`, text `#F0F0F0`, JetBrains Mono throughout
- Primary accent `#00E0B5` (teal) — H1/H2, code, borders
- Secondary accent `#5A6BFF` (purple) — H3, blockquote borders, table headers

## When to apply

Trigger on any request to export or convert a `.md` file to PDF. Examples:
- "Save the setup guide as a PDF"
- "Convert this offer review to PDF"
- "Export the MDP analysis as a document"
- "Resave / share this as a PDF"

If the user doesn't specify a file, infer from context (file open in editor, most recently discussed `.md`, or the most relevant file).

## How to run

The script lives in `.cursor/skills/md-to-pdf/scripts/md_to_pdf.sh` (this repo, canonical copy):

```bash
bash .cursor/skills/md-to-pdf/scripts/md_to_pdf.sh <path/to/file.md> [path/to/output.pdf]
```

- Output defaults to **same directory as input**, with `.pdf` extension.
- Opens the PDF in Preview automatically on macOS.
- Works from any working directory — paths are resolved to absolute.

**Common invocations:**

```bash
# Setup guide (repo root)
bash .cursor/skills/md-to-pdf/scripts/md_to_pdf.sh SETUP_GUIDE.md

# Portfolio review offer output
bash .cursor/skills/md-to-pdf/scripts/md_to_pdf.sh x-wizard/portfolio-review/outputs/2026-04/supply-chain-ai.md

# MDP analysis
bash .cursor/skills/md-to-pdf/scripts/md_to_pdf.sh x-wizard/portfolio-review/outputs/2026-04/mdp-analysis.md
```

## Requirements

- `pandoc` — `brew install pandoc`
- Google Chrome — at `/Applications/Google Chrome.app/`

The script prints a clear error with install instructions if either is missing.

## What the script does

1. Resolves input to absolute path (safe from any cwd)
2. Runs `pandoc` → standalone HTML with BCG X CSS embedded
3. Runs Chrome headless → PDF (no browser header/footer bar)
4. Deletes temp HTML, opens the PDF
