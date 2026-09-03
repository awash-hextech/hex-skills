---
name: mode-migration-classic
description: >-
  Migrate Mode (Mode Analytics / ThoughtSpot Mode) reports into Hex as a CLASSIC
  app — native notebook cells (SQL, input parameters, EXPLORE/METRIC/pivot charts)
  assembled in an app layout — by delegating the build to Hex's in-product notebook
  agent. Use when someone wants to convert, port, rebuild, or migrate Mode content
  (reports, queries, charts, Report Builder / HTML-Liquid layouts, Python/R notebooks)
  into Hex and wants a maintainable native dashboard rather than a generative code
  app. This coding agent reads the report's SQL + Liquid + chart defs as the source of
  truth, translates the Mode-specific bits (Liquid params, definitions, dataset refs)
  and writes a migration brief; Hex's notebook agent builds the native cells + app
  layout over gated SQL; this agent verifies with a SQL-fidelity gate, a cell-spec
  diff, and a visual-QA loop. Triggers: "migrate Mode to Hex as a classic app", "port
  my Mode reports to native Hex cells", "Mode → Hex (classic app)". For a generative
  app, use the sibling `mode-migration` skill.
---

# Mode → Hex Migration (classic-app build)

A CLI-driven migration where this coding agent understands the Mode source and
verifies the result, and Hex's in-product notebook agent builds the dashboard as a
**classic app** — native notebook cells arranged in an app layout. You fetch a report
via the Mode API, read its **queries (SQL), Liquid templating, chart defs, and any
Python/R notebook** as the source of truth, translate the Mode-specific semantics, and
write a migration brief into the Hex project; the notebook agent reads that brief and
builds native SQL + INPUT + EXPLORE/METRIC/pivot cells plus the `appLayout`; then you run
a SQL-fidelity gate on the SQL, a **cell-spec diff** on the viz cells, and a visual-QA
loop on the render.


> **The deliverable is a classic app.** Every chart is a real Hex cell with an editable
> spec, the numbers sit in inspectable, gated SQL cells, filters are INPUT cells, and the
> whole thing is maintainable by the customer's analysts with no code. It is also
> **mechanically diff-able** — the exported YAML carries chart type, encodings, colors, and
> formats, so fidelity is verified against the styling spec, not just by eye.
>
> **The trade-off, state it up front:** native cells **cannot** reproduce a bespoke
> HTML/Liquid Mode report page (custom CSS, D3/JS embeds). Those become native
> approximations + named gaps. If pixel fidelity to a hand-built HTML report is the
> requirement, use the sibling **`mode-migration`** skill, which delivers a generative app.

## Why delegate the build to the notebook agent

This coding agent (reading this skill) is blind to the things that make the build
correct, meaning that it can't see the live warehouse schema or data, workspace context, nor rendered result. The notebook agent has visibility into all three since it runs inside the workspace. So for building in Hex it is the better-equipped agent and delegating the classic-app build to it is the default path. Please note that this spends Hex credits.

> **Division of labor:** this coding agent owns understanding the Mode report, including
> (the durable IP: reading each query's SQL + Liquid, resolving definitions/dataset
> refs, translating params, mapping Python/R notebook logic and the report layout) and
> **verifying the result** (the fidelity gate + the cell-spec diff). The notebook agent
> owns **building it in Hex**. Accuracy is guaranteed by the gate — which reviews whoever
> wrote the SQL — not by this agent hand-writing every query.

**Priority order (say this to the customer up front):** (1) **accuracy** of SQL +
visuals first, (2) **similar look & feel** second, (3) **maintainability** — which the
classic build buys you outright, since the result is native cells the team can edit.
The look-&-feel ceiling is lower than the generative build's: Hex's native chart styling,
mirrored **structure** (rows + column spans) rather than pixels, and no bespoke CSS. Some
Mode features have **no** native analogue (a hand-built HTML report page, D3/JS embeds,
maps, ratio-of-aggregates in a chart) — name those early, with their agreed substitute, so
"it isn't pixel-identical" is never a surprise. Philosophy: **cover the basis, don't
gold-plate.**

