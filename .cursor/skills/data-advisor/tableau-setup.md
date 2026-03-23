# Tableau Setup Reference

Technical reference for the Tableau discovery and access-checking workflow. Used by the data-advisor skill during Phases 4-7 of the Tableau onboarding flow.

The discovery script is at `scripts/discover.py`.

## Platform Setup

> Detect the user's OS from the `OS Version` field in `<user_info>`.

| | Mac / Linux | Windows |
|---|---|---|
| **Python command** | `python3` | `py` |
| **Run discovery** | `python3 .cursor/skills/data-advisor/scripts/discover.py "URL"` | `py .cursor/skills/data-advisor/scripts/discover.py "URL"` |

**First-time setup:** If any import fails, install dependencies:
```
pip install requests
```

## URL Parsing

Tableau Server URLs follow this structure:
```
https://{server}/#/site/{site_content_url}/{object_type}/{vizportal_id}/{section}
```

Extract these components:

| Component | Regex / Position | Example |
|---|---|---|
| `server` | Host | `tableau.yourcompany.com` |
| `site_content_url` | After `/site/` | `YourSiteName`, `FinanceTeam` |
| `object_type` | After site | `workbooks`, `views`, `datasources` |
| `vizportal_id` | Numeric ID | `8976` |
| `section` | Trailing path | `datasources`, `views`, (empty) |

**Known URL patterns:**

| Pattern | Meaning | Resolution |
|---|---|---|
| `/#/site/{site}/workbooks/{id}/datasources` | Datasources tab of a workbook | Direct — vizportal ID resolves via Metadata API |
| `/#/site/{site}/workbooks/{id}/views` | Views tab of a workbook | Direct — same as above |
| `/#/site/{site}/views/{wbContentUrl}/{viewName}?:iid=...` | Specific dashboard view (most commonly shared!) | Indirect — strip query params, resolve view → parent workbook via REST API, then Metadata API by LUID |
| `/#/site/{site}/datasources/{id}` | Published datasource detail page | Direct — vizportal ID resolves via Metadata API |
| `/#/site/{site}/datasources` | All datasources on the site | N/A — no specific resource to discover |

**View URLs are the most common** — users share the dashboard link, not the workbook admin page. The script handles both transparently.

## Authentication

Load PAT credentials from `.env.local` (project root) and sign in to the **target site** extracted from the URL.

```bash
curl -s -X POST "https://{server}/api/3.19/auth/signin" \
  -H "Content-Type: application/json" \
  -d '{
    "credentials": {
      "personalAccessTokenName": "'$TABLEAU_TOKEN_NAME'",
      "personalAccessTokenSecret": "'$TABLEAU_TOKEN_SECRET'",
      "site": { "contentUrl": "{site_from_url}" }
    }
  }'
```

**Critical:** The site in the sign-in request MUST match the site from the URL. The PAT may be scoped to one site — if sign-in fails with 401, the user's PAT doesn't have access to that site.

Extract from response:
- `token` — for all subsequent API calls (`X-Tableau-Auth` header)
- `site_id` — LUID of the site
- `user_id` — LUID of the authenticated user

## Resolve View URLs (if applicable)

If the URL is a view (`/views/WorkbookContentUrl/ViewName`), resolve to the parent workbook first:

1. Strip query params (`?:iid=1`, `?:embed=y`, etc.)
2. Split the path: `SalesDashboard/QuarterlyView` → workbook content URL = `SalesDashboard`, view name = `QuarterlyView`
3. List all views via REST API and match by `contentUrl`:

```bash
curl -s "https://{server}/api/3.19/sites/{site_id}/views?pageSize=1000" \
  -H "X-Tableau-Auth: {token}" -H "Accept: application/json"
```

4. Each view in the response includes `workbook.id` (the workbook LUID)
5. Once you have the LUID, proceed to workbook discovery using `discover_workbook_by_luid` instead of vizportal ID

