#!/usr/bin/env python3
"""Fetch Omni dashboard(s) and everything the migration parses as source of truth.

Step 1 of the Omni -> Hex migration flow. Authenticates to the Omni REST API with an
API key (Bearer), then either lists dashboards (with view counts, for triage) or
downloads specific ones. For each dashboard it saves:

    omni_exports/<dashboard>/
        document.json             # the documents-list record (owner, folder, views, url)
        dashboard.v2.json         # GET /v2/documents/{id}: tiles, vis config, controls,
                                  #   layout containers (422 on classic-layout dashboards)
        queries.json              # GET /v1/documents/{id}/queries: every saved tile query
        export.json               # GET /unstable/documents/{id}/export (org API key only):
                                  #   dashboard + workbookModel + queryModels + palettes
        models/<model_id>/        # model YAML files for every model the dashboard touches
            _meta.json            #   (shared = combined; workbook/query = extension layer)
            <file>.yaml
        connections.json          # GET /v1/connections (dialect + database per connection)
        sql/<key>__<tile>.sql     # Omni's OWN generated SQL per tile (query/run planOnly)
        results/<key>__<tile>.json  # (--results) Omni's result rows per tile, for parity
        dashboard.png             # (--png) Omni's rendered dashboard, for visual QA

The tile query JSON + model YAML are the definition; the generated SQL is Omni's own
compilation of them and the strongest reference for the SQL-fidelity gate. See
reference/omni-semantics.md.

Usage:
  python scripts/omni_fetch.py --list                       # every dashboard, by views
  python scripts/omni_fetch.py --list --folder "Sales"      # filter by folder path
  python scripts/omni_fetch.py --dashboard abc123           # one dashboard by identifier
  python scripts/omni_fetch.py --name "Revenue Overview"    # by exact name
  python scripts/omni_fetch.py --folder "Sales"             # every dashboard in a folder
  python scripts/omni_fetch.py --dashboard abc123 --results --png

Credentials are read from credentials/omni.env (gitignored). Standard library only;
if `pyarrow` is installed, Arrow result payloads are also decoded to JSON rows.

NOTE ON THE OMNI API: /unstable/* endpoints are beta and may change; the dashboard
export and v2 document shapes are only partly typed in the OpenAPI spec. The script
saves RAW JSON for every resource so nothing is lost if a field moves. When a call
fails, check https://docs.omni.co/api/openapi.yaml (you have WebFetch).
"""
import argparse
import base64
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "credentials" / "omni.env"
EXPORT_DIR = REPO_ROOT / "omni_exports"
MIN_INTERVAL = 1.05  # Omni rate limit is 60 requests/minute


def load_env(path: Path) -> dict:
    if not path.exists():
        sys.exit(
            f"Missing {path}.\n"
            f"Copy credentials/omni.env.example to credentials/omni.env "
            f"and fill in your Omni instance URL + API key."
        )
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip()
    missing = [k for k in ("OMNI_BASE_URL", "OMNI_API_KEY") if not env.get(k)]
    if missing:
        sys.exit(f"omni.env is missing values for: {', '.join(missing)}")
    return env


class ApiError(RuntimeError):
    def __init__(self, code, url, body):
        super().__init__(f"HTTP {code} for {url}\n{body[:400]}")
        self.code = code
        self.body = body


