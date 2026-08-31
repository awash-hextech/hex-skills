---
name: mode-migration
description: >-
  Migrate Mode (Mode Analytics / ThoughtSpot Mode) reports into Hex by delegating
  the build to Hex's in-product notebook agent. Use when someone wants to convert,
  port, rebuild, or migrate Mode content (reports, queries, charts, Report Builder /
  HTML-Liquid layouts, Python/R notebooks) into Hex. This coding agent pulls the
  report via the Mode API, reads its SQL + Liquid + chart defs as the source of
  truth, translates the Mode-specific bits (Liquid params, definitions, dataset
  refs), and writes a migration brief. Then Hex's notebook agent (which can
  see the live warehouse schema + workspace context) builds a generative app on
  top of gated SQL cells, and this agent verifies with a SQL-fidelity gate + a
  visual-QA loop. Triggers: "migrate Mode to Hex", "port my Mode reports with the
  Hex agent", "convert a Mode report", "Mode → Hex".
---

# Mode → Hex Migration (generative-app build)

A CLI-driven migration where this coding agent understands the Mode source and
verifies the result, and Hex's in-product notebook agent builds the dashboard as a
generative app. You fetch a report via the Mode API, read its **queries (SQL),
Liquid templating, chart defs, and any Python/R notebook** as the source of truth,
translate the Mode-specific semantics, and write a migration brief into the Hex
project; the notebook agent reads that brief and builds a generative app on a
natively-gated SQL data layer; then you run a SQL-fidelity gate on the SQL and a
visual-QA loop on the render.


> **The deliverable is a generative app.** A generative app reproduces Mode's Report Builder 
> layout and any bespoke HTML/Liquid report page in a way native EXPLORE/METRIC chart cells can't.
> The numbers stay in inspectable, gated SQL cells underneath. Hand-building native cells is a
> fallback for when the notebook agent isn't available (see the build-path gate).

## Why delegate the build to the notebook agent

This coding agent (reading this skill) is blind to the things that make the build
correct, meaning that it can't see the live warehouse schema or data, workspace context, nor rendered result. The notebook agent has visibility into all three since it runs inside the workspace. So for building in Hex it is the better-equipped agent and delegating the generative-app build to it is the default path. Please note that this spends Hex credits.

> **Division of labor:** this coding agent owns understanding the Mode report, including
> (the durable IP: reading each query's SQL + Liquid, resolving definitions/dataset
> refs, translating params, mapping Python/R notebook logic and the HTML layout) and
> **verifying the result** (the fidelity gate). The notebook agent owns **building it
> in Hex**. Accuracy is guaranteed by the gate — which reviews whoever wrote the SQL —
> not by this agent hand-writing every query.

**Priority order (say this to the customer up front):** (1) **accuracy** of SQL +
visuals first, (2) **similar look & feel** second. The generative-app default is what
lets you deliver #2 — it reproduces Mode's layout/styling (including a hand-built
HTML report page) far closer than native cells, and the visual-QA loop verifies the
render — while SQL stays gated underneath for #1. Some Mode features still have no
clean 1:1 in Hex (bespoke D3/JS in an HTML report, R-only notebook logic, map
libraries) — name those early so "it isn't pixel-identical" is never a surprise.
Philosophy: **cover the basis, don't gold-plate.**