This means **any dashboard URL a user shares will work** — the script transparently resolves it to the parent workbook and runs the same discovery.

## Discover Workbook Details

The vizportal ID in URLs (e.g., `8976`) is NOT the REST API LUID. Use the **Metadata GraphQL API** to resolve it:

```bash
curl -s -X POST "https://{server}/api/metadata/graphql" \
  -H "X-Tableau-Auth: {token}" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "{ workbooks(filter: {vizportalUrlId: \"8976\"}) { id name luid vizportalUrlId projectName owner { name } createdAt updatedAt description uri embeddedDatasources { id name hasExtracts upstreamTables { name schema database { name connectionType } } } } }"
  }'
```

This returns:
- Workbook name, LUID, project, owner, created/updated dates
- All embedded datasources with their upstream table/connection info
- Whether extracts exist (`.hyper` files baked in)

**If the URL points to a published datasource** (not a workbook), use:
```graphql
{ publishedDatasources(filter: {vizportalUrlId: "1234"}) {
    id name luid vizportalUrlId
    owner { name }
    hasExtracts
    upstreamTables { name schema database { name connectionType } }
  }
}
```

## Check User Access Rights

**Get site role:**
```bash
curl -s -X GET "https://{server}/api/3.19/sites/{site_id}/users/{user_id}" \
  -H "X-Tableau-Auth: {token}" \
  -H "Accept: application/json"
```

Site roles determine baseline capabilities:

| Site Role | Can View | Can Download WB | Can Download DS | Can Query Permissions |
|---|---|---|---|---|
| Viewer | Yes | No | No | No |
| Explorer | Yes | Maybe* | Maybe* | No |
| Explorer (Can Publish) | Yes | Maybe* | Maybe* | No |
| Creator | Yes | Maybe* | Maybe* | Maybe* |
| Site Administrator Explorer | Yes | Yes | Yes | Yes |
| Site Administrator Creator | Yes | Yes | Yes | Yes |

*Depends on per-resource permission grants.

**Test actual download access** (faster than parsing ACLs):

```bash
# Test workbook download
curl -s -o /dev/null -w "%{http_code}" \
  "https://{server}/api/3.19/sites/{site_id}/workbooks/{wb_luid}/content" \
  -H "X-Tableau-Auth: {token}"

# Test published datasource download (if applicable)
curl -s -o /dev/null -w "%{http_code}" \
  "https://{server}/api/3.19/sites/{site_id}/datasources/{ds_luid}/content" \
  -H "X-Tableau-Auth: {token}"
```

