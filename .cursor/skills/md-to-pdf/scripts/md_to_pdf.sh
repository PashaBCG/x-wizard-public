#!/usr/bin/env bash
# md_to_pdf.sh — convert a Markdown file to a BCG X branded PDF
# Usage:  bash .cursor/skills/md-to-pdf/scripts/md_to_pdf.sh <input.md> [output.pdf]
# Output defaults to the same directory as the input file.

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: md_to_pdf.sh <input.md> [output.pdf]" >&2
  exit 1
fi

# Resolve input to absolute path
INPUT="$(cd "$(dirname "$1")" && pwd)/$(basename "$1")"
OUTDIR="$(dirname "$INPUT")"
BASENAME="$(basename "${INPUT%.md}")"
OUTPUT="${2:-${OUTDIR}/${BASENAME}.pdf}"

# If a relative output path was given, resolve it relative to cwd
if [[ "$OUTPUT" != /* ]]; then
  OUTPUT="$(pwd)/$OUTPUT"
fi

TMPHTML="$(mktemp /tmp/md_to_pdf_XXXXXX.html)"

# ── Chrome path — auto-detect OS ───────────────────────────────────────────────
if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
  # Windows (Git Bash / MSYS2 / Cygwin)
  CHROME_CANDIDATES=(
    "/c/Program Files/Google/Chrome/Application/chrome.exe"
    "/c/Program Files (x86)/Google/Chrome/Application/chrome.exe"
    "$LOCALAPPDATA/Google/Chrome/Application/chrome.exe"
  )
else
  # macOS
  CHROME_CANDIDATES=(
    "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
  )
fi

CHROME=""
for candidate in "${CHROME_CANDIDATES[@]}"; do
  if [[ -x "$candidate" ]]; then
    CHROME="$candidate"
    break
  fi
done

# ── Sanity checks ──────────────────────────────────────────────────────────────
if [[ ! -f "$INPUT" ]]; then
  echo "Error: '$INPUT' not found." >&2
  exit 1
fi
if ! command -v pandoc &>/dev/null; then
  if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" || "$OSTYPE" == "cygwin" ]]; then
    echo "Error: pandoc not installed. Download from: https://pandoc.org/installing.html" >&2
  else
    echo "Error: pandoc not installed. Run: brew install pandoc" >&2
  fi
  exit 1
fi
if [[ -z "$CHROME" ]]; then
  echo "Error: Google Chrome not found." >&2
  echo "  Mac: install from https://google.com/chrome" >&2
  echo "  Windows: install from https://google.com/chrome or check path manually" >&2
  exit 1
fi

# ── BCG X dark theme ──────────────────────────────────────────────────────────
CSS='
<style>
  @import url("https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,400;0,500;0,600;0,700;1,400&display=swap");

  header#title-block-header { display: none; }

  @page { margin: 20mm 18mm; background: #232326; }

  *, *::before, *::after { box-sizing: border-box; }

  html { background: #232326; }

  body {
    font-family: "JetBrains Mono", "Fira Code", "Courier New", monospace;
    font-size: 10pt;
    line-height: 1.7;
    color: #F0F0F0;
    background: #232326;
    max-width: 860px;
    margin: 0 auto;
    padding: 48px 52px 64px;
  }

  h1 {
    font-size: 20pt; font-weight: 700; color: #00E0B5;
    border-bottom: 2px solid #00E0B5;
    padding-bottom: 10px; margin-top: 0; margin-bottom: 20px;
  }
  h2 { font-size: 13pt; font-weight: 700; color: #00E0B5; margin-top: 36px; margin-bottom: 10px; }
  h3 { font-size: 11pt; font-weight: 600; color: #5A6BFF; margin-top: 24px; margin-bottom: 6px; }
  h4 { font-size: 10pt; font-weight: 600; color: #A0A0B0; margin-top: 18px; margin-bottom: 4px; }

  h1 + p, h2 + p, h3 + p { margin-top: 0; }
  p { margin: 0 0 10px; }

  a { color: #00E0B5; text-decoration: none; }
  strong { color: #ffffff; font-weight: 600; }
  em { color: #C0C0D0; }

  ul, ol { margin: 0 0 12px 0; padding-left: 22px; }
  li { margin-bottom: 4px; }

  pre {
    background: #1A1A1D; border-left: 3px solid #00E0B5;
    border-radius: 4px; padding: 14px 16px; overflow-x: auto; margin: 10px 0 16px;
  }
  pre code {
    font-family: "JetBrains Mono", monospace; font-size: 9pt;
    background: none; padding: 0; color: #00E0B5;
  }
  code {
    font-family: "JetBrains Mono", monospace; font-size: 9pt;
    background: #1A1A1D; border-radius: 3px; padding: 1px 5px; color: #00E0B5;
  }

  blockquote {
    border-left: 3px solid #5A6BFF; background: #1E1E2A;
    margin: 10px 0 14px; padding: 10px 16px;
    border-radius: 0 4px 4px 0; color: #B0B8FF;
  }
  blockquote p { margin: 0; }

  table { border-collapse: collapse; width: 100%; margin: 12px 0 20px; font-size: 9.5pt; }
  th { background: #5A6BFF; color: #fff; padding: 8px 12px; text-align: left; font-weight: 600; }
  td { padding: 7px 12px; border-bottom: 1px solid #333340; vertical-align: top; color: #E0E0E0; }
  tr:nth-child(even) td { background: #2A2A2E; }

  hr { border: none; border-top: 1px solid #3A3A3E; margin: 24px 0; }

  .xwizard-footer {
    margin-top: 48px;
    padding-top: 12px;
    border-top: 1px solid #3A3A3E;
    font-size: 8pt;
    color: #666;
    font-style: italic;
  }

  @media print {
    html, body { background: #232326 !important; }
    a { color: #00E0B5; }
    pre, blockquote, table { page-break-inside: avoid; }
    h1, h2, h3 { page-break-after: avoid; }
  }
</style>
'

# ── pandoc → HTML ──────────────────────────────────────────────────────────────
echo "→ Converting $(basename "$INPUT") to HTML..."
pandoc "$INPUT" \
  --to html5 \
  --standalone \
  --embed-resources \
  --resource-path="$(dirname "$INPUT")" \
  --metadata title="$(basename "$BASENAME")" \
  --variable "header-includes=$CSS" \
  --output "$TMPHTML"

# Append X-Wizard footer before </body>
FOOTER='<div class="xwizard-footer">Generated by X-Wizard</div>'
sed -i.bak "s|</body>|${FOOTER}</body>|" "$TMPHTML"
rm -f "${TMPHTML}.bak"

# ── Chrome headless → PDF ──────────────────────────────────────────────────────
echo "→ Rendering PDF..."
"$CHROME" \
  --headless \
  --disable-gpu \
  --no-sandbox \
  --print-to-pdf="$OUTPUT" \
  --print-to-pdf-no-header \
  --no-pdf-header-footer \
  "file://$TMPHTML" \
  2>/dev/null

rm -f "$TMPHTML"

echo "✓ Saved: $OUTPUT"

# Open the PDF (Mac only)
if [[ "$(uname)" == "Darwin" ]]; then
  open "$OUTPUT"
fi