## Reference docs (read on demand)
- [`reference/connection-mapping.md`](reference/connection-mapping.md) — resolve the Mode data source → Hex data connection, and decide whether the warehouse (and thus the SQL dialect) changes.
- [`reference/mode-semantics.md`](reference/mode-semantics.md) — **understand the report:** Mode construct → Hex meaning. SQL ports near-verbatim; the real work is **Liquid** (`{{ @param }}`, `{% form %}`, `{% if %}`, definitions), **query/dataset dependencies**, **Python/R notebook** cells, chart defs, and the dialect step *only if the warehouse changes*. This is what you distill into the brief.
- [`reference/build-generative-app.md`](reference/build-generative-app.md) — **the build (default):** gate the SQL natively, then have the agent build a **Generative app** on top (Report Builder layout / bespoke HTML page, pixel styling); the styling spec + the `genAppFiles` verification.
- [`reference/build-notebook-agent.md`](reference/build-notebook-agent.md) — **brief + handoff mechanics:** how to write the migration brief (intent, not literal SQL), inject it (⚠️ `{% raw %}`-wrapped — doubly important, Mode SQL is *full* of `{{ }}`/`{% %}`), hand it to the notebook agent, surface the live URL, and iterate. Shared by the generative build.
- [`reference/visual-qa-loop.md`](reference/visual-qa-loop.md) — **render gate (default):** headless Playwright screenshot (persistent profile, one-time login) → panel-by-panel diff vs. the source Mode PNG → surgical fix batch → repeat.
- [`reference/sql-review.md`](reference/sql-review.md) — **SQL-fidelity gate:** ledger → independent re-derivation & diff → mistake-class checklist → read-back + differential probes. Runs on the native SQL cells under the app.
- [`reference/building-cells.md`](reference/building-cells.md) — **fallback build only:** this coding agent hand-builds native cells from templates (for when the notebook agent isn't available).
- [`reference/datasource-guide.md`](reference/datasource-guide.md) — author a Hex guide mirroring the Mode data source / definitions (semantic layer for Threads/agent), published via `hex guide`.
- [`reference/gotchas.md`](reference/gotchas.md) — parsing correctness rules, Hex CLI quirks, app layout.

## What you need before starting
- **Mode access** — a Mode **API token + secret** (for `scripts/mode_fetch.py`) *or* exported report contents. The token's workspace must be able to see the reports.
- **Hex CLI** installed and authed; the **target Hex data connection** the migrated cells will query; and the **headless-agent-threads feature enabled** for the workspace (the default build path uses `hex thread`).
- `credentials/mode.env` filled in from `credentials/mode.env.example` (workspace/account slug + API token + secret). Gitignored.
- **Visual-QA render gate:** `pip install playwright && playwright install chromium`, plus a **one-time headed login** into each screenshot profile — one for Hex, one for Mode (the customer signs in once each; every later capture is headless). See [`visual-qa-loop.md`](reference/visual-qa-loop.md).
- **(Fallback path only)** Hex-YAML editor validation — the RedHat YAML VS Code extension for hand-editing exported project YAML. See [`building-cells.md`](reference/building-cells.md).

## Workflow at a glance
0. **Prioritize & organize** the customer's reports → one folder.
1. **Pilot 1–2 reports** end-to-end, QA, tune.
2. **Port each report:** resolve connection (+ decide if the warehouse/dialect changes) → pull + read queries/Liquid/charts/notebook → build the **generative app** (gate the SQL layer natively, then build the app on top; fall back to hand-built native cells only if the notebook agent is unavailable) → **SQL-fidelity gate** + **visual-QA loop** → ship the guide.
3. **Batch the rest** with the folder loop + manifest.

---

# Step 0 — Prioritize & organize (do this FIRST, before any report)

Migration is the best moment a team ever gets to prune. Most Mode workspaces are
60–80% dead weight — abandoned drafts, one-offs, near-duplicates, personal
scratch reports. **Do not migrate what nobody uses.** Guide the customer through a
short triage before a single report is ported.

1. **Take inventory.** Mode's **Discovery / usage analytics** (the "Mode reporting on
   Mode" collection, or the admin *Reports* / *Activity* export) carries **view counts**
   + **last-run / last-viewed** per report; otherwise ask. The API (`scripts/mode_fetch.py
   --list`) enumerates every report in every space with its token, name, and space. Per
   report capture: name, owner, space, last-run, recent view count, and a one-line "what
   decision does this drive?"

2. **Prioritize on three axes**, then bucket:

   | Axis | Migrate-first | Drop / defer |
   |------|---------------|--------------|
   | **Usage** | run/viewed regularly, real audience | ~0 runs in 90 days |
   | **Business value** | drives a recurring decision | ad-hoc / one-time / "nice to have" |
   | **Freshness / ownership** | actively maintained, clear owner | stale, orphaned, personal-space scratch |

   **Get the customer to confirm the buckets** — it's a business call: **Migrate**,
   **Archive/rebuild-later** (snapshot, don't port as-is), **Drop** (dead — say so).
   Collapse **near-duplicates** (Mode "duplicate report" sprawl is common) into one
   canonical version.

3. **Organize into ONE folder** (the batch loop points at a single directory of report
   exports):
   - **Mode API:** `scripts/mode_fetch.py` (`--space` / `--name`) — downloads each report's
     JSON + every query's SQL + chart defs + notebook into `mode_exports/<report>/`.
   - **Manual:** customer exports report contents (queries + notebook) into one folder.

4. **Complexity triage — set expectations.** Flag known-gap features up front (detail in
   [`gotchas.md`](reference/gotchas.md)): **bespoke HTML report pages with custom D3/JS** →
   generative app can reproduce layout + Chart.js-style visuals but arbitrary JS is
   best-effort; **R notebook cells** → port logic to Python (or flag); **Python notebook
   cells that call external services / pip packages** → confirm availability in Hex;
   **non-warehouse query results** (uploaded CSVs, Google Sheets, Mode's own "helper"
   datasets) → rows aren't in the warehouse; **ask the customer for the source**;
   **`{% form %}`-driven dynamic SQL** → maps to Hex input params but sweep every branch.
   Put these in the brief as known gaps so the notebook agent doesn't silently approximate
   them.

# First pass — cap at 1–2 reports (pilot, then scale)

**Do not run the full folder first.** Migrate **one or two** reports end-to-end, then stop and tune.
- **Pick the pilot(s):** one *simple/representative*; if two, add one *representative-complex* (a report with a bespoke HTML layout or a Python notebook surfaces gaps early). Don't make the single hardest edge case your only pilot.
- **Go all the way:** pull → brief → gate the SQL → build the generative app → visual-QA loop → **customer's final visual confirm** vs. the Mode original.
- **Tune, then scale:** fold fixes (connection mapping, Liquid translations, brief wording, format mappings, screenshot-selector tweaks) back into this playbook *before* batching the rest.

Why: the visual-QA loop gets the render close automatically, but a human confirm on a tiny first batch catches systematic errors before they multiply.

# Guiding the customer
- **State the priority order up front** (accuracy first, look & feel second) and that the deliverable is a **generative app**.
- **Name the human gates:** (1) **data connection** — you'll ask when the target is ambiguous, and confirm whether the warehouse (and dialect) is the same or changes; (2) **screenshot logins** — the one-time headed sign-ins (Hex + Mode) that power the visual-QA loop; (3) **final visual confirm** — the loop drives the render to near-parity automatically, then the customer signs off on the pilot and each batch. (You only surface the *build path* as a question if the notebook agent is unavailable and you must fall back to hand-built native cells.)
- **Tell them what to provide:** Mode API token + secret *or* exported report contents; which **Hex data connection** to target (and whether it's the same warehouse Mode queried); and that the default build spends **Hex credits** (needs the headless-agent-threads feature).
- **Work in waves:** pilot → tune → batch a wave → QA → next wave.

---

# Porting a report (the core per-report loop)

1. **Resolve the data connection, then note its SQL dialect — and whether it changed.**
   A Mode report's queries each name a **data source**; match it to a Hex connection on
   metadata (type + database), not names/hosts. Full procedure →
   [`connection-mapping.md`](connection-mapping.md). ⚠️ **The dialect step is
   conditional, not automatic:** if the target Hex connection is the **same warehouse**
   Mode queried (the common case), the SQL ports **near-verbatim** — only Liquid and
   Mode-isms need changing. If the customer is **also switching warehouses** (e.g. Mode
   on Redshift → Hex on Snowflake), you additionally owe a real dialect translation
   pass (see [`mode-semantics.md`](reference/mode-semantics.md) "Dialect step"). Ask
   which case you're in. ⚠️ **Never assume Snowflake.**

2. **Create the Hex project and inject the raw report source.** Keep the source of truth
   in the project — the report JSON + each query's SQL:
   ```bash
   hex project create ...
   hex cell create -t markdown -s "$(cat mode_exports/<report>/report.json)"   # source reference
   hex cell create -t markdown -s "$(cat mode_exports/<report>/queries/<q>.sql)"
   ```
   Keep these reference cells in the notebook but **never add them to the app layout** —
   they're maintainer references. ⚠️ **Wrap any injected reference text (report JSON,
   the raw Liquid SQL, the brief, the styling spec) in `{% raw %}` … `{% endraw %}`.**
   This is **more critical for Mode than Tableau**: Mode SQL is *saturated* with `{{ @param }}`
   and `{% form %}` / `{% if %}` Liquid tags, and Hex markdown cells Jinja-render `{{ }}`
   — an unwrapped Mode query cell will ERROR the whole `hex project run` even though every
   real SQL cell is fine. See [`gotchas.md`](reference/gotchas.md).

3. **Read the report and understand it.** The Mode export is the **source of truth**;
   screenshots are QA only. Produce an intent-level plan, not finished SQL:
   - **Inventory the queries.** Each query = one SQL statement + its data source. This is
     already warehouse SQL — capture it verbatim as the baseline, then note the Liquid it
     carries. Strategy for clustering into Hex SQL cells → [`mode-semantics.md`](reference/mode-semantics.md) §"Consolidate".
   - **Resolve definitions + dataset references.** A `{{ @definition_name }}` inlines a
     reusable SQL snippet; a report that reads another report's query as a **dataset** is a
     cross-report dependency. Resolve each to concrete SQL (a CTE or an upstream cell) so
     nothing dangles. → [`mode-semantics.md`](reference/mode-semantics.md) §"Definitions & datasets".
   - **Sweep ALL Liquid + parameters.** `{% form %}` blocks define the report's parameters;
     `{{ @param }}` references consume them; `{% if %}`/`{% assign %}`/`{% case %}` branch
     the SQL. Sweep every branch — a parameter that rewrites the `WHERE` changes the
     population of *every* chart on that query. → [`mode-semantics.md`](reference/mode-semantics.md) §"Liquid".
   - **Map the Python/R notebook.** Mode notebook cells read query results as
     `datasets['Query Name']`; port each to a Hex Python cell reading the upstream SQL
     cell's dataframe. R → port to Python (or flag). → [`mode-semantics.md`](reference/mode-semantics.md) §"Notebook".
   - **Extract the styling values now into a styling spec** (chart titles, chart types,
     per-series colors as **hex codes from the chart JSON / HTML CSS**, number/date
     formats, big-number tiles, the report layout). This drives both the generative-app
     build and the visual-QA diff → [`build-generative-app.md`](reference/build-generative-app.md).
   - Export the original's PNGs for QA: `python scripts/mode_shots.py "<report url>"`.

4. **Build path — generative app is the default; native hand-build is a fallback.** There's no "which mode" question in the normal case: **build a generative app.** You only drop to the fallback when the notebook agent isn't available (feature off / no Hex credits).

   | Path | Presentation layer | SQL data layer | Cost | When |
   |---|---|---|---|---|
   | **Generative app (DEFAULT)** | notebook agent builds a **Generative app** (`genAppFiles`) reading the SQL dataframes | native SQL cells — gated the same way regardless of who wrote them | Hex credits (+ your tokens if you pre-build the SQL) | **every migration**, unless the notebook agent is unavailable |
   | **Native hand-build (FALLBACK)** | this coding agent hand-builds native EXPLORE/METRIC cells | this coding agent hand-builds (YAML) | your model tokens | **only** when the notebook agent is unavailable |

   Generative (default) → [`build-generative-app.md`](reference/build-generative-app.md), using the brief/handoff mechanics in [`build-notebook-agent.md`](reference/build-notebook-agent.md) and the render gate [`visual-qa-loop.md`](reference/visual-qa-loop.md). Fallback → [`building-cells.md`](reference/building-cells.md).

   **SQL-first within the generative default.** The app's data layer is always native, inspectable, gated SQL cells — the app reads those dataframes and never re-queries. Two ways to get there: (a) **pre-build + gate the SQL yourself first** (YAML) when the population is subtle (a `{% form %}` param that rewrites the `WHERE`, a definition that hides a join, a relative-date window) — pin the numbers before the app is built; or (b) let the **notebook agent build the SQL cells too** and run the fidelity gate **post-hoc** on them. Default to (b); escalate to (a) for high-stakes/subtle-population reports. Either way the SQL is gated before the migration ships. Because Mode SQL is already the warehouse dialect (when the connection is unchanged), pre-building is often just *paste the query, replace the Liquid with Hex params, validate it runs* — cheaper here than in a Tableau migration.

5. **Build the generative app (default).** Write the **migration brief** + **styling spec** (intent, not literal SQL — the queries and *what each represents*, plus params, chart specs, notebook logic, layout, and the hex-code styling), inject them as project cells (⚠️ `{% raw %}`-wrapped), then hand off to the notebook agent with a prompt that **opens** with *"Build this as a GENERATIVE APP (App builder → Generative app), not a classic notebook"* and tells it to read those dataframes rather than re-query. `hex thread create --json` → **give the customer the live URL immediately** so they can watch/intervene. Verify `genAppFiles` is non-empty in the export. Full procedure + prompt template → [`build-generative-app.md`](reference/build-generative-app.md); brief/handoff mechanics → [`build-notebook-agent.md`](reference/build-notebook-agent.md).
   - **Fallback only (notebook agent unavailable):** clone-and-override native cells from `templates/` → [`building-cells.md`](reference/building-cells.md).

6. **SQL-fidelity gate (mandatory — the accuracy guarantee).** The gate reviews the SQL *whoever wrote it*. Read every SQL cell's values (`hex cell run --with-output`) and export its source; write a **translation ledger**, **independently re-derive** the intended SQL from the Mode query + Liquid and **diff** it (spawn a subagent where supported), run the **mistake-class checklist** (Liquid param wiring, definition inlining, dataset-ref resolution, dialect drift *if warehouse changed*, `{% if %}` branch coverage, dedup/fan-out join, relative-date window), and **prove** suspect filters/joins with differential probes. It runs on the native SQL cells under the app — **post-hoc** when the agent built the SQL, or *before* the app when you pre-built it (the app reads those gated dataframes and never re-queries). Any divergence → fix (agent-built SQL: `hex thread continue` naming the divergence, or edit the cell; pre-built/fallback: edit the SQL) and re-check. Full procedure → [`sql-review.md`](reference/sql-review.md).

   > **When the connection is unchanged, the gate has a strong anchor Tableau never had:** the Mode query's own SQL is the reference. A ported cell that diverges *textually* from the source query (beyond the Liquid→param swap) is the first thing to explain. Lean on that.

7. **Run and QA.** `hex project run` (async — poll `run status`). Confirm what it built via `hex project export`: **`genAppFiles` non-empty** (it's a generative app, not classic — re-prompt if empty), SQL cells present + unchanged, params wired. Then the visual gate:
   - **Generative app (default):** run the **visual-QA loop** — headless Playwright screenshot (persistent profile) → panel-by-panel diff vs. the source Mode PNG → surgical `hex thread continue` fix batch → repeat until parity, then a final human confirm. This is an automated render gate, not a punt to the human → [`visual-qa-loop.md`](reference/visual-qa-loop.md).
   - **Fallback (native hand-build):** hand the customer the project link + the original PNGs (`scripts/mode_shots.py`) for **visual QA** side-by-side — this agent can't render native cells, so the human is the gate. App layout via export/import → [`gotchas.md`](reference/gotchas.md).

8. **Author a Hex guide for the data source (once per data source).** Ship a semantic layer, not just charts: mirror the Mode data source + its reused **definitions** as a retrieved Hex guide (canonical metrics + join patterns + migration risk areas) so the team can self-serve in Threads / the notebook agent. Built from the parse, reused across reports on that data source, published via `hex guide preview`/`publish`. Template → [`datasource-guide.md`](reference/datasource-guide.md).

---

# Batch migration (folder loop)

Point at a folder of report exports and migrate them as a set. Three phases:

**Phase 1 — parallel, read-only (safe to fan out):** scan → pull + parse each report (queries + SQL, Liquid params, definitions, dataset refs, chart defs, notebook cells, data source) → resolve each connection (+ same-warehouse-or-not) → **cluster queries into shared SQL cells** → produce a per-report **plan + draft brief**. **Batch every ambiguous-connection question into ONE ask**, and **ask the build-path once for the batch** (step 4) — don't stop per report.

**Phase 2 — sequential, mutating (one report at a time):** run the *Porting a report* loop for each — brief → build → **SQL-fidelity gate** → record the gate result in the manifest `notes`. **Write status to the manifest after each** so the batch is resumable and fail-soft. **Author each data source's guide once.**

**Phase 3 — verify (one batch):** collect all project links + original PNGs and present them for human visual QA in one pass.

### Manifest (`migrations.json`) — the resumable backbone
```json
[
  {
    "report_token": "a1b2c3d4e5f6",
    "title": "Marketing Funnel",
    "space": "Growth",
    "hex_project_id": null,
    "connection_id": "019a59ac-8c0f-...",
    "same_warehouse": true,             // true → SQL ports near-verbatim | false → dialect translation owed
    "build_path": "generative",         // generative (default) | native-fallback
    "sql_source": "agent",              // agent (built + gated post-hoc) | prebuilt (gated first)
    "thread_id": null,                  // notebook-agent thread (generative path)
    "status": "pending",                // pending → parsed → briefed → built → gated → run → verified | failed
    "queries": 4,
    "sql_cells": 2,                     // shared SQL cells after clustering
    "has_notebook": false,              // Python/R notebook cells present?
    "layout": "report-builder",         // report-builder | html-liquid | notebook-only
    "gate": "",                         // e.g. "12 rows, KPIs tie; no divergence"
    "notes": ""                         // e.g. "R cell → python", "ambiguous connection: asked", "html report page"
  }
]
```
On rerun, skip any report whose `status` is `verified`. Record `failed` + the error in `notes` and continue.

---

# Files in this skill
- `SKILL.md` — this playbook (workflow spine).
- `reference/` — `connection-mapping.md`, `mode-semantics.md` (understand the report), `build-generative-app.md` (**the default build** — Generative app), `build-notebook-agent.md` (brief + handoff mechanics), `visual-qa-loop.md` (render gate), `sql-review.md` (fidelity gate), `building-cells.md` (**fallback only** — hand-build native cells), `datasource-guide.md`, `gotchas.md`.
- `templates/` — clone-and-override native-cell configs for the **fallback** hand-build (METRIC + EXPLORE variants, `_filter_snippet.json`). *(Reused verbatim from the Tableau skill — they're Hex-side target format, source-agnostic.)*
- `scripts/mode_fetch.py` — fetch reports (JSON + query SQL + chart defs + notebook) from the Mode API (`--list` / `--name` / `--space`).
- `scripts/mode_shots.py` — headless Playwright screenshot of a Mode report (persistent profile, one-time login) for the visual-QA gate.
- `scripts/hex_shots.py` — headless Playwright screenshot of the built Hex app (persistent profile, one-time login) for the visual-QA loop.
- `credentials/mode.env.example` — template for Mode workspace slug + API token + secret. Copy to `mode.env` (gitignored).
- `mode_exports/`, `working/` — local downloads + scratch (gitignored).

## Hex CLI cheat-sheet (verified against `hex 1.2026.07.21`)
- **Notebook agent (default build):** `hex thread create "<prompt>" --project <id> --json` → `url` (**hand to the customer to watch/intervene**) + `thread_id`; poll `hex thread get <id>` (`RUNNING`→`IDLE`); iterate `hex thread continue <id> "<prompt>"`. Uses Hex credits; needs the headless-agent-threads feature.
- **Generative app (default form):** the prompt **must open** with "Build this as a GENERATIVE APP…, not a classic notebook" — no CLI flag controls form. Verify with `hex project export <id>` → `genAppFiles` non-empty; re-prompt if it built classic.
- **Hex app screenshot (visual-QA gate):** one-time `python scripts/hex_shots.py --login` (headed; customer signs in), then `python scripts/hex_shots.py "<url>" -o working/shots/migrated.png` (headless). Mode source shots: one-time `python scripts/mode_shots.py --login`, then `python scripts/mode_shots.py "<report url>" -o working/shots/source.png`. Needs `pip install playwright && playwright install chromium`.
- **Cells:** `hex cell create` makes only code/sql/markdown; INPUT (parameter) cells + connection-less dataframe-SQL companions are authored in YAML (fallback / pre-built-SQL). ⚠️ Injected markdown reference cells (report JSON, raw Liquid SQL, brief, spec) must be `{% raw %}`-wrapped or their `{{ }}`/`{% %}` tokens ERROR the run. `hex cell run <id> --with-output` returns result rows; after a YAML import use the **API id from `hex cell list`**, not the export `cellId`.
- **Guides (headless):** `hex guide preview <*.md>` → `preview_id`; `hex guide publish <preview_id>`. Markdown only.
