"""
Tableau Discovery
=================
Discover workbook metadata, datasources, and access rights from a Tableau Server URL.

Usage:
    python3 .cursor/skills/data-advisor/scripts/discover.py "https://tableau.yourcompany.com/#/site/..."

Requires TABLEAU_TOKEN_NAME and TABLEAU_TOKEN_SECRET in .env.local or environment.
"""

from __future__ import annotations

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import requests

WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
API_VERSION = "3.19"


# ---------------------------------------------------------------------------
# URL parsing
# ---------------------------------------------------------------------------

@dataclass
class TableauUrl:
    server: str
    site_content_url: str
    object_type: str          # workbooks, views, datasources
    vizportal_id: str         # numeric ID from the URL (may be empty for views)
    section: str              # trailing segment (datasources, views, "")
    view_content_url: str     # for view URLs: workbookContentUrl/viewName
    raw: str

    @property
    def base_url(self) -> str:
        return f"https://{self.server}"


_URL_RE = re.compile(
    r"https?://(?P<server>[^/]+)"
    r"/\#/site/(?P<site>[^/]+)"
    r"/(?P<obj_type>workbooks|views|datasources)"
    r"(?:/(?P<rest>[^?]+))?",
    re.IGNORECASE,
)


def parse_url(url: str) -> TableauUrl:
    url_clean = url.strip().split("?")[0]

    m = _URL_RE.match(url_clean)
    if not m:
        raise ValueError(f"Cannot parse Tableau URL: {url}")

    server = m.group("server")
    site = m.group("site")
    obj_type = m.group("obj_type")
    rest = m.group("rest") or ""

    parts = [p for p in rest.split("/") if p]

    vizportal_id = ""
    section = ""
    view_content_url = ""

    if obj_type == "views":
        view_content_url = "/".join(parts)
    elif parts:
        vizportal_id = parts[0]
        section = parts[1] if len(parts) > 1 else ""

    return TableauUrl(
        server=server,
        site_content_url=site,
        object_type=obj_type,
        vizportal_id=vizportal_id,
        section=section,
        view_content_url=view_content_url,
        raw=url,
    )


# ---------------------------------------------------------------------------
# Authentication
# ---------------------------------------------------------------------------

@dataclass
class AuthContext:
    token: str
    site_id: str
    user_id: str
    server: str

    @property
    def base_api(self) -> str:
        return f"https://{self.server}/api/{API_VERSION}"

    def headers(self, accept_json: bool = True) -> dict:
        h = {"X-Tableau-Auth": self.token}
        if accept_json:
            h["Accept"] = "application/json"
        return h


def load_env():
    """Load .env.local from workspace root if env vars aren't already set."""
    env_file = WORKSPACE_ROOT / ".env.local"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, _, val = line.partition("=")
                val = val.strip().strip('"').strip("'")
                os.environ.setdefault(key.strip(), val)


def sign_in(server: str, site_content_url: str) -> AuthContext:
    token_name = os.environ.get("TABLEAU_TOKEN_NAME", "")
    token_secret = os.environ.get("TABLEAU_TOKEN_SECRET", "")

    if not token_name or not token_secret:
        raise ValueError(
            "TABLEAU_TOKEN_NAME and TABLEAU_TOKEN_SECRET must be set. "
            "Add them to .env.local or export in your shell."
        )

    url = f"https://{server}/api/{API_VERSION}/auth/signin"
    xml_payload = f"""<tsRequest xmlns="http://tableau.com/api">
        <credentials personalAccessTokenName="{token_name}"
                     personalAccessTokenSecret="{token_secret}">
            <site contentUrl="{site_content_url}" />
        </credentials>
    </tsRequest>"""

    resp = requests.post(
        url,
        data=xml_payload,
        headers={"Content-Type": "application/xml"},
        timeout=30,
    )
    resp.raise_for_status()

    ns = {"t": "http://tableau.com/api"}
    root = ET.fromstring(resp.text)
    creds_el = root.find(".//t:credentials", ns)
    site_el = root.find(".//t:site", ns)
    user_el = root.find(".//t:user", ns)

    return AuthContext(
        token=creds_el.attrib["token"],
        site_id=site_el.attrib["id"],
        user_id=user_el.attrib["id"],
        server=server,
    )