## Reference docs (read on demand)
- [`reference/connection-mapping.md`](reference/connection-mapping.md) — resolve the Mode data source → Hex data connection, and decide whether the warehouse (and thus the SQL dialect) changes.
- [`reference/mode-semantics.md`](reference/mode-semantics.md) — **understand the report:** Mode construct → Hex meaning. SQL ports near-verbatim; the real work is **Liquid** (`{{ @param }}`, `{% form %}`, `{% if %}`, definitions), **query/dataset dependencies**, **Python/R notebook** cells, chart defs, and the dialect step *only if the warehouse changes*. This is what you distill into the brief.
- [`reference/build-classic-app.md`](reference/build-classic-app.md) — **the build (default):** gate the SQL natively, then have the agent build **native viz cells + the app layout** on top; the known ceilings, the styling spec, the prescriptive prompt, the "is it classic?" verification, and the **cell-spec diff gate**.
- [`reference/building-cells.md`](reference/building-cells.md) — **the native-cell capability map** (what EXPLORE/METRIC can and can't express, the clone-and-override templates, the `seriesId` trap, the METRIC 1-row rule) — *and* the hand-build procedure for the fallback when the notebook agent is unavailable. Read it in the classic build even when delegating.
- [`reference/build-notebook-agent.md`](reference/build-notebook-agent.md) — **brief + handoff mechanics:** how to write the migration brief (intent, not literal SQL), inject it (⚠️ `{% raw %}`-wrapped — doubly important, Mode SQL is *full* of `{{ }}`/`{% %}`), hand it to the notebook agent, surface the live URL, and iterate.
- [`reference/visual-qa-loop.md`](reference/visual-qa-loop.md) — **render gate:** headless Playwright screenshot (persistent profile, one-time login) → panel-by-panel diff vs. the source Mode PNG → surgical fix batch → repeat. Run it *after* the cell-spec diff is clean.
- [`reference/sql-review.md`](reference/sql-review.md) — **SQL-fidelity gate:** ledger → independent re-derivation & diff → mistake-class checklist → read-back + differential probes. Runs on the native SQL cells under the app.
- [`reference/datasource-guide.md`](reference/datasource-guide.md) — author a Hex guide mirroring the Mode data source / definitions (semantic layer for Threads/agent), published via `hex guide`.
- [`reference/gotchas.md`](reference/gotchas.md) — parsing correctness rules, Hex CLI quirks, **app layout** (first-class here).

## What you need before starting
- **Mode access** — a Mode **API token + secret** (for `scripts/mode_fetch.py`) *or* exported report contents. The token's workspace must be able to see the reports.
- **Hex CLI** installed and authed; the **target Hex data connection** the migrated cells will query; and the **headless-agent-threads feature enabled** for the workspace (the default build path uses `hex thread`).
- `credentials/mode.env` filled in from `credentials/mode.env.example` (workspace/account slug + API token + secret). Gitignored.
- **Visual-QA render gate:** `pip install playwright && playwright install chromium`, plus a **one-time headed login** into each screenshot profile — one for Hex, one for Mode (the customer signs in once each; every later capture is headless). See [`visual-qa-loop.md`](reference/visual-qa-loop.md).
- **Hex-YAML editor validation** — the RedHat YAML VS Code extension, for the YAML round-trips this path uses (INPUT cells, dataframe-SQL companions, `appLayout` edits, and any hand-build). See [`building-cells.md`](reference/building-cells.md).

## Workflow at a glance
0. **Prioritize & organize** the customer's reports → one folder.
1. **Pilot 1–2 reports** end-to-end, QA, tune.
2. **Port each report:** resolve connection (+ decide if the warehouse/dialect changes) → pull + read queries/Liquid/charts/notebook → name the **native-cell gaps** → build the **classic app** (gate the SQL layer natively, then native viz cells + `appLayout` on top; hand-build only if the notebook agent is unavailable) → **SQL-fidelity gate** + **cell-spec diff** + **visual-QA loop** → ship the guide.
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

4. **Complexity triage — set expectations, and route the outliers.** The classic build has
   a real ceiling, so triage is also a **routing** decision. Flag these up front (detail in
   [`build-classic-app.md`](reference/build-classic-app.md) §Known ceilings and
   [`gotchas.md`](reference/gotchas.md)):
   - **Bespoke HTML report pages with custom CSS / D3 / JS** → ⚠️ **the weakest fit for a
     classic app.** Native cells reproduce the *content and row order*, not the styling.
     Either agree to a native approximation, or migrate **that report** with the sibling
     `mode-migration` (generative) skill. Decide per report, not for the whole batch.
   - **Charts plotting a ratio of aggregates** (margin %, conversion rate) → EXPLORE can't
     compute it; **pre-compute in SQL** at the chart's grain.
   - **Maps** → Python cell (plotly), no native map.
   - **R notebook cells** → port logic to Python (or flag).
   - **Python notebook cells that call external services / pip packages** → confirm
     availability in Hex.
   - **Non-warehouse query results** (uploaded CSVs, Google Sheets, Mode's own "helper"
     datasets) → rows aren't in the warehouse; **ask the customer for the source**.
   - **`{% form %}`-driven dynamic SQL** → maps to Hex INPUT params but sweep every branch.

   Put these in the brief as known gaps **with their agreed substitute** so the notebook
   agent doesn't silently approximate them.

# First pass — cap at 1–2 reports (pilot, then scale)

**Do not run the full folder first.** Migrate **one or two** reports end-to-end, then stop and tune.
- **Pick the pilot(s):** one *simple/representative*; if two, add one *representative-complex* (a report with a ratio chart, several `{% form %}` params, or a Python notebook surfaces gaps early). Don't make the single hardest edge case your only pilot.
- **Go all the way:** pull → brief + styling spec → gate the SQL → build the classic app → cell-spec diff → visual-QA loop → **customer's final visual confirm** vs. the Mode original.
- **Tune, then scale:** fold fixes (connection mapping, Liquid translations, brief wording, format mappings, prompt phrasing that reliably yields native cells, layout grid choices, screenshot-selector tweaks) back into this playbook *before* batching the rest.

Why: the gates get the result close automatically, but a human confirm on a tiny first batch catches systematic errors before they multiply.

# Guiding the customer
- **State the priority order up front** (accuracy first, look & feel second, maintainability as the reason for this build) and that the deliverable is a **classic Hex app made of native cells**.
- **State the ceiling in the same breath:** a bespoke HTML/CSS Mode report page won't come across pixel-for-pixel; you'll mirror structure and content natively, or route that report to the generative skill. Get that agreed *before* building.
- **Name the human gates:** (1) **data connection** — you'll ask when the target is ambiguous, and confirm whether the warehouse (and dialect) is the same or changes; (2) **screenshot logins** — the one-time headed sign-ins (Hex + Mode) that power the visual-QA loop; (3) **final visual confirm** — the gates drive the render to near-parity automatically, then the customer signs off on the pilot and each batch. (You only surface the *builder* as a question if the notebook agent is unavailable and you must hand-build.)
- **Tell them what to provide:** Mode API token + secret *or* exported report contents; which **Hex data connection** to target (and whether it's the same warehouse Mode queried); and that the default build spends **Hex credits** (needs the headless-agent-threads feature).
- **Work in waves:** pilot → tune → batch a wave → QA → next wave.

---

# Porting a report (the core per-report loop)

1. **Resolve the data connection, then note its SQL dialect — and whether it changed.**
   A Mode report's queries each name a **data source**; match it to a Hex connection on
   metadata (type + database), not names/hosts. Full procedure →
   [`connection-mapping.md`](reference/connection-mapping.md). ⚠️ **The dialect step is
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
   - **Map each tile to a native cell type, and catch what native cells can't do.** Per
     tile: EXPLORE (which variant), METRIC, `pivot-table`, markdown, or Python 🐍. Flag
     **ratios of aggregates** (need a pre-computed SQL column), **maps** (Python), and
     **bespoke HTML/D3** (approximate + gap) *now*, while you still have the parse open →
     [`building-cells.md`](reference/building-cells.md), [`build-classic-app.md`](reference/build-classic-app.md) §Known ceilings.
   - **Extract the styling values now into a styling spec** (chart titles, cell types,
     encodings, per-series colors as **hex codes from the chart JSON / HTML CSS**,
     number/date formats, big-number tiles, and each tile's **row + width share**). This
     drives the build, the cell-spec diff, and the visual-QA diff →
     [`build-classic-app.md`](reference/build-classic-app.md).
   - Export the original's PNGs for QA: `python scripts/mode_shots.py "<report url>"`.

4. **Builder — delegate by default; hand-build is the fallback.** There's no "which form"
   question: **build a classic app of native cells.** The only question is *who builds it*,
   and you only hand-build when the notebook agent isn't available (feature off / no Hex
   credits).

   | Builder | Presentation layer | SQL data layer | Cost | When |
   |---|---|---|---|---|
   | **Notebook agent (DEFAULT)** | agent builds native EXPLORE/METRIC/pivot cells + `appLayout` | native SQL cells — gated the same way regardless of who wrote them | Hex credits (+ your tokens if you pre-build the SQL) | **every migration**, unless the notebook agent is unavailable |
   | **Hand-build (FALLBACK)** | this coding agent clones templates → native cells + `appLayout` (YAML) | this coding agent hand-builds (YAML) | your model tokens | **only** when the notebook agent is unavailable |

   Default → [`build-classic-app.md`](reference/build-classic-app.md), using the brief/handoff
   mechanics in [`build-notebook-agent.md`](reference/build-notebook-agent.md), the capability
   map + templates in [`building-cells.md`](reference/building-cells.md), and the render gate
   [`visual-qa-loop.md`](reference/visual-qa-loop.md). The artifact is the same either way —
   only the builder changes.

   **SQL-first either way.** The app's data layer is always native, inspectable, gated SQL
   cells — the charts read those dataframes and never re-query. Two ways to get there:
   (a) **pre-build + gate the SQL yourself first** (YAML) when the population is subtle (a
   `{% form %}` param that rewrites the `WHERE`, a definition that hides a join, a
   relative-date window) — pin the numbers before any chart is built; or (b) let the
   **notebook agent build the SQL cells too** and run the fidelity gate **post-hoc** on
   them. Default to (b); escalate to (a) for high-stakes/subtle-population reports. Either
   way the SQL is gated before the migration ships. Because Mode SQL is already the
   warehouse dialect (when the connection is unchanged), pre-building is often just *paste
   the query, replace the Liquid with Hex params, validate it runs* — cheaper here than in
   a Tableau migration. ⚠️ **Ratio tiles are a reason to pre-build:** the ratio column has
   to exist in SQL before a chart can plot it.

5. **Build the classic app (default).** Write the **migration brief** + **styling spec**
   (intent, not literal SQL — the queries and *what each represents*, plus params, the
   **cell type + encodings per tile**, notebook logic, the row-by-row layout with width
   shares, and the hex-code styling), inject them as project cells (⚠️ `{% raw %}`-wrapped),
   then hand off to the notebook agent with a **prescriptive** prompt: *"Build this as a
   CLASSIC HEX APP using native notebook cells — SQL, input parameters, and native chart
   cells (EXPLORE/METRIC/pivot) arranged in the App builder layout. Do NOT build a
   Generative app."* Name the dataframes the charts must read, tell it to **consolidate**
   (not one query per chart), and to keep reference/SQL cells **out** of the layout.
   `hex thread create --json` → **give the customer the live URL immediately** so they can
   watch/intervene. Verify `genAppFiles` is **empty** and `appLayout` is populated. Full
   procedure + prompt template → [`build-classic-app.md`](reference/build-classic-app.md);
   brief/handoff mechanics → [`build-notebook-agent.md`](reference/build-notebook-agent.md).
   - **Fallback only (notebook agent unavailable):** clone-and-override native cells from
     `templates/` and assemble the `appLayout` yourself → [`building-cells.md`](reference/building-cells.md).

6. **SQL-fidelity gate (mandatory — the accuracy guarantee).** The gate reviews the SQL *whoever wrote it*. Read every SQL cell's values (`hex cell run --with-output`) and export its source; write a **translation ledger**, **independently re-derive** the intended SQL from the Mode query + Liquid and **diff** it (spawn a subagent where supported), run the **mistake-class checklist** (Liquid param wiring, definition inlining, dataset-ref resolution, dialect drift *if warehouse changed*, `{% if %}` branch coverage, dedup/fan-out join, relative-date window), and **prove** suspect filters/joins with differential probes. It runs on the native SQL cells under the app — **post-hoc** when the agent built the SQL, or *before* the build when you pre-built it. Any divergence → fix (agent-built SQL: `hex thread continue` naming the divergence, or edit the cell; pre-built/hand-built: edit the SQL) and re-check. Full procedure → [`sql-review.md`](reference/sql-review.md).

   > **When the connection is unchanged, the gate has a strong anchor Tableau never had:** the Mode query's own SQL is the reference. A ported cell that diverges *textually* from the source query (beyond the Liquid→param swap) is the first thing to explain. Lean on that.

7. **Cell-spec diff gate (classic-only — do it before screenshotting).** `hex project export`
   and check each viz cell's spec against the styling spec: `cellType` /
   `visualizationType`, `config.dataframe`, every encoding in `spec.fields[]` (channel,
   column, aggregation, `truncUnit`), **`dataType: DATE` on date axes**, `displayFormat`,
   the **hex codes** in `colorMappings`/`chartConfig.series[]`, the
   **`seriesId == series.id == seriesGroups id`** linkage (a mismatch renders blank while
   the cell still reports COMPLETED), and the `appLayout` (every viz cell present, no
   reference/SQL cells, **no fixed `height` on chart EXPLOREs**). This is fidelity checking
   the generative build simply couldn't do — most look-&-feel bugs are catchable here
   without rendering anything. → [`build-classic-app.md`](reference/build-classic-app.md)
   §Verify accuracy + fidelity.

8. **Run and QA the render.** `hex project run` (async — poll `run status`). Confirm what it
   built via `hex project export`: **`genAppFiles` empty** (it's classic, not generative —
   re-prompt if non-empty), native viz cells present, SQL cells present + unchanged, params
   wired **upstream** of their consumers, `appLayout` populated. Then:
   - **Visual-QA loop:** headless Playwright screenshot (persistent profile) → panel-by-panel
     diff vs. the source Mode PNG → surgical `hex thread continue` fix batch (or a YAML
     `appLayout` edit) → repeat until parity, then a final human confirm. ⚠️ **COMPLETED ≠
     renders correctly** — a broken viz spec passes the run oracle, so the render gate is not
     optional → [`visual-qa-loop.md`](reference/visual-qa-loop.md).
   - **Layout fixes** are often faster as a direct export → edit `appLayout` → import round-trip
     than as a prompt → [`gotchas.md`](reference/gotchas.md) §App layout.

9. **Author a Hex guide for the data source (once per data source).** Ship a semantic layer, not just charts: mirror the Mode data source + its reused **definitions** as a retrieved Hex guide (canonical metrics + join patterns + migration risk areas) so the team can self-serve in Threads / the notebook agent. Built from the parse, reused across reports on that data source, published via `hex guide preview`/`publish`. Template → [`datasource-guide.md`](reference/datasource-guide.md).

---

# Batch migration (folder loop)

Point at a folder of report exports and migrate them as a set. Three phases:

**Phase 1 — parallel, read-only (safe to fan out):** scan → pull + parse each report (queries + SQL, Liquid params, definitions, dataset refs, chart defs, notebook cells, data source) → resolve each connection (+ same-warehouse-or-not) → **cluster queries into shared SQL cells** → **map each tile to a native cell type and record the native-cell gaps** → produce a per-report **plan + draft brief + styling spec**. **Batch every ambiguous-connection question into ONE ask**, and **ask once for the batch** about any report whose bespoke HTML layout should be routed to the generative skill instead (step 0.4) — don't stop per report.

**Phase 2 — sequential, mutating (one report at a time):** run the *Porting a report* loop for each — brief → build → **SQL-fidelity gate** → **cell-spec diff** → record both gate results in the manifest. **Write status to the manifest after each** so the batch is resumable and fail-soft. **Author each data source's guide once.**

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
    "builder": "agent",                 // agent (default) | handbuilt (notebook agent unavailable)
    "sql_source": "agent",              // agent (built + gated post-hoc) | prebuilt (gated first)
    "thread_id": null,                  // notebook-agent thread
    "status": "pending",                // pending → parsed → briefed → built → gated → spec-diffed → run → verified | failed
    "queries": 4,
    "sql_cells": 2,                     // shared SQL cells after clustering
    "viz_cells": 6,                     // native EXPLORE/METRIC/pivot cells
    "has_notebook": false,              // Python/R notebook cells present?
    "layout": "report-builder",         // report-builder | html-liquid | notebook-only
    "native_gaps": [],                  // e.g. ["bespoke CSS not reproduced", "map → python cell"]
    "gate": "",                         // e.g. "12 rows, KPIs tie; no divergence"
    "spec_diff": "",                    // e.g. "clean" | "2 color fixes, 1 date-axis fix"
    "notes": ""                         // e.g. "R cell → python", "ratio pre-computed in SQL", "html report: native approximation agreed"
  }
]
```
On rerun, skip any report whose `status` is `verified`. Record `failed` + the error in `notes` and continue.

---

# Files in this skill
- `SKILL.md` — this playbook (workflow spine).
- `reference/` — `connection-mapping.md`, `mode-semantics.md` (understand the report), `build-classic-app.md` (**the default build** — native cells + app layout), `building-cells.md` (**native-cell capability map** + hand-build fallback), `build-notebook-agent.md` (brief + handoff mechanics), `visual-qa-loop.md` (render gate), `sql-review.md` (fidelity gate), `datasource-guide.md`, `gotchas.md`.
- `templates/` — clone-and-override native-cell configs (METRIC + EXPLORE variants, `_filter_snippet.json`). The **target format of this build** — a reference for the delegated build and the source material for the hand-build fallback. *(Reused verbatim from the Tableau skill — they're Hex-side target format, source-agnostic.)*
- `scripts/mode_fetch.py` — fetch reports (JSON + query SQL + chart defs + notebook) from the Mode API (`--list` / `--name` / `--space`).
- `scripts/mode_shots.py` — headless Playwright screenshot of a Mode report (persistent profile, one-time login) for the visual-QA gate.
- `scripts/hex_shots.py` — headless Playwright screenshot of the built Hex app (persistent profile, one-time login) for the visual-QA loop.
- `credentials/mode.env.example` — template for Mode workspace slug + API token + secret. Copy to `mode.env` (gitignored).
- `mode_exports/`, `working/` — local downloads + scratch (gitignored).

## Sibling skill
**`mode-migration`** is the same playbook delivering a **generative app** (a bespoke code
app — `genAppFiles`) instead of native cells. Prefer it for a Mode report that is a
**hand-built HTML/Liquid page** with custom CSS and D3/JS, where pixel fidelity outranks
maintainability. Prefer *this* skill when the customer wants a native Hex dashboard their
analysts can edit. The Mode-side parsing, the brief, and the SQL gate are identical.

**Getting it:** in the `hex-skills` marketplace it's a separate plugin
(`/plugin install mode-migration@hex-skills`); in the `hex-migrations` plugin the two ship
together and resolve as `hex-migrations:mode-migration`. If neither is installed, the
routing advice above still applies — you just can't hand a report off to it.

## Hex CLI cheat-sheet (verified against `hex 1.2026.07.21`)
- **Notebook agent (default builder):** `hex thread create "<prompt>" --project <id> --json` → `url` (**hand to the customer to watch/intervene**) + `thread_id`; poll `hex thread get <id>` (`RUNNING`→`IDLE`); iterate `hex thread continue <id> "<prompt>"`. Uses Hex credits; needs the headless-agent-threads feature.
- **Classic app (the form we want):** no CLI flag controls form — the prompt does. Be **prescriptive about cell types** and say *"do NOT build a Generative app."* Verify with `hex project export <id>` → `genAppFiles` **empty/absent**, native `cellType`s present, `appLayout.tabs[].rows[]` populated; re-prompt if it built generative.
- **Hex app screenshot (visual-QA gate):** one-time `python scripts/hex_shots.py --login` (headed; customer signs in), then `python scripts/hex_shots.py "<url>" -o working/shots/migrated.png` (headless). Mode source shots: one-time `python scripts/mode_shots.py --login`, then `python scripts/mode_shots.py "<report url>" -o working/shots/source.png`. Needs `pip install playwright && playwright install chromium`.
- **Cells:** `hex cell create` makes only code/sql/markdown; **native viz cells (EXPLORE/METRIC/pivot), INPUT (parameter) cells, and connection-less dataframe-SQL companions are authored in YAML** — plan on a YAML round-trip on the hand-build path and for surgical fixes. ⚠️ Injected markdown reference cells (report JSON, raw Liquid SQL, brief, spec) must be `{% raw %}`-wrapped or their `{{ }}`/`{% %}` tokens ERROR the run. `hex cell run <id> --with-output` returns result rows; after a YAML import use the **API id from `hex cell list`**, not the export `cellId`.
- **App layout:** `hex project export <id> -o f.yaml` → edit `appLayout` → `hex project import f.yaml`. Never put reference/raw-SQL cells in the layout; never set a fixed `height` on a chart-type EXPLORE element. → [`gotchas.md`](reference/gotchas.md).
- **Guides (headless):** `hex guide preview <*.md>` → `preview_id`; `hex guide publish <preview_id>`. Markdown only.
