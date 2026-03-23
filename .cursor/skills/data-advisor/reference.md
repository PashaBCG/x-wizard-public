# Data Advisor — Reference Patterns

This file is read by the agent when building data skills via `create-skill`. It contains production-tested patterns for each data source type.

**When to read this file:** Whenever `create-skill` is building a skill whose data comes from Excel, Tableau, or Snowflake. The SKILL.md workflow will point you here at handoff time.

---

## Excel Pattern (Local Files)

### Conversion Rules

| Source size | Target | Method |
|-------------|--------|--------|
| Under 20 MB | CSV | `pd.read_excel(...).to_csv(...)` |
| 20 MB+ | Parquet | `pd.read_excel(...).to_parquet(...)` |

Always:
- Use `openpyxl` engine for `.xlsx` files
- Drop completely empty columns and rows before writing
- Cast financial/numeric columns explicitly: `pd.to_numeric(col, errors="coerce").fillna(0.0)`
- Normalize string columns: `.str.strip()` to remove whitespace
- Print a sanity-check summary after conversion: row count, column list, file size, key column sums

### Extraction Script Template

Every Excel-based data skill should include an extraction script at `scripts/extract_{name}.py`. The script handles conversion from raw `.xlsx` to the clean query format. Follow this structure:

```python
#!/usr/bin/env python3
"""Extract data from [DESCRIPTION] Excel file and write a cleansed [CSV/Parquet] file.

Usage:
    python3 .cursor/skills/{skill-name}/scripts/extract_{name}.py
    python3 .cursor/skills/{skill-name}/scripts/extract_{name}.py /path/to/file.xlsx
"""

import glob
import os
import sys
from pathlib import Path

import pandas as pd

SKILL_DIR = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = SKILL_DIR.parents[2]
OUTPUT_PATH = WORKSPACE_ROOT / "x-wizard" / "{skill-name}" / "data-latest.parquet"
DOWNLOADS_DIR = Path.home() / "Downloads"

# Columns to drop (customize per dataset)
COLUMNS_TO_DROP = []

# Columns to rename for clarity (customize per dataset)
COLUMN_RENAMES = {}

# Columns that should be numeric (customize per dataset)
FINANCIAL_COLUMNS = []


def find_source_file(explicit_path=None):
    if explicit_path:
        p = Path(explicit_path)
        if not p.exists():
            sys.exit(f"File not found: {p}")
        return p

    pattern = str(DOWNLOADS_DIR / "{FilePattern}*")
    matches = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    xlsx = [m for m in matches if m.endswith(".xlsx") and not os.path.basename(m).startswith("~$")]
    if not xlsx:
        sys.exit(
            f"No matching file found in {DOWNLOADS_DIR}.\n"
            "Download the Excel file first, or pass the path explicitly:\n"
            f"  python3 .cursor/skills/{{skill-name}}/scripts/extract_{{name}}.py /path/to/file.xlsx"
        )
    return Path(xlsx[0])


def extract(source):
    print(f"Reading: {source}")
    print(f"  File size: {source.stat().st_size / (1024 * 1024):.1f} MB")

    df = pd.read_excel(source, sheet_name="Sheet1", engine="openpyxl")
    print(f"  Rows loaded: {len(df):,}")
    print(f"  Columns: {len(df.columns)}")

    # Drop unused columns
    existing_drops = [c for c in COLUMNS_TO_DROP if c in df.columns]
    if existing_drops:
        df = df.drop(columns=existing_drops)

    # Rename columns
    df = df.rename(columns={k: v for k, v in COLUMN_RENAMES.items() if k in df.columns})

    # Cast numeric columns
    for col in FINANCIAL_COLUMNS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

    # Write output
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(OUTPUT_PATH, engine="pyarrow", index=False)

    file_size_mb = OUTPUT_PATH.stat().st_size / (1024 * 1024)
    print(f"\nDone.")
    print(f"  Output: {OUTPUT_PATH}")
    print(f"  Rows: {len(df):,}")
    print(f"  Columns: {len(df.columns)} — {list(df.columns)}")
    print(f"  Output size: {file_size_mb:.1f} MB")


if __name__ == "__main__":
    explicit = sys.argv[1] if len(sys.argv) > 1 else None
    extract(find_source_file(explicit))
```

