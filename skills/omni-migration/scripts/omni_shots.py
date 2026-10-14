#!/usr/bin/env python3
"""Headless screenshot of an Omni dashboard for the visual-QA loop (source of truth).

Prefer Omni's own PNG download (scripts/omni_fetch.py --png) when it works; use this
script when the API download fails, or when you need a specific filter state.

Uses a persistent Playwright profile so the customer logs into Omni ONCE (headed),
and every later capture is fully headless. The agent never types credentials — the
customer authenticates their own browser during --login. This mirrors hex_shots.py;
the two scripts keep separate profiles (Hex vs. Omni).

Setup once:
    pip install playwright && playwright install chromium
    python scripts/omni_shots.py --login          # headed; sign into Omni, then press Enter

Capture (headless, reuses the saved session):
    python scripts/omni_shots.py "<omni_dashboard_url>" -o working/shots/source.png

Notes:
- Pass the dashboard's normal URL (e.g. https://<instance>.omniapp.co/dashboards/<id>).
- --login opens the Omni instance from OMNI_BASE_URL in credentials/omni.env (or pass
  --base-url). Omni tiles render client-side; the script waits for network idle + a
  settle delay.
- The dashboard body may be an inner scroll container; the script captures the
  dashboard element when it can find one, else falls back to full_page. If a capture
  looks clipped, confirm/extend DASHBOARD_SELECTORS against the live DOM.
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROFILE = ROOT / "working" / "omni-screenshot-profile"
ENV_FILE = ROOT / "credentials" / "omni.env"

# Candidate selectors for the rendered Omni dashboard body, most specific first.
# These are guesses until confirmed against a live instance — if captures clip,
# inspect the DOM and extend this list.
DASHBOARD_SELECTORS = [
    "[data-testid='dashboard']",
    "[class*='DashboardGrid']",
    "[class*='dashboard-grid']",
    ".react-grid-layout",
    "main",
]


def base_url_from_env() -> str:
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            key, _, val = line.strip().partition("=")
            if key.strip() == "OMNI_BASE_URL" and val.strip():
                return val.strip().rstrip("/")
    return ""


def login(base_url):
    PROFILE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=False, viewport={"width": 1600, "height": 1000}
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(base_url)
        print("A browser window opened. Sign into Omni, then return here.")
        input("Press Enter once you're fully logged in… ")
        ctx.close()
    print(f"Session saved to {PROFILE}. Later captures are headless.")


def capture(url, out):
    if not PROFILE.exists():
        sys.exit("No saved profile. Run:  python scripts/omni_shots.py --login")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=True, viewport={"width": 1600, "height": 1000}
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(5000)  # let tiles finish rendering
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass

        el = None
        for sel in DASHBOARD_SELECTORS:
            el = page.query_selector(sel)
            if el:
                break
        if el:
            el.screenshot(path=str(out))
        else:
            page.screenshot(path=str(out), full_page=True)
        ctx.close()
    print(f"Wrote {out}")


def main():
    ap = argparse.ArgumentParser(description="Headless Omni-dashboard screenshot for visual QA.")
    ap.add_argument("url", nargs="?", help="Omni dashboard URL to capture")
    ap.add_argument("--login", action="store_true", help="Headed one-time sign-in")
    ap.add_argument("-o", "--out", default="working/shots/source.png", help="Output PNG path")
    ap.add_argument("--base-url", help="Omni instance URL for --login (default: OMNI_BASE_URL in credentials/omni.env)")
    args = ap.parse_args()

    if args.login:
        base = (args.base_url or base_url_from_env()).rstrip("/")
        if not base:
            ap.error("set OMNI_BASE_URL in credentials/omni.env or pass --base-url https://<instance>.omniapp.co")
        login(base)
        return
    if not args.url:
        ap.error("provide a URL to capture, or use --login for first-time setup")
    capture(args.url, args.out)


if __name__ == "__main__":
    main()