class Omni:
    def __init__(self, env: dict):
        base = env["OMNI_BASE_URL"].rstrip("/")
        self.api = base if base.endswith("/api") else base + "/api"
        self.auth = "Bearer " + env["OMNI_API_KEY"]
        self._last = 0.0

    def _request(self, method, path, params=None, body=None, raw=False):
        wait = MIN_INTERVAL - (time.monotonic() - self._last)
        if wait > 0:
            time.sleep(wait)
        url = f"{self.api}{path}"
        if params:
            url += "?" + urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": self.auth,
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "omni-to-hex-migration/1.0",
        })
        for attempt in range(4):
            try:
                with urllib.request.urlopen(req, timeout=120) as resp:
                    self._last = time.monotonic()
                    payload = resp.read()
                    return payload if raw else payload.decode()
            except urllib.error.HTTPError as e:
                self._last = time.monotonic()
                text = e.read().decode(errors="replace")
                if e.code == 429 and attempt < 3:
                    time.sleep(15 * (attempt + 1))
                    continue
                raise ApiError(e.code, url, text) from None

    def get(self, path, **params):
        return json.loads(self._request("GET", path, params))

    def post(self, path, body, **params):
        return self._request("POST", path, params, body)

    # --- content ---
    def documents(self, folder_id=None):
        out, cursor = [], None
        while True:
            page = self.get("/v1/documents", pageSize=100, cursor=cursor, folderId=folder_id,
                            include="_count,labels", sortField="visits", sortDirection="desc")
            out.extend(page.get("records", []))
            info = page.get("pageInfo") or {}
            cursor = info.get("nextCursor")
            if not info.get("hasNextPage") or not cursor:
                return out

    # --- query run (NDJSON or JSON depending on resultType) ---
    def run_query(self, body):
        try:
            text = self.post("/v1/query/run", body)
        except ApiError as e:
            if e.code != 408:
                raise
            text = e.body
        lines = parse_ndjson(text)
        pending = []
        for ln in lines:
            if isinstance(ln, dict) and ln.get("remaining_job_ids"):
                pending = ln["remaining_job_ids"]
        tries = 0
        while pending and tries < 20:
            tries += 1
            more = parse_ndjson(self._request("GET", "/v1/query/wait",
                                              {"jobIds": ",".join(pending)}))
            lines.extend(more)
            pending = []
            for ln in more:
                if isinstance(ln, dict) and ln.get("remaining_job_ids"):
                    pending = ln["remaining_job_ids"]
        return lines


def parse_ndjson(text):
    text = (text or "").strip()
    if not text:
        return []
    try:
        return [json.loads(text)]          # a single JSON document (or an array of rows)
    except json.JSONDecodeError:
        pass
    out = []
    for line in text.splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                out.append({"_unparsed": line[:500]})
    return out


def job_lines(lines):
    return [ln for ln in lines if isinstance(ln, dict) and "job_id" in ln and "status" in ln]


def generated_sql(lines):
    for ln in lines:
        if not isinstance(ln, dict):
            continue
        for summary in (ln.get("summary"), ln):
            if isinstance(summary, dict):
                for key in ("display_sql", "sql"):
                    if summary.get(key):
                        return summary[key]
    return None


def decode_arrow(b64):
    try:
        import io
        import pyarrow.ipc as ipc
    except ImportError:
        return None
    reader = ipc.open_stream(io.BytesIO(base64.b64decode(b64)))
    return reader.read_all().to_pylist()


def safe(name, n=80):
    s = re.sub(r"[^A-Za-z0-9 _-]", "_", name or "").strip()
    return s[:n] or "untitled"


def write_json(path: Path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))


def collect_model_ids(queries, v2, export):
    """Every model the dashboard touches, with the YAML mode to pull it in."""
    ids = {}
    if v2:
        if v2.get("modelId"):
            ids[v2["modelId"]] = "combined"      # shared model: the governed layer
        if v2.get("workbookModelId"):
            ids[v2["workbookModelId"]] = "extension"
    for q in queries:
        mid = (q.get("query") or {}).get("modelId")
        if mid:
            ids.setdefault(mid, "extension")
    if export:
        wb = export.get("workbookModel") or {}
        if wb.get("base_model_id"):
            ids[wb["base_model_id"]] = "combined"
        if wb.get("id"):
            ids.setdefault(wb["id"], "extension")
        for mid in (export.get("queryModels") or {}):
            ids.setdefault(mid, "extension")
    return ids