Adapt per dataset:
- Replace `{skill-name}`, `{name}`, `{FilePattern}`, `{DESCRIPTION}` with actual values
- Set the correct `sheet_name` (ask the user which sheet contains the data)
- Populate `COLUMNS_TO_DROP`, `COLUMN_RENAMES`, `FINANCIAL_COLUMNS` based on the actual data
- Switch output from `.to_parquet()` to `.to_csv()` if the source file is under 20 MB

### Querying Pattern (pandas)

Skills that query local Excel-derived data should follow this pattern:

**Loading:**
```python
import pandas as pd
df = pd.read_parquet("x-wizard/{skill-name}/data-latest.parquet")
# or for CSV:
df = pd.read_csv("x-wizard/{skill-name}/data-latest.csv")
```

**Common operations:**

```python
# Grouped aggregation with totals
result = df.groupby("Category").agg(
    metric_a=("Column A", "sum"),
    metric_b=("Column B", "sum"),
).sort_values("metric_a", ascending=False)

# Pivot table
pivot = df.pivot_table(
    values="Value", index="Row Field", columns="Col Field",
    aggfunc="sum", fill_value=0, margins=True, margins_name="Total"
)

# Fuzzy name matching (case-insensitive)
df[df["Name"].str.contains("keyword", case=False, na=False)]

# Period comparison
for year in sorted(df["Year"].unique()):
    yr = df[df["Year"] == year]
    # compute metrics per year
```

**Value formatting:**
```python
def fmt_m(val):
    """Format value as millions."""
    return f"${val / 1e6:,.1f}M"

def fmt_pct(num, denom):
    """Format as percentage."""
    return f"{num / denom * 100:.1f}%" if denom else "N/A"
```

**Output rules:**
- Always include a **Total** row at the bottom of grouped tables
- Sort by primary metric descending (largest first)
- Show top 20 rows by default; mention total count if truncated
- Format as markdown tables
- Bold the key fact in the lead sentence

**Key dependencies:** `pandas`, `openpyxl`, `pyarrow` (for Parquet)

### Two-Wave Workflow

Every Excel-based skill should define two modes:

- **Wave 1 — Data Refresh:** Run the extraction script to convert a fresh Excel file. Only trigger when the user explicitly asks to refresh, or when the data file is missing. Never auto-refresh.
- **Wave 2 — Querying:** Load the converted file with pandas and answer questions. This is the default mode.

---

## Tableau Pattern

### config.yaml Template

```yaml
tableau:
  server: "https://tableau.yourcompany.com"
  api_version: "3.19"
  site_content_url: "YourSiteName"

data_sources:
  your_source:
    name: "Human-Readable Name"
    datasource_id: "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
    snapshots_dir: "x-wizard/{skill-name}/data/snapshots"
    refresh_hours: 48
    description: "What this data source contains"
```

### Cache Logic

The download and cache workflow:

1. **Sign in** via Personal Access Token (PAT) — reads `TABLEAU_TOKEN_NAME` and `TABLEAU_TOKEN_SECRET` from `.env.local`
2. **Download** the published data source as a `.tdsx` file via the Tableau REST API
3. **Extract** the `.hyper` file from inside the `.tdsx` (which is a zip archive)
4. **Store** as a dated snapshot: `YYYY-MM-DD_{source_name}.hyper` in the snapshots directory
5. **Query** using `tableauhyperapi` — SQL against the local `.hyper` file

### Tableau Auth Function

