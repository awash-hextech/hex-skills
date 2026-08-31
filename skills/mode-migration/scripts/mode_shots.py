#!/usr/bin/env python3
"""Headless screenshot of a Mode report for the visual-QA loop (source of truth).

Uses a persistent Playwright profile so the customer logs into Mode ONCE (headed),
and every later capture is fully headless. The agent never types credentials — the
customer authenticates their own browser during --login. This mirrors hex_shots.py;
the two scripts keep separate profiles (Hex vs. Mode).

Setup once:
    pip install playwright && playwright install chromium
    python scripts/mode_shots.py --login          # headed; sign into Mode, then press Enter

Capture (headless, reuses the saved session):
    python scripts/mode_shots.py "<mode_report_url>" -o working/shots/source.png

Notes:
- Pass the report's normal URL (e.g. https://app.mode.com/<workspace>/reports/<token>).
- Mode charts render client-side; the script waits for network idle + a settle delay.
- The report body is an inner scroll container; the script captures the report element
  when it can find one, else falls back to full_page. If a capture looks clipped,
  confirm/extend REPORT_SELECTORS against the live DOM.
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROFILE = ROOT / "working" / "mode-screenshot-profile"

# Candidate selectors for the rendered Mode report body, most specific first.
# Mode markup changes over time — if captures clip, confirm/extend these.
REPORT_SELECTORS = [
    "[data-testid='report-viewer']",
    "[class*='reportView']",
    "[class*='ReportView']",
    ".report-container",
    "main",
]


def login():
    PROFILE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=False, viewport={"width": 1600, "height": 1000}
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://app.mode.com/signin")
        print("A browser window opened. Sign into Mode, then return here.")
        input("Press Enter once you're fully logged in… ")
        ctx.close()
    print(f"Session saved to {PROFILE}. Later captures are headless.")


def capture(url, out):
    if not PROFILE.exists():
        sys.exit("No saved profile. Run:  python scripts/mode_shots.py --login")
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=True, viewport={"width": 1600, "height": 1000}
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(4000)  # let charts finish rendering
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass

        el = None
        for sel in REPORT_SELECTORS:
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
    ap = argparse.ArgumentParser(description="Headless Mode-report screenshot for visual QA.")
    ap.add_argument("url", nargs="?", help="Mode report URL to capture")
    ap.add_argument("--login", action="store_true", help="Headed one-time sign-in")
    ap.add_argument("-o", "--out", default="working/shots/source.png", help="Output PNG path")
    args = ap.parse_args()

    if args.login:
        login()
        return
    if not args.url:
        ap.error("provide a URL to capture, or use --login for first-time setup")
    capture(args.url, args.out)


if __name__ == "__main__":
    main()