def dump_dashboard(o: Omni, doc: dict, want_results: bool, want_png: bool):
    ident = doc["identifier"]
    out = EXPORT_DIR / safe(doc.get("name") or ident)
    out.mkdir(parents=True, exist_ok=True)
    notes = []
    write_json(out / "document.json", doc)

    v2 = None
    try:
        v2 = o.get(f"/v2/documents/{ident}")
        write_json(out / "dashboard.v2.json", v2)
    except ApiError as e:
        if e.code == 422:
            notes.append("v2 GET 422: classic-layout dashboard; layout/vis come from export.json "
                         "(do NOT upgrade the layout — that publishes)")
        else:
            notes.append(f"v2 GET failed: HTTP {e.code}")

    queries = o.get(f"/v1/documents/{ident}/queries").get("queries", [])
    write_json(out / "queries.json", queries)
    print(f"      {len(queries)} saved query(ies)")

    export = None
    try:
        export = json.loads(o._request("GET", f"/unstable/documents/{ident}/export"))
        write_json(out / "export.json", export)
        if export.get("fileUploads"):
            notes.append("export has fileUploads: spreadsheet/upload tiles — ask the customer for the source")
    except ApiError as e:
        notes.append(f"export failed: HTTP {e.code}"
                     + (" (needs an Organization API key, not a PAT)" if e.code in (401, 403) else ""))

    # model YAML for every layer the dashboard touches
    models = collect_model_ids(queries, v2, export)
    for mid, mode in models.items():
        try:
            yml = o.get(f"/v1/models/{mid}/yaml", mode=mode, includeSchemas="false")
        except ApiError as e:
            notes.append(f"model {mid} YAML failed: HTTP {e.code}")
            continue
        mdir = out / "models" / mid
        write_json(mdir / "_meta.json", {"mode": mode, "version": yml.get("version"),
                                         "viewNames": yml.get("viewNames")})
        for fname, text in (yml.get("files") or {}).items():
            p = mdir / (re.sub(r"[^A-Za-z0-9._-]", "_", fname)[:120] + ".yaml")
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(text if isinstance(text, str) else json.dumps(text, indent=2))
    print(f"      {len(models)} model layer(s)")

    try:
        write_json(out / "connections.json", o.get("/v1/connections"))
    except ApiError as e:
        notes.append(f"connections list failed: HTTP {e.code}")

    # Omni's own generated SQL per tile (planOnly), and optionally the result rows
    sql_ok = 0
    for q in queries:
        key = q.get("queryIdentifierMapKey") or q.get("id")
        stem = f"{safe(str(key), 12)}__{safe(q.get('name') or 'tile', 60)}"
        query = q.get("query") or {}
        try:
            lines = o.run_query({"query": query, "planOnly": True, "cache": "SkipCache"})
            sql = generated_sql(lines)
            if sql:
                (out / "sql").mkdir(exist_ok=True)
                (out / "sql" / f"{stem}.sql").write_text(sql)
                sql_ok += 1
            else:
                write_json(out / "sql" / f"{stem}.plan.json", lines)
                notes.append(f"tile {key}: no SQL in plan response (saved raw plan)")
        except ApiError as e:
            notes.append(f"tile {key}: plan failed HTTP {e.code}")

        if want_results:
            try:
                text = o.post("/v1/query/run", {"query": query, "resultType": "json",
                                                "cache": "SkipCache"})
                rows = parse_ndjson(text)
                rows = rows[0] if len(rows) == 1 else rows
            except ApiError as e:
                if e.code != 408:
                    notes.append(f"tile {key}: results failed HTTP {e.code}")
                    continue
                # long-running: fall back to the job flow (Arrow payload)
                rows = None
                for jl in job_lines(o.run_query({"query": query, "cache": "SkipCache"})):
                    if jl.get("result"):
                        rows = decode_arrow(jl["result"])
                        if rows is None:
                            (out / "results").mkdir(exist_ok=True)
                            (out / "results" / f"{stem}.arrow.b64").write_text(jl["result"])
                            notes.append(f"tile {key}: Arrow result saved raw (pip install pyarrow to decode)")
                    elif jl.get("status") != "COMPLETE":
                        notes.append(f"tile {key}: job {jl.get('status')} {jl.get('error_message', '')}")
            if rows is not None:
                write_json(out / "results" / f"{stem}.json", rows)
    print(f"      generated SQL for {sql_ok}/{len(queries)} tile(s)")

    if want_png:
        png = download_png(o, ident, notes)
        if png:
            (out / "dashboard.png").write_bytes(png)
            print("      dashboard.png saved")

    write_json(out / "_fetch_notes.json", notes)
    for n in notes:
        print(f"      note: {n}")
    print(f"  OK  {doc.get('name')}  -> {out.relative_to(REPO_ROOT)}/")


