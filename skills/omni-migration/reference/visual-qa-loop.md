# Visual-QA loop (headless screenshot → diff → fix)

The **render gate, on both build paths**. It renders the Hex app headlessly with a
**persistent browser profile the customer logs into once**, diffs it panel-by-panel
against the original Omni dashboard, and feeds the notebook agent surgical fixes until
parity.

- **Classic path:** run the **cell-spec diff first** ([`build-classic-app.md`](build-classic-app.md))
  — wrong chart type, encodings, colors, formats, and a broken `seriesId` linkage are
  catchable in the YAML without rendering. Spend these rounds on what only a render
  reveals: blank or partial series, collapsed chart heights, clipped or mis-ordered rows,
  overflowing labels, live filter behavior. ⚠️ **COMPLETED ≠ renders correctly.**
- **Generative path:** there are no diff-able chart cells, so this loop is the **whole**
  look-&-feel gate.

> **Not a credential-entry step.** The agent never types a password. The *customer* logs
> in **once**, in a headed browser, into a local profile that persists. Every later round
> reuses that session headlessly.

## Two sources for the Omni reference image

1. **Omni's own dashboard download (preferred).** Omni renders dashboards to PNG/PDF via
   its download API — no browser profile needed, and it's what Omni itself considers the
   dashboard's rendered form. `python scripts/omni_fetch.py --dashboard <id> --png`
   (async job; the script polls). Some dashboards fail to export before a job is created
   — if no job id comes back, don't claim a download; fall back to (2).
2. **Headless browser capture.** `python scripts/omni_shots.py --login` once (headed;
   customer signs into Omni), then `python scripts/omni_shots.py "<dashboard url>" -o
   working/shots/source.png`. Use this when the API download fails, when you need a
   specific filter state, or to test interactive behavior.

## One-time setup (Phase 0)

```bash
pip install playwright && playwright install chromium   # once
python scripts/hex_shots.py  --login                     # headed: customer signs into Hex
python scripts/omni_shots.py --login                     # headed: only if you need browser captures of Omni
```

Then one command per capture:

```bash
python scripts/omni_fetch.py --dashboard <id> --png                              # → omni_exports/<dash>/dashboard.png
python scripts/hex_shots.py "<hex_app_url>" -o working/shots/migrated.png
```

- **Hex unpublished drafts** show a URL lock screen. `hex_shots.py` opens the editor and
  clicks **App builder** to reveal the rendered app without publishing.
- **Full-app capture:** the Hex app is an inner scroll container; the script scrolls and
  stitches. If a capture looks clipped, check that first.
- **Same filter state on both sides.** Capture the Omni dashboard at its **default**
  filters and the Hex app at its default inputs — a mismatched default is a real bug
  (record it), not a capture artifact.

## The loop

Repeat until the diff is clean — typically **3+ rounds**. **Re-screenshot and re-diff
every round**; never assume a fix landed.

```
1. capture the Hex app (headless) + the Omni dashboard PNG
2. diff tile-by-tile:
     • layout / position / relative size (Omni grid → Hex rows + spans)
     • the numbers (against the gated SQL cells AND Omni's baseline results)
     • filter wiring (does changing an input move the right tiles?)
     • colors (vs. the styling-spec hex codes), titles, label fields, number/date formats
3. zero discrepancies? → EXIT (hand to human for final confirm)
4. send ONE coherent fix batch:  hex thread continue <thread_id> "<numbered fix list>"
     (classic path: layout-only fixes are often faster as export → edit appLayout → import)
5. wait for IDLE, then go to 1
```

### Diffing well
- **Compare per tile against a fixed checklist** — a whole-image pixel diff is noisy
  (fonts/antialiasing differ) and misses semantic errors.
- **Numbers are verified against data, not pictures.** The screenshot confirms the right
  value is in the right place; the SQL gate's **result-parity check** against Omni's
  query results confirms the value is correct ([`sql-review.md`](sql-review.md)).
- **Keep each `continue` batch surgical and numbered** ("1. Revenue KPI is currency, 0
  decimals; 2. move the trend chart above the table; 3. segment colors are
  #1f77b4/#ff7f0e"). Vague prompts make the agent thrash.

## Exit

Zero discrepancies → **final human confirm**: hand the customer the Hex app link + the
Omni dashboard side-by-side. The loop gets to near-parity; the human signs off.

## Cheat-sheet

- Setup once: `pip install playwright && playwright install chromium`, `python scripts/hex_shots.py --login` (+ `omni_shots.py --login` if needed).
- Source: `python scripts/omni_fetch.py --dashboard <id> --png`, or `python scripts/omni_shots.py "<url>" -o working/shots/source.png`.
- Migrated: `python scripts/hex_shots.py "<url>" -o working/shots/migrated.png`.
- Fix: `hex thread continue <thread_id> "<numbered fix list>"` → re-capture → re-diff.
- Profiles live in `working/hex-screenshot-profile/` and `working/omni-screenshot-profile/` (gitignored).