| HTTP Status | Meaning |
|---|---|
| 200 | Download allowed — proceed |
| 403 | Forbidden — insufficient permissions |
| 404 | Resource not found (embedded DS can't be downloaded standalone) |

**Test view access and data export:**
```bash
# List views (tests basic read access)
curl -s "https://{server}/api/3.19/sites/{site_id}/workbooks/{wb_luid}/views" \
  -H "X-Tableau-Auth: {token}" -H "Accept: application/json"

# Test CSV export from a view
curl -s -o /dev/null -w "%{http_code}" \
  "https://{server}/api/3.19/sites/{site_id}/views/{view_id}/data" \
  -H "X-Tableau-Auth: {token}"
```

**Try querying permissions** (usually only works for admins/owners):
```bash
curl -s "https://{server}/api/3.19/sites/{site_id}/workbooks/{wb_luid}/permissions" \
  -H "X-Tableau-Auth: {token}" -H "Accept: application/json"
```

## Check for Published Datasource

An embedded datasource (baked into a `.twbx`) cannot be downloaded separately. Check whether the same data is also published as a standalone datasource:

```bash
curl -s "https://{server}/api/3.19/sites/{site_id}/datasources?pageSize=1000" \
  -H "X-Tableau-Auth: {token}" -H "Accept: application/json"
```

Search by name (fuzzy match against the embedded datasource name). If found, the published version can potentially be downloaded directly — much simpler than extracting from a workbook.

## Discovery Output Format

The script prints structured JSON:

```json
{
  "url": "https://tableau.yourcompany.com/#/site/YourSiteName/workbooks/123/datasources",
  "server": "tableau.yourcompany.com",
  "site": "YourSiteName",
  "workbook": {
    "name": "Sales Dashboard",
    "luid": "abc-123",
    "owner": "jane.smith@company.com",
    "project": "Analytics"
  },
  "datasources": [
    {
      "name": "Sales Extract",
      "type": "embedded",
      "has_extracts": true
    }
  ],
  "access": {
    "site_role": "Explorer",
    "can_download_workbook": true,
    "can_download_datasource": false,
    "datasource_is_published": false
  },
  "recommendation": "EMBEDDED DATASOURCE — but you can download the workbook..."
}
```

## Access Scenarios and Recommendations

### Decision Tree

```
Is the datasource published separately?
├─ YES → Can you download it? (HTTP 200 on /datasources/{id}/content)
│   ├─ YES → Download directly. Add to config.yaml, set up auto-refresh.
│   └─ NO  → Ask owner for "Download" permission on the published datasource.
│            Or ask site admin to upgrade your role to Explorer+.
│
└─ NO (embedded in workbook) → Can you download the workbook? (HTTP 200 on /workbooks/{id}/content)
    ├─ YES → Download .twbx, extract .hyper from the zip archive.
    │        Consider asking owner to publish the DS separately for cleaner refresh.
    └─ NO  → Three options (pick based on relationship with owner):
         ├─ Option A: Ask owner to PUBLISH the datasource separately on this site.
         │            Then request Download permission.
         │            Best for: recurring need, automated refresh.
         ├─ Option B: Ask owner to grant you "Download/Save a Copy" on the workbook.
         │            + ask site admin for Explorer role if you're Viewer.
         │            Best for: one-time or infrequent need.
         └─ Option C: Ask owner to send the .hyper file directly (email/Teams/Slack).
                      Best for: quick one-off analysis, no admin overhead.
```

### Email Templates (used by Phase 6 of data-advisor SKILL.md)

**Scenario: Need published datasource access**
> Hi {owner}, could you give me download access to the "{datasource_name}" datasource on Tableau ({site} site)? I'm automating the lookups I already do manually. Read + download only — nothing gets modified. My account is {user_email}. Happy to chat if you have questions.

**Scenario: Need datasource published separately**
> Hi {owner}, I'd like to query the data behind the "{workbook_name}" workbook. The datasource ({ds_name}) is currently embedded. Would it be possible to publish it as a standalone datasource on the {site} site so I can set up automated downloads? If you'd prefer not to publish it, even a one-time export of the .hyper file would work.

**Scenario: Need role upgrade**
> Hi {admin}, could you upgrade my site role on the {site} Tableau site from Viewer to Explorer? I need to download datasources for automated reporting. My account: {user_email}.

## API Reference

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/3.19/auth/signin` | POST | Authenticate with PAT |
| `/api/metadata/graphql` | POST | Resolve vizportal IDs, get rich metadata |
| `/api/3.19/sites/{sid}/users/{uid}` | GET | Check site role |
| `/api/3.19/sites/{sid}/workbooks/{wid}` | GET | Workbook metadata |
| `/api/3.19/sites/{sid}/workbooks/{wid}/views` | GET | List views in workbook |
| `/api/3.19/sites/{sid}/workbooks/{wid}/connections` | GET | Datasource connections |
| `/api/3.19/sites/{sid}/workbooks/{wid}/permissions` | GET | Permission ACLs (admin only) |
| `/api/3.19/sites/{sid}/workbooks/{wid}/content` | GET | Download workbook (.twbx) |
| `/api/3.19/sites/{sid}/datasources` | GET | List published datasources |
| `/api/3.19/sites/{sid}/datasources/{did}/content` | GET | Download published datasource |
| `/api/3.19/sites/{sid}/views/{vid}/data` | GET | Export view data as CSV |