# ---------------------------------------------------------------------------
# Metadata API (GraphQL)
# ---------------------------------------------------------------------------

def graphql_query(auth: AuthContext, query: str) -> dict:
    url = f"https://{auth.server}/api/metadata/graphql"
    resp = requests.post(
        url,
        json={"query": query},
        headers={"X-Tableau-Auth": auth.token, "Content-Type": "application/json"},
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def discover_workbook(auth: AuthContext, vizportal_id: str) -> Optional[dict]:
    gql = (
        '{ workbooks(filter: {vizportalUrlId: "' + vizportal_id + '"}) {'
        " id name luid vizportalUrlId projectName"
        " owner { name }"
        " createdAt updatedAt description uri"
        " embeddedDatasources {"
        "   id name hasExtracts"
        "   upstreamTables { name schema database { name connectionType } }"
        " }"
        "} }"
    )
    result = graphql_query(auth, gql)
    workbooks = result.get("data", {}).get("workbooks", [])
    return workbooks[0] if workbooks else None


def discover_workbook_by_luid(auth: AuthContext, luid: str) -> Optional[dict]:
    gql = (
        '{ workbooks(filter: {luid: "' + luid + '"}) {'
        " id name luid vizportalUrlId projectName"
        " owner { name }"
        " createdAt updatedAt description uri"
        " embeddedDatasources {"
        "   id name hasExtracts"
        "   upstreamTables { name schema database { name connectionType } }"
        " }"
        "} }"
    )
    result = graphql_query(auth, gql)
    workbooks = result.get("data", {}).get("workbooks", [])
    return workbooks[0] if workbooks else None


def resolve_view_to_workbook_luid(auth: AuthContext, view_content_url: str) -> Optional[str]:
    """
    Resolve a view content URL (e.g. 'SalesDashboard/QuarterlyView')
    to its parent workbook LUID.

    Strategy: list all views on the site, match by contentUrl.
    Falls back to matching workbook contentUrl from the first path segment.
    """
    wb_content_url = view_content_url.split("/")[0]

    url = f"{auth.base_api}/sites/{auth.site_id}/views?pageSize=1000"
    resp = requests.get(url, headers=auth.headers(), timeout=30)
    if resp.status_code != 200:
        return None

    views = resp.json().get("views", {}).get("view", [])

    for view in views:
        if view.get("contentUrl", "") == view_content_url:
            return view.get("workbook", {}).get("id")

    for view in views:
        if view.get("contentUrl", "").startswith(wb_content_url + "/"):
            return view.get("workbook", {}).get("id")

    return None


def discover_published_datasource(auth: AuthContext, vizportal_id: str) -> Optional[dict]:
    gql = (
        '{ publishedDatasources(filter: {vizportalUrlId: "' + vizportal_id + '"}) {'
        " id name luid vizportalUrlId"
        " owner { name }"
        " hasExtracts description"
        " upstreamTables { name schema database { name connectionType } }"
        "} }"
    )
    result = graphql_query(auth, gql)
    dss = result.get("data", {}).get("publishedDatasources", [])
    return dss[0] if dss else None


# ---------------------------------------------------------------------------
# REST API checks
# ---------------------------------------------------------------------------

def get_user_role(auth: AuthContext) -> dict:
    url = f"{auth.base_api}/sites/{auth.site_id}/users/{auth.user_id}"
    resp = requests.get(url, headers=auth.headers(), timeout=15)
    resp.raise_for_status()
    return resp.json().get("user", {})


def get_workbook_views(auth: AuthContext, wb_luid: str) -> list:
    url = f"{auth.base_api}/sites/{auth.site_id}/workbooks/{wb_luid}/views"
    resp = requests.get(url, headers=auth.headers(), timeout=15)
    if resp.status_code != 200:
        return []
    return resp.json().get("views", {}).get("view", [])


def get_workbook_connections(auth: AuthContext, wb_luid: str) -> list:
    url = f"{auth.base_api}/sites/{auth.site_id}/workbooks/{wb_luid}/connections"
    resp = requests.get(url, headers=auth.headers(), timeout=15)
    if resp.status_code != 200:
        return []
    return resp.json().get("connections", {}).get("connection", [])


def test_download(auth: AuthContext, resource_type: str, luid: str) -> int:
    """Test download access. Returns HTTP status code."""
    url = f"{auth.base_api}/sites/{auth.site_id}/{resource_type}/{luid}/content"
    resp = requests.get(url, headers=auth.headers(accept_json=False), timeout=15, stream=True)
    resp.close()
    return resp.status_code


def test_csv_export(auth: AuthContext, view_id: str) -> int:
    url = f"{auth.base_api}/sites/{auth.site_id}/views/{view_id}/data"
    resp = requests.get(url, headers=auth.headers(accept_json=False), timeout=15, stream=True)
    resp.close()
    return resp.status_code


def test_permissions(auth: AuthContext, resource_type: str, luid: str) -> tuple[int, dict]:
    url = f"{auth.base_api}/sites/{auth.site_id}/{resource_type}/{luid}/permissions"
    resp = requests.get(url, headers=auth.headers(), timeout=15)
    if resp.status_code == 200:
        return 200, resp.json()
    return resp.status_code, {}


def search_published_datasources(auth: AuthContext, name_keyword: str) -> list:
    """Search published datasources by name (case-insensitive substring match)."""
    url = f"{auth.base_api}/sites/{auth.site_id}/datasources?pageSize=1000"
    resp = requests.get(url, headers=auth.headers(), timeout=30)
    if resp.status_code != 200:
        return []
    dss = resp.json().get("datasources", {}).get("datasource", [])
    keyword = name_keyword.lower()
    return [d for d in dss if keyword in d.get("name", "").lower()]


# ---------------------------------------------------------------------------
# Recommendation engine
# ---------------------------------------------------------------------------

@dataclass
class AccessRights:
    site_role: str = ""
    can_view: bool = False
    can_download_workbook: bool = False
    can_download_datasource: bool = False
    can_export_csv: bool = False
    can_query_permissions: bool = False
    datasource_is_published: bool = False
    published_ds_luid: str = ""


def recommend(rights: AccessRights, workbook_name: str, ds_name: str,
              owner: str, site: str, user_email: str) -> str:
    lines = []

    if rights.datasource_is_published and rights.can_download_datasource:
        lines.append("READY TO DOWNLOAD: The datasource is published and you have download access.")
        lines.append(f"Add it to config.yaml with datasource_id: \"{rights.published_ds_luid}\" and set up auto-refresh.")
        return "\n".join(lines)

    if rights.datasource_is_published and not rights.can_download_datasource:
        lines.append("PUBLISHED BUT NO DOWNLOAD ACCESS.")
        lines.append(f"Ask {owner} to grant you Download permission on the \"{ds_name}\" published datasource.")
        if rights.site_role == "Viewer":
            lines.append(f"Also ask site admin to upgrade your role from Viewer to Explorer on the {site} site.")
        if rights.can_export_csv:
            lines.append(f"WORKAROUND: CSV export from views IS available — you can pull the data as CSV right now (limited to what the view shows).")
        return "\n".join(lines)

    if not rights.datasource_is_published and rights.can_download_workbook:
        lines.append("EMBEDDED DATASOURCE — but you can download the workbook.")
        lines.append("Download the .twbx file and extract the .hyper from inside (it's a zip archive).")
        lines.append(f"Consider asking {owner} to publish \"{ds_name}\" as a standalone datasource for cleaner auto-refresh.")
        return "\n".join(lines)

    lines.append("EMBEDDED DATASOURCE — NO DOWNLOAD ACCESS. Options:")
    lines.append(f"  A) Ask {owner} to publish \"{ds_name}\" as a standalone datasource on {site},")
    lines.append(f"     then request Download permission. Best for recurring automated pulls.")
    lines.append(f"  B) Ask {owner} for Download/Save a Copy on \"{workbook_name}\",")
    if rights.site_role == "Viewer":
        lines.append(f"     + ask site admin to upgrade you from Viewer to Explorer on {site}.")
    lines.append(f"     Best for occasional manual downloads.")
    lines.append(f"  C) Ask {owner} to send the .hyper file directly (email/Teams/Slack).")
    lines.append(f"     Best for one-off analysis.")
    if rights.can_export_csv:
        lines.append(f"  IMMEDIATE: CSV export from views IS available — you can pull visible data as CSV right now.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main discovery flow
# ---------------------------------------------------------------------------

def discover(url: str) -> dict:
    parsed = parse_url(url)
    load_env()

    id_label = parsed.vizportal_id or parsed.view_content_url
    print(f"Parsed URL: site={parsed.site_content_url}, type={parsed.object_type}, id={id_label}")
    print(f"Signing in to {parsed.server} (site: {parsed.site_content_url})...")
    auth = sign_in(parsed.server, parsed.site_content_url)
    print("Authenticated successfully.\n")

    result = {
        "url": parsed.raw,
        "server": parsed.server,
        "site": parsed.site_content_url,
        "object_type": parsed.object_type,
        "vizportal_id": parsed.vizportal_id,
    }

    user_info = get_user_role(auth)
    site_role = user_info.get("siteRole", "Unknown")
    user_email = user_info.get("name", user_info.get("email", "unknown"))
    result["user"] = {"email": user_email, "site_role": site_role}
    print(f"User: {user_email} | Site Role: {site_role}")

    rights = AccessRights(site_role=site_role)

    if parsed.object_type == "views" and parsed.view_content_url:
        print(f"\nResolving view URL \"{parsed.view_content_url}\" to parent workbook...")
        wb_luid = resolve_view_to_workbook_luid(auth, parsed.view_content_url)
        if wb_luid:
            print(f"Found workbook LUID: {wb_luid}")
            result["resolved_from_view"] = parsed.view_content_url
            parsed.object_type = "workbooks"
            parsed.vizportal_id = f"__luid__{wb_luid}"
        else:
            print("ERROR: Could not resolve view to parent workbook.")
            result["error"] = f"View '{parsed.view_content_url}' not found or not accessible"
            return result

    if parsed.object_type == "workbooks" and parsed.vizportal_id:
        if parsed.vizportal_id.startswith("__luid__"):
            wb_luid_direct = parsed.vizportal_id.replace("__luid__", "")
            print(f"\nQuerying Metadata API for workbook luid={wb_luid_direct}...")
            wb = discover_workbook_by_luid(auth, wb_luid_direct)
        else:
            print(f"\nQuerying Metadata API for workbook vizportalId={parsed.vizportal_id}...")
            wb = discover_workbook(auth, parsed.vizportal_id)
        if not wb:
            print("ERROR: Workbook not found via Metadata API.")
            result["error"] = "Workbook not found"
            return result

        wb_luid = wb["luid"]
        wb_name = wb["name"]
        owner = wb.get("owner", {}).get("name", "unknown")

        result["workbook"] = {
            "name": wb_name,
            "luid": wb_luid,
            "vizportal_id": wb.get("vizportalUrlId"),
            "project": wb.get("projectName"),
            "owner": owner,
            "created": wb.get("createdAt"),
            "updated": wb.get("updatedAt"),
            "description": wb.get("description", ""),
        }
        print(f"Found: \"{wb_name}\" | Owner: {owner} | Project: {wb.get('projectName')}")

        embedded_ds = wb.get("embeddedDatasources", [])
        ds_list = []
        for ds in embedded_ds:
            ds_info = {
                "name": ds["name"],
                "type": "embedded",
                "has_extracts": ds.get("hasExtracts", False),
                "upstream_tables": ds.get("upstreamTables", []),
            }
            ds_list.append(ds_info)
            print(f"  Datasource: \"{ds['name']}\" (embedded, extracts={ds_info['has_extracts']})")
            for ut in ds_info["upstream_tables"]:
                db = ut.get("database", {})
                print(f"    └─ {db.get('name', '?')} ({db.get('connectionType', '?')}) → {ut.get('schema', '?')}.{ut.get('name', '?')}")

        result["datasources"] = ds_list

        views = get_workbook_views(auth, wb_luid)
        rights.can_view = len(views) > 0
        result["views"] = [{"name": v.get("name"), "id": v.get("id")} for v in views]
        print(f"\nViews: {len(views)} found" + (f" ({', '.join(v['name'] for v in views)})" if views else ""))

        print("\nTesting access rights...")

        dl_wb = test_download(auth, "workbooks", wb_luid)
        rights.can_download_workbook = dl_wb == 200
        print(f"  Download workbook: HTTP {dl_wb} ({'OK' if dl_wb == 200 else 'DENIED'})")

        perm_status, _ = test_permissions(auth, "workbooks", wb_luid)
        rights.can_query_permissions = perm_status == 200
        print(f"  Query permissions: HTTP {perm_status} ({'OK' if perm_status == 200 else 'DENIED'})")

        if views:
            csv_status = test_csv_export(auth, views[0]["id"])
            rights.can_export_csv = csv_status == 200
            print(f"  Export CSV: HTTP {csv_status} ({'OK' if csv_status == 200 else 'DENIED'})")

        for ds in ds_list:
            words = [w for w in ds["name"].split() if len(w) > 2 and w.lower() not in ("the", "and", "for", "data", "tableau", "extract")]
            search_term = " ".join(words[:3]) if words else ds["name"]
            published = search_published_datasources(auth, search_term)
            if not published and words:
                published = search_published_datasources(auth, words[0])
            if published:
                rights.datasource_is_published = True
                rights.published_ds_luid = published[0].get("id", "")
                ds["published_match"] = {
                    "name": published[0].get("name"),
                    "id": published[0].get("id"),
                }
                dl_ds = test_download(auth, "datasources", rights.published_ds_luid)
                rights.can_download_datasource = dl_ds == 200
                print(f"  Published DS match: \"{published[0].get('name')}\" → download HTTP {dl_ds}")
            else:
                print(f"  No published datasource found matching \"{ds['name']}\"")

        result["access"] = asdict(rights)

        primary_ds_name = ds_list[0]["name"] if ds_list else "unknown"
        rec = recommend(rights, wb_name, primary_ds_name, owner, parsed.site_content_url, user_email)
        result["recommendation"] = rec
        print(f"\n{'='*60}")
        print("RECOMMENDATION:")
        print(rec)
        print(f"{'='*60}")

    elif parsed.object_type == "datasources" and parsed.vizportal_id:
        print(f"\nQuerying Metadata API for published datasource vizportalId={parsed.vizportal_id}...")
        ds = discover_published_datasource(auth, parsed.vizportal_id)
        if not ds:
            print("ERROR: Published datasource not found via Metadata API.")
            result["error"] = "Datasource not found"
            return result

        ds_luid = ds["luid"]
        ds_name = ds["name"]
        owner = ds.get("owner", {}).get("name", "unknown")

        result["datasource"] = {
            "name": ds_name,
            "luid": ds_luid,
            "vizportal_id": ds.get("vizportalUrlId"),
            "type": "published",
            "owner": owner,
            "has_extracts": ds.get("hasExtracts", False),
            "upstream_tables": ds.get("upstreamTables", []),
        }
        print(f"Found: \"{ds_name}\" | Owner: {owner}")

        dl_ds = test_download(auth, "datasources", ds_luid)
        rights.datasource_is_published = True
        rights.published_ds_luid = ds_luid
        rights.can_download_datasource = dl_ds == 200
        print(f"  Download: HTTP {dl_ds} ({'OK' if dl_ds == 200 else 'DENIED'})")

        result["access"] = asdict(rights)
        rec = recommend(rights, "", ds_name, owner, parsed.site_content_url, user_email)
        result["recommendation"] = rec
        print(f"\n{'='*60}")
        print("RECOMMENDATION:")
        print(rec)
        print(f"{'='*60}")

    else:
        print(f"Object type '{parsed.object_type}' with id '{parsed.vizportal_id}' — manual inspection needed.")
        result["note"] = "URL type not fully supported for automated discovery. Use REST API manually."

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    if len(sys.argv) < 2:
        print("Usage: python discover.py <tableau_url>")
        print('Example: python discover.py "https://tableau.yourcompany.com/#/site/YourSiteName/workbooks/123/datasources"')
        sys.exit(1)

    url = sys.argv[1]

    try:
        result = discover(url)
    except requests.HTTPError as e:
        print(f"\nHTTP Error: {e}")
        print("Check that your PAT has access to this site.")
        sys.exit(1)
    except ValueError as e:
        print(f"\nError: {e}")
        sys.exit(1)

    print("\n--- JSON Output ---")
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
