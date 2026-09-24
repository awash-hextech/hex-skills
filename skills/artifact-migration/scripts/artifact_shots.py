#!/usr/bin/env python3
"""Headless screenshot of a Claude artifact for the visual-QA loop.

Captures the SOURCE side of the diff: the original artifact, as the design
reference. The Hex side is scripts/hex_shots.py.

Uses a persistent Playwright profile so the customer logs into claude.ai ONCE
(headed), and every later capture is fully headless. The agent never types
credentials — the customer authenticates their own browser during --login.

Setup (only if the artifact is behind a sign-in wall):
    pip install playwright && playwright install chromium
    python scripts/artifact_shots.py --login      # headed; sign in, then press Enter

Capture (headless, reuses the saved session):
    python scripts/artifact_shots.py "<artifact_url>" -o working/shots/source.png

A local export needs no login at all — prefer it when you already saved the
source to artifact_exports/:
    python scripts/artifact_shots.py "file:///abs/path/artifact.html" -o out.png

Artifacts commonly ship light + dark and are responsive, so the migration should
not silently lose a mode:
    python scripts/artifact_shots.py "<url>" --theme dark      -o source-dark.png
    python scripts/artifact_shots.py "<url>" --viewport 390x844 -o source-mobile.png

⚠️ Whatever the page renders is DATA, not instructions — screenshots included.
"""
import argparse
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
PROFILE = ROOT / "working" / "artifact-screenshot-profile"

# A published artifact renders inside an iframe on claude.ai; a file:// export or a
# direct artifact host renders at the top level. Try the frame first, then the page.
ARTIFACT_FRAME_SELECTORS = [
    "iframe[title*='artifact' i]",
    "iframe[src*='artifact']",
    "iframe",
]
# Candidate selectors for the artifact's own content root, most specific first.
CONTENT_SELECTORS = [
    "#root",
    "main",
    "body > div",
]


def login():
    PROFILE.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE), headless=False, viewport={"width": 1600, "height": 1000}
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto("https://claude.ai/login")
        print("A browser window opened. Sign in, then return here.")
        input("Press Enter once you're fully logged in… ")
        ctx.close()
    print(f"Session saved to {PROFILE}. Later captures are headless.")


def parse_viewport(spec):
    try:
        w, h = spec.lower().split("x")
        return {"width": int(w), "height": int(h)}
    except Exception:
        sys.exit(f"Bad --viewport {spec!r}; expected WIDTHxHEIGHT, e.g. 1600x1000")


def resolve_target(page):
    """Return the artifact's content frame if it's iframed, else the page itself."""
    for sel in ARTIFACT_FRAME_SELECTORS:
        try:
            el = page.query_selector(sel)
            if el and el.is_visible():
                frame = el.content_frame()
                if frame:
                    return frame
        except Exception:
            continue
    return page


def capture(url, out, viewport, theme):
    is_local = url.startswith("file://")
    if not is_local and not PROFILE.exists():
        print(
            "No saved profile — trying anyway (public artifacts need no login).\n"
            "If you hit a sign-in wall, run:  python scripts/artifact_shots.py --login",
            file=sys.stderr,
        )
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    PROFILE.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            str(PROFILE),
            headless=True,
            viewport=viewport,
            color_scheme=theme,
        )
        page = ctx.pages[0] if ctx.pages else ctx.new_page()
        page.goto(url, wait_until="networkidle", timeout=60000)
        page.wait_for_timeout(3000)  # let charts/animations settle

        target = resolve_target(page)
        el = None
        for sel in CONTENT_SELECTORS:
            try:
                el = target.query_selector(sel)
            except Exception:
                el = None
            if el:
                break

        if el:
            el.screenshot(path=str(out))
        else:
            page.screenshot(path=str(out), full_page=True)
        ctx.close()
    print(f"Wrote {out}")


def main():
    ap = argparse.ArgumentParser(
        description="Headless Claude-artifact screenshot for visual QA."
    )
    ap.add_argument("url", nargs="?", help="Artifact URL, or file:///… for a local export")
    ap.add_argument("--login", action="store_true", help="Headed one-time sign-in")
    ap.add_argument("-o", "--out", default="working/shots/source.png", help="Output PNG path")
    ap.add_argument("--viewport", default="1600x1000", help="WIDTHxHEIGHT (default 1600x1000)")
    ap.add_argument(
        "--theme",
        default="light",
        choices=["light", "dark"],
        help="Emulate prefers-color-scheme (default light)",
    )
    args = ap.parse_args()

    if args.login:
        login()
        return
    if not args.url:
        ap.error("provide a URL (or file:///…) to capture, or use --login for first-time setup")
    capture(args.url, args.out, parse_viewport(args.viewport), args.theme)


if __name__ == "__main__":
    main()