def download_png(o: Omni, ident: str, notes: list):
    try:
        resp = json.loads(o.post(f"/v1/dashboards/{ident}/download", {"format": "png"}))
        job = resp.get("job_id")
    except ApiError as e:
        if e.code == 409:
            try:
                job = json.loads(e.body).get("existing_job_id")
            except json.JSONDecodeError:
                job = None
        else:
            notes.append(f"png download failed before a job was created: HTTP {e.code} "
                         "— use scripts/omni_shots.py instead")
            return None
    if not job:
        notes.append("png download returned no job id — use scripts/omni_shots.py instead")
        return None
    for _ in range(60):
        st = o.get(f"/v1/dashboards/{ident}/download/{job}/status")
        if st.get("status") == "complete":
            return o._request("GET", f"/v1/dashboards/{ident}/download/{job}", raw=True)
        if st.get("status") == "error":
            notes.append(f"png job errored: {st.get('error')}")
            return None
        time.sleep(3)
    notes.append("png job timed out")
    return None


def main():
    ap = argparse.ArgumentParser(description="Fetch Omni dashboards (tiles, model YAML, generated SQL) for migration")
    ap.add_argument("--list", action="store_true", help="List dashboards (most-viewed first) and exit")
    ap.add_argument("--dashboard", nargs="+", metavar="ID", help="Download dashboard(s) by identifier")
    ap.add_argument("--name", help="Download the dashboard with this exact name")
    ap.add_argument("--folder", help="Filter/download by folder path (prefix match)")
    ap.add_argument("--results", action="store_true", help="Also save Omni's result rows per tile (parity baseline)")
    ap.add_argument("--png", action="store_true", help="Also download Omni's rendered dashboard PNG")
    args = ap.parse_args()

    env = load_env(ENV_FILE)
    EXPORT_DIR.mkdir(exist_ok=True)
    o = Omni(env)

    docs = [d for d in o.documents() if d.get("hasDashboard") and not d.get("deleted")]
    if args.folder:
        docs = [d for d in docs if ((d.get("folder") or {}).get("path") or "").startswith(args.folder)]
    print(f"Signed in to {o.api}; {len(docs)} dashboard(s) visible\n")

    if args.list or not (args.dashboard or args.name or args.folder):
        rows = []
        for d in docs:
            views = (d.get("_count") or {}).get("views", "")
            path = (d.get("folder") or {}).get("path") or "(no folder)"
            print(f"  {str(views):>6} views  [{path}]  {d.get('name')}   "
                  f"(id={d.get('identifier')}, owner={(d.get('owner') or {}).get('name')}, "
                  f"updated={d.get('updatedAt')})")
            rows.append({"identifier": d.get("identifier"), "name": d.get("name"), "folder": path,
                         "owner": (d.get("owner") or {}).get("name"), "views": views,
                         "favorites": (d.get("_count") or {}).get("favorites"),
                         "updatedAt": d.get("updatedAt"), "url": d.get("url")})
        write_json(EXPORT_DIR / "inventory.json", rows)
        print(f"\nInventory written to {(EXPORT_DIR / 'inventory.json').relative_to(REPO_ROOT)} (use it for triage).")
        if not args.list:
            print('Re-run with --dashboard <id>, --name "<name>" or --folder "<path>" to download.')
        return

    targets = docs
    if args.dashboard:
        by_id = {d["identifier"]: d for d in docs}
        targets = [by_id.get(i, {"identifier": i, "name": i}) for i in args.dashboard]
    elif args.name:
        targets = [d for d in docs if d.get("name") == args.name]
    if not targets:
        sys.exit("No dashboards matched. Run with --list to see options.")

    print(f"Downloading {len(targets)} dashboard(s) to {EXPORT_DIR}/\n")
    for d in targets:
        try:
            dump_dashboard(o, d, args.results, args.png)
        except ApiError as e:
            print(f"  FAIL {d.get('name')}: {e}")


if __name__ == "__main__":
    main()
