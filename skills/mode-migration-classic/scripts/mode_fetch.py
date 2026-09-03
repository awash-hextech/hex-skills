#!/usr/bin/env python3
"""Fetch Mode report(s) and their source (queries + SQL + charts + notebook).

Step 1 of the Mode -> Hex migration flow. Authenticates to the Mode API with an
API token + secret (HTTP Basic), then either lists reports or downloads specific
ones. For each report it saves everything the migration agent parses as the source
of truth:

    mode_exports/<report>/
        report.json                  # full report object (raw API response)
        queries/<query>.sql          # each query's raw SQL (Liquid included)
        queries/<query>.json         # each query object (data_source_id, etc.)
        charts/<query>__<chart>.json # each chart definition
        notebook.json                # Python/R notebook cells (if the report has one)

The SQL is the source of truth: a Mode query is warehouse SQL that already ran, so
the .sql files are what you port (swapping Liquid for Hex params). See
reference/mode-semantics.md.

Usage:
  # list every space + report you can see (name + space + token)
  venv/bin/python scripts/mode_fetch.py --list

  # download one report by exact name (optionally disambiguate with --space)
  venv/bin/python scripts/mode_fetch.py --name "Marketing Funnel"
  venv/bin/python scripts/mode_fetch.py --name "Marketing Funnel" --space "Growth"

  # download every report in a space
  venv/bin/python scripts/mode_fetch.py --space "Growth"

Credentials are read from credentials/mode.env (gitignored).

NOTE ON THE MODE API: Mode returns HAL+JSON (`_embedded`, `_links`). The resource
paths below are the documented shapes, but Mode's API evolves and some fields (esp.
the notebook endpoint) vary by plan/report generation. This script saves the RAW
JSON for every resource so nothing is lost even if a field name differs. If a call
404s or a field is missing, verify the current shape against
https://mode.com/developer/api-reference/  (you have WebFetch/WebSearch).
"""
import argparse
import base64
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = REPO_ROOT / "credentials" / "mode.env"
EXPORT_DIR = REPO_ROOT / "mode_exports"


def load_env(path: Path) -> dict:
    if not path.exists():
        sys.exit(
            f"Missing {path}.\n"
            f"Copy credentials/mode.env.example to credentials/mode.env "
            f"and fill in your Mode workspace + API token + secret."
        )
    env = {}
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        env[key.strip()] = val.strip()
    required = ["MODE_WORKSPACE", "MODE_TOKEN", "MODE_SECRET"]
    missing = [k for k in required if not env.get(k)]
    if missing:
        sys.exit(f"mode.env is missing values for: {', '.join(missing)}")
    env.setdefault("MODE_HOST", "https://app.mode.com")
    return env


class Mode:
    def __init__(self, env: dict):
        self.host = env["MODE_HOST"].rstrip("/")
        self.workspace = env["MODE_WORKSPACE"]
        raw = f"{env['MODE_TOKEN']}:{env['MODE_SECRET']}".encode()
        self.auth = "Basic " + base64.b64encode(raw).decode()

    def get(self, path: str) -> dict:
        """GET an absolute-or-relative API path and return parsed JSON."""
        url = path if path.startswith("http") else f"{self.host}{path}"
        req = urllib.request.Request(url, headers={
            "Authorization": self.auth,
            "Accept": "application/hal+json",
            "Content-Type": "application/json",
            "User-Agent": "mode-to-hex-migration/1.0",
        })
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode())
        except urllib.error.HTTPError as e:
            body = e.read().decode(errors="replace")[:400]
            raise RuntimeError(f"HTTP {e.code} for {url}\n{body}") from None

    def embedded(self, obj: dict, key: str) -> list:
        return (obj.get("_embedded") or {}).get(key, []) or []

    def paged(self, path: str, key: str) -> list:
        """Follow HAL `_links.next` pagination, collecting `_embedded[key]`."""
        out, nxt = [], path
        while nxt:
            page = self.get(nxt)
            out.extend(self.embedded(page, key))
            nxt = ((page.get("_links") or {}).get("next") or {}).get("href")
        return out

    # --- resource helpers (verify shapes against the API reference if they drift) ---
    def spaces(self) -> list:
        return self.paged(f"/api/{self.workspace}/spaces?filter=all", "spaces")

    def reports(self, space_token: str) -> list:
        return self.paged(
            f"/api/{self.workspace}/spaces/{space_token}/reports", "reports")

    def report(self, report_token: str) -> dict:
        return self.get(f"/api/{self.workspace}/reports/{report_token}")

    def queries(self, report_token: str) -> list:
        return self.paged(
            f"/api/{self.workspace}/reports/{report_token}/queries", "queries")

    def charts(self, report_token: str, query_token: str) -> list:
        return self.paged(
            f"/api/{self.workspace}/reports/{report_token}/queries/{query_token}/charts",
            "charts")

    def notebook(self, report_token: str):
        """Best-effort: the notebook endpoint varies; return None if absent."""
        for path in (
            f"/api/{self.workspace}/reports/{report_token}/notebook",
            f"/api/{self.workspace}/reports/{report_token}/python_notebook",
        ):
            try:
                return self.get(path)
            except RuntimeError:
                continue
        return None