```python
import os
import requests
import xml.etree.ElementTree as ET

def tableau_sign_in(config):
    token_name = os.environ.get("TABLEAU_TOKEN_NAME", "")
    token_secret = os.environ.get("TABLEAU_TOKEN_SECRET", "")
    if not token_name or not token_secret:
        raise ValueError("TABLEAU_TOKEN_NAME and TABLEAU_TOKEN_SECRET must be set in .env.local")

    server = config["tableau"]["server"]
    api_version = config["tableau"]["api_version"]
    site_url = config["tableau"]["site_content_url"]

    url = f"{server}/api/{api_version}/auth/signin"
    xml_payload = f"""
    <tsRequest xmlns="http://tableau.com/api">
        <credentials personalAccessTokenName="{token_name}"
                     personalAccessTokenSecret="{token_secret}">
            <site contentUrl="{site_url}" />
        </credentials>
    </tsRequest>
    """
    resp = requests.post(url, data=xml_payload,
                         headers={"Content-Type": "application/xml"}, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"t": "http://tableau.com/api"}
    token = root.find(".//t:credentials", ns).attrib["token"]
    site_id = root.find(".//t:site", ns).attrib["id"]
    return token, site_id
```

### Download and Extract

```python
import zipfile
from pathlib import Path
from datetime import datetime

def download_datasource(config, source_name, token, site_id):
    source_config = config["data_sources"][source_name]
    datasource_id = source_config["datasource_id"]
    server = config["tableau"]["server"]
    api_version = config["tableau"]["api_version"]

    url = f"{server}/api/{api_version}/sites/{site_id}/datasources/{datasource_id}/content"
    resp = requests.get(url, headers={"X-Tableau-Auth": token}, timeout=120)
    resp.raise_for_status()

    snapshots_dir = Path(source_config["snapshots_dir"])
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    temp_tdsx = snapshots_dir / f"{source_name}_temp.tdsx"
    temp_tdsx.write_bytes(resp.content)
    return str(temp_tdsx)


def extract_hyper(tdsx_path, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(tdsx_path, "r") as z:
        hyper_files = [f for f in z.namelist() if f.endswith(".hyper")]
        if not hyper_files:
            raise ValueError("No .hyper file found in TDSX")
        z.extract(hyper_files[0], output_path.parent / "_temp")
        extracted = output_path.parent / "_temp" / hyper_files[0]
        extracted.rename(output_path)
    Path(tdsx_path).unlink()
    return str(output_path)
```

### Query Pattern (SQL via HyperProcess)

```python
from tableauhyperapi import HyperProcess, Telemetry, Connection

def execute_sql(hyper_file, query):
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(endpoint=hyper.endpoint, database=hyper_file) as conn:
            try:
                return conn.execute_list_query(query), None
            except Exception as e:
                return None, str(e)
```