def safe(name: str, n: int = 80) -> str:
    return "".join(c if c.isalnum() or c in "-_ " else "_" for c in (name or "")).strip()[:n] or "untitled"


def dump_report(m: Mode, rpt: str, rname: str, space: str):
    out = EXPORT_DIR / safe(rname)
    (out / "queries").mkdir(parents=True, exist_ok=True)
    (out / "charts").mkdir(parents=True, exist_ok=True)

    rep = m.report(rpt)
    (out / "report.json").write_text(json.dumps(rep, indent=2))

    qs = m.queries(rpt)
    print(f"      {len(qs)} query(ies)")
    for q in qs:
        qname = safe(q.get("name") or q.get("token") or "query")
        qtok = q.get("token")
        (out / "queries" / f"{qname}.json").write_text(json.dumps(q, indent=2))
        sql = q.get("raw_query")
        if sql is not None:
            (out / "queries" / f"{qname}.sql").write_text(sql)
        if qtok:
            try:
                for c in m.charts(rpt, qtok):
                    cname = safe(c.get("token") or "chart", 24)
                    (out / "charts" / f"{qname}__{cname}.json").write_text(
                        json.dumps(c, indent=2))
            except RuntimeError as e:
                print(f"      (charts for {qname}: {e})")

    nb = m.notebook(rpt)
    if nb is not None:
        (out / "notebook.json").write_text(json.dumps(nb, indent=2))
        print("      notebook: saved")

    print(f"  OK  [{space}] {rname}")
    print(f"      -> {out.relative_to(REPO_ROOT)}/")


def main():
    ap = argparse.ArgumentParser(description="Fetch Mode reports (SQL + charts + notebook) for migration")
    ap.add_argument("--list", action="store_true", help="List all visible spaces + reports and exit")
    ap.add_argument("--name", help="Download the report with this exact name")
    ap.add_argument("--space", help="Filter/download by space name")
    args = ap.parse_args()

    env = load_env(ENV_FILE)
    EXPORT_DIR.mkdir(exist_ok=True)
    m = Mode(env)

    spaces = m.spaces()
    print(f"Signed in to {env['MODE_HOST']} (workspace: {env['MODE_WORKSPACE']}), "
          f"{len(spaces)} space(s) visible\n")

    # Build (space, report) inventory
    inventory = []
    for sp in spaces:
        sname = sp.get("name") or sp.get("token")
        if args.space and sname != args.space:
            continue
        for r in m.reports(sp.get("token")):
            inventory.append((sname, r.get("name"), r.get("token")))

    if args.list or (not args.name and not args.space):
        print(f"{len(inventory)} report(s) visible:\n")
        for sname, rname, rtok in sorted(inventory, key=lambda x: (x[0] or "", x[1] or "")):
            print(f"  [{sname}]  {rname}   (token={rtok})")
        if not args.list:
            print("\nRe-run with --name \"<report>\" or --space \"<space>\" to download.")
        return

    targets = inventory
    if args.name:
        targets = [t for t in targets if t[1] == args.name]
    if not targets:
        sys.exit("No reports matched your filters. Run with --list to see options.")

    print(f"Downloading {len(targets)} report(s) to {EXPORT_DIR}/\n")
    for sname, rname, rtok in targets:
        try:
            dump_report(m, rtok, rname, sname)
        except RuntimeError as e:
            print(f"  FAIL [{sname}] {rname}: {e}")


if __name__ == "__main__":
    main()