SQL rules for `.hyper` files:
- All column names MUST be double-quoted: `"Column Name"`
- Use `LOWER()` with `LIKE` for text searches: `WHERE LOWER("Company") LIKE '%keyword%'`
- Use the shortest distinctive keyword for fuzzy matching
- Always apply default filters (check the skill's schema reference)

### Staleness and Refresh

- Each skill defines a `refresh_hours` in `config.yaml` (default: 48 hours)
- Before every query, check the latest snapshot's age
- If stale + credentials available → auto-refresh
- If stale + no credentials → use stale data with a WARNING to the user
- If refresh fails → fall back to stale cache with WARNING
- Force refresh: `python3 .cursor/skills/{skill-name}/scripts/query.py --refresh`

### Key Dependencies

`tableauhyperapi`, `requests`, `pyyaml`, `python-dotenv`

### Tableau Discovery Pattern (`--discover`)

The `--discover` flag is the self-scaffolding entry point. It connects to Tableau, downloads all data sources for a workbook, reads their schema, and auto-generates `reference.md` — so the user never has to describe column names manually.

**When to use:** During Phase 7 of the data-advisor flow (after PAT is configured and access is granted), and as a built-in flag in every Tableau-based skill created via create-skill.

**What it does:**

1. Sign in via PAT (same auth as `--refresh`)
2. Use the Tableau REST API to query the workbook by ID and list its data sources
3. Download each data source as `.tdsx`, extract the `.hyper` file
4. Open each `.hyper` with `tableauhyperapi` and read: all table names, all column names with types, and sample values (first 5 rows)
5. Auto-generate / update `reference.md` with the discovered schema
6. Print a structured JSON summary for the agent to present to the user

**Discovery script template:**

```python
#!/usr/bin/env python3
"""Discover Tableau data sources for a workbook and scaffold the schema reference.

Usage:
    python3 .cursor/skills/{skill-name}/scripts/query.py --discover

Requires: tableauhyperapi requests pyyaml python-dotenv
"""

import json
import os
import sys
import zipfile
from datetime import datetime
from pathlib import Path

import requests
import yaml
import xml.etree.ElementTree as ET
from dotenv import load_dotenv


def discover_workbook_datasources(config, token, site_id):
    """List all data sources associated with a workbook via the REST API."""
    server = config["tableau"]["server"]
    api_version = config["tableau"]["api_version"]
    workbook_id = config["tableau"].get("workbook_id", "")

    if not workbook_id:
        sys.exit("ERROR: workbook_id is not set in config.yaml.")

    url = f"{server}/api/{api_version}/sites/{site_id}/workbooks/{workbook_id}"
    resp = requests.get(url, headers={"X-Tableau-Auth": token}, timeout=30)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    ns = {"t": "http://tableau.com/api"}
    workbook_name = root.find(".//t:workbook", ns).attrib.get("name", "Unknown")

    ds_url = f"{server}/api/{api_version}/sites/{site_id}/workbooks/{workbook_id}/connections"
    ds_resp = requests.get(ds_url, headers={"X-Tableau-Auth": token}, timeout=30)
    ds_resp.raise_for_status()

    return workbook_name, ds_resp.text


def download_and_extract_datasource(config, token, site_id, datasource_id, snapshots_dir):
    """Download a single data source and extract its .hyper file."""
    server = config["tableau"]["server"]
    api_version = config["tableau"]["api_version"]

    url = f"{server}/api/{api_version}/sites/{site_id}/datasources/{datasource_id}/content"
    resp = requests.get(url, headers={"X-Tableau-Auth": token}, timeout=120)
    resp.raise_for_status()

    snapshots_dir = Path(snapshots_dir)
    snapshots_dir.mkdir(parents=True, exist_ok=True)

    temp_tdsx = snapshots_dir / f"{datasource_id}_temp.tdsx"
    temp_tdsx.write_bytes(resp.content)

    hyper_path = snapshots_dir / f"{datetime.now().strftime('%Y-%m-%d')}_{datasource_id}.hyper"
    with zipfile.ZipFile(temp_tdsx, "r") as z:
        hyper_files = [f for f in z.namelist() if f.endswith(".hyper")]
        if not hyper_files:
            temp_tdsx.unlink(missing_ok=True)
            return None
        z.extract(hyper_files[0], snapshots_dir / "_temp")
        extracted = snapshots_dir / "_temp" / hyper_files[0]
        hyper_path.unlink(missing_ok=True)
        extracted.rename(hyper_path)

    temp_tdsx.unlink(missing_ok=True)
    import shutil
    shutil.rmtree(snapshots_dir / "_temp", ignore_errors=True)

    return hyper_path


def read_hyper_schema(hyper_path):
    """Read all tables, columns, types, and sample rows from a .hyper file."""
    from tableauhyperapi import HyperProcess, Telemetry, Connection

    schema_info = []
    with HyperProcess(telemetry=Telemetry.DO_NOT_SEND_USAGE_DATA_TO_TABLEAU) as hyper:
        with Connection(endpoint=hyper.endpoint, database=str(hyper_path)) as conn:
            catalog = conn.catalog
            for schema_name in catalog.get_schema_names():
                for table in catalog.get_table_names(schema=schema_name):
                    table_def = catalog.get_table_definition(table)
                    columns = []
                    for col in table_def.columns:
                        columns.append({
                            "name": str(col.name).strip('"'),
                            "type": str(col.type),
                        })

                    sample_query = f'SELECT * FROM "{schema_name}"."{table}" LIMIT 5'
                    try:
                        rows = conn.execute_list_query(sample_query)
                        sample = [list(str(v) for v in row) for row in rows]
                    except Exception:
                        sample = []

                    schema_info.append({
                        "schema": str(schema_name),
                        "table": str(table),
                        "columns": columns,
                        "sample_rows": sample,
                        "row_count_sample": len(sample),
                    })
    return schema_info


def scaffold_reference_md(skill_dir, workbook_name, datasource_name, schema_info,
                          server, site, dashboard_url, workbook_url):
    """Auto-generate reference.md from discovered schema."""
    ref_path = Path(skill_dir) / "reference.md"
    lines = [
        f"# {workbook_name} — Reference\n",
        "## Data Source\n",
        f"- **Workbook:** {workbook_name}",
        f"- **Data source:** {datasource_name}",
        f"- **Server:** {server}",
        f"- **Site:** {site}",
        f"- **Dashboard URL:** {dashboard_url}",
        f"- **Workbook URL:** {workbook_url}",
        "",
        "---\n",
        "## Column Schema\n",
    ]

    for table_info in schema_info:
        lines.append(f"### Table: {table_info['schema']}.{table_info['table']}\n")
        lines.append("| Column name | Type | Example value |")
        lines.append("|-------------|------|---------------|")
        for i, col in enumerate(table_info["columns"]):
            example = ""
            if table_info["sample_rows"] and len(table_info["sample_rows"]) > 0:
                example = table_info["sample_rows"][0][i] if i < len(table_info["sample_rows"][0]) else ""
            lines.append(f"| {col['name']} | {col['type']} | {example} |")
        lines.append("")

    lines.extend([
        "---\n",
        "## Staleness Policy\n",
        "- Snapshot refreshed automatically if older than 48 hours (configurable in `config.yaml`)",
        "- Force refresh: `python3 .cursor/skills/{skill-name}/scripts/query.py --refresh`",
        "- Re-discover schema: `python3 .cursor/skills/{skill-name}/scripts/query.py --discover`",
        "",
    ])

    ref_path.write_text("\n".join(lines), encoding="utf-8")
    return str(ref_path)


def run_discover(config):
    """Full discovery flow: sign in, find data sources, download, read schema, scaffold."""
    from dotenv import load_dotenv
    env_path = Path(config.get("_workspace_root", ".")) / ".env.local"
    load_dotenv(env_path)

    token_name = os.environ.get("TABLEAU_TOKEN_NAME", "")
    token_secret = os.environ.get("TABLEAU_TOKEN_SECRET", "")
    if not token_name or not token_secret or token_secret == "PASTE_YOUR_TOKEN_SECRET_HERE":
        sys.exit("ERROR: Tableau credentials not configured. Fill in .env.local first.")

    # Sign in (reuse the standard auth function from the Tableau pattern)
    # ... (use tableau_sign_in from the main script)

    # Then call discover_workbook_datasources, download, read schema, scaffold
    # Output structured JSON for the agent
    pass
```

**Output format** — the `--discover` flag prints a JSON block that the agent parses:

```json
{
  "workbook_name": "Moonshot Dashboard",
  "datasource_name": "Tableau Data 5x Extract",
  "server": "https://tableauha.bcg.com",
  "site": "ProductAnalytics",
  "tables": [
    {
      "schema": "Extract",
      "table": "Extract",
      "columns": [
        {"name": "Period", "type": "TEXT"},
        {"name": "Revenue_Actual", "type": "DOUBLE"}
      ],
      "sample_rows": [["2025-12", "4500000.0"]]
    }
  ],
  "reference_md_path": ".cursor/skills/{skill-name}/reference.md",
  "snapshot_path": "x-wizard/{skill-name}/data/snapshots/2026-03-23_abc123.hyper"
}
```

The agent reads this output, presents the schema to the user in plain English, asks interpretation questions, and passes everything to create-skill.

---

## Snowflake Pattern

### config.yaml Template

```yaml
snowflake:
  account: "your-account-id"
  warehouse: "your-warehouse"
  database: "your-database"
  schema: "your-schema"

data_sources:
  your_source:
    name: "Human-Readable Name"
    query: "SELECT * FROM your_table"
    snapshots_dir: "x-wizard/{skill-name}/data/snapshots"
    refresh_hours: 48
    description: "What this data source contains"
```

### Cache Logic

1. **Connect** via `snowflake-connector-python` using credentials from `.env.local`
2. **Execute** the configured SQL query
3. **Cache** results as a dated Parquet file: `YYYY-MM-DD_{source_name}.parquet`
4. **Query** locally using pandas on the cached Parquet (no live Snowflake hits during analysis)

### Connection and Download

```python
import os
import snowflake.connector
import pandas as pd
from pathlib import Path
from datetime import datetime

def snowflake_connect():
    return snowflake.connector.connect(
        account=os.environ["SNOWFLAKE_ACCOUNT"],
        user=os.environ["SNOWFLAKE_USER"],
        password=os.environ["SNOWFLAKE_PASSWORD"],
        warehouse=os.environ.get("SNOWFLAKE_WAREHOUSE", ""),
        database=os.environ.get("SNOWFLAKE_DATABASE", ""),
        schema=os.environ.get("SNOWFLAKE_SCHEMA", ""),
    )


def refresh_snapshot(config, source_name):
    source_config = config["data_sources"][source_name]
    conn = snowflake_connect()
    try:
        cursor = conn.cursor()
        cursor.execute(source_config["query"])
        df = cursor.fetch_pandas_all()
    finally:
        conn.close()

    snapshots_dir = Path(source_config["snapshots_dir"])
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_path = snapshots_dir / f"{date_str}_{source_name}.parquet"
    df.to_parquet(output_path, engine="pyarrow", index=False)
    return str(output_path)
```

### Query Pattern (pandas on cached Parquet)

Same pandas patterns as the Excel section — `groupby`, `pivot_table`, `str.contains`, value formatting. Load from the latest snapshot:

```python
df = pd.read_parquet("x-wizard/{skill-name}/data/snapshots/YYYY-MM-DD_{source}.parquet")
```

### Staleness and Refresh

Same logic as Tableau — check snapshot age, auto-refresh if credentials present, warn if stale.

### Key Dependencies

`snowflake-connector-python`, `pandas`, `pyarrow`, `python-dotenv`

---

## Common Patterns (All Platforms)

### Credential Loading

```python
from dotenv import load_dotenv
load_dotenv(".env.local")
```

Or without `python-dotenv`:
```python
import os
# Credentials are set in .env.local and loaded by the shell or IDE
token = os.environ.get("TABLEAU_TOKEN_NAME", "")
```

Excel-based skills need no credentials.

### Snapshot Naming Convention

All snapshots follow: `YYYY-MM-DD_{source_name}.{ext}`

Examples:
- `2026-03-19_pipeline.hyper` (Tableau)
- `2026-03-19_sales.parquet` (Snowflake)

### Discovery Commands

Every data skill should support these CLI flags in its `query.py`:

| Flag | Action |
|------|--------|
| `--discover` | Connect to source, download data, read schema, and auto-scaffold `reference.md` |
| `--tables` | List available tables |
| `--columns` | Show all columns with types |
| `--snapshots` | List available snapshots with dates |
| `--refresh` | Force download a fresh snapshot |

### Two-Wave Workflow

- **Wave 1 — Data Refresh:** Download/convert fresh data. Manual trigger only — never auto-run unless data is missing.
- **Wave 2 — Querying:** Load local data and answer questions. This is the default mode.

### Name Matching

- Exact match for codes and IDs: `df["Code"] == "ABC"`
- Case-insensitive partial match for names: `df["Name"].str.contains("keyword", case=False, na=False)`
- For SQL (Tableau Hyper): `LOWER("Column") LIKE '%keyword%'`

### Value Formatting

- Millions: `$X.XM` (divide by 1e6, one decimal)
- Percentages: `X.X%` (one decimal)
- Counts: comma-separated (`1,234`)

### Output Tables

- Markdown format
- Sorted by primary metric descending (largest first)
- Total row at the bottom of grouped tables
- Top 20 rows by default; mention total count if truncated
- Bold the key answer in the lead sentence
