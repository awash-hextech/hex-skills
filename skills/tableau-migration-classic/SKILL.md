---
name: tableau-migration-classic
description: >-
  Migrate Tableau dashboards/workbooks into Hex as a CLASSIC app — native notebook
  cells (SQL, input parameters, EXPLORE/METRIC/pivot charts) assembled in an app
  layout — by delegating the build to Hex's in-product notebook agent. Use when
  someone wants to convert, port, rebuild, or migrate Tableau content (.twb / .twbx,
  Tableau Cloud/Server views) into Hex and wants a maintainable native dashboard
  rather than a generative code app. This coding agent parses the workbook XML as the
  source of truth, translates the Tableau semantics (calcs, LOD, table calcs, filters,
  params) and writes a migration brief; Hex's notebook agent builds the native cells +
  app layout over gated SQL; this agent verifies with a SQL-fidelity gate, a cell-spec
  diff, and a visual-QA loop. Triggers: "migrate Tableau to Hex as a classic app",
  "port my Tableau dashboards to native Hex cells", "Tableau → Hex (classic app)".
  For a generative app, use the sibling `tableau-migration` skill.
---

# Tableau → Hex Migration (classic-app build)

A CLI-driven migration where this coding agent understands the Tableau source and
verifies the result, and Hex's in-product notebook agent builds the dashboard as a
**classic app** — native notebook cells arranged in an app layout. You fetch a workbook,
read its XML as the source of truth, translate its semantics, and write a **migration
brief** into the Hex project; the notebook agent reads that brief and builds native SQL +
INPUT + EXPLORE/METRIC/pivot cells plus the `appLayout`; then you run a **SQL-fidelity
gate** on the SQL, a **cell-spec diff** on the viz cells, and a **visual-QA loop** on the
render.

> **The deliverable is a classic app.** Every chart is a real Hex cell with an editable
> spec, the numbers sit in inspectable, gated SQL cells, filters are INPUT cells, and the
> whole thing is maintainable by the customer's analysts with no code. It is also
> **mechanically diff-able** — the exported YAML carries chart type, encodings, colors, and
> formats, so fidelity is verified against the styling spec, not just by eye.
>
> **The trade-off, state it up front:** native cells **cannot** reproduce Tableau's pixel
> chrome, and several Tableau constructs have no in-chart equivalent — **table calcs,
> running totals, LOD ratios and any ratio-of-aggregates must be pre-computed as SQL
> columns**, and maps / detail-text tooltips / iframe embeds become named gaps. If pixel
> fidelity outranks maintainability, use the sibling **`tableau-migration`** skill, which
> delivers a generative app.

## Why delegate the build to the notebook agent

This coding agent (reading this skill) is **blind to the things that make the build
correct**: it can't see the live **warehouse schema** or data, it can't see the customer's
**Hex workspace context** (Context Studio descriptions, endorsed tables, semantic models,
guides), and it can't see the **rendered result**. The notebook agent has all three — it
runs inside the workspace. So for *building in Hex* it is the better-equipped agent, and
delegating the classic-app build to it is the default path (it spends Hex credits).

> **Division of labor:** this coding agent owns **understanding the Tableau workbook**
> (the durable IP: reading the XML, translating calcs/LOD/table-calcs/filters/params) and
> **verifying the result** (the fidelity gate + the cell-spec diff). The notebook agent
> owns **building it in Hex**. Accuracy is guaranteed by the gate — which reviews whoever
> wrote the SQL — not by this agent hand-writing every query.

**Priority order (say this to the customer up front):** (1) **accuracy** of SQL + visuals
first, (2) **similar look & feel** second, (3) **maintainability** — which the classic
build buys you outright, since the result is native cells the team can edit. The
look-&-feel ceiling is lower than the generative build's: Hex's native chart styling,
mirrored **structure** (rows + column spans from the `.twb` zone geometry) rather than
pixels, and no bespoke chrome. Some Tableau features have **no** native analogue (maps,
detail/LOD text tooltips, web-page embeds, in-chart table calcs and ratios) — name those
early, with their agreed substitute, so "it isn't pixel-identical" is never a surprise.
Philosophy: **cover the basis, don't gold-plate.**

## Reference docs (read on demand)
- [`reference/connection-mapping.md`](reference/connection-mapping.md) — resolve the Tableau → Hex data connection.
- [`reference/tableau-semantics.md`](reference/tableau-semantics.md) — **understand the workbook:** Tableau construct → warehouse SQL/Python meaning (calcs, LOD, window calcs, params, sets, RLS), filter scopes, and how to cluster worksheets into shared derivations. This is what you distill into the brief.
- [`reference/build-classic-app.md`](reference/build-classic-app.md) — **the build (default):** gate the SQL natively, then have the agent build **native viz cells + the app layout** on top; the known ceilings, the styling spec, the prescriptive prompt, the "is it classic?" verification, and the **cell-spec diff gate**.
- [`reference/building-cells.md`](reference/building-cells.md) — **the native-cell capability map** (what EXPLORE/METRIC can and can't express, the clone-and-override templates, the `seriesId` trap, the METRIC 1-row rule, the dashboard-object table) — *and* the hand-build procedure for the fallback when the notebook agent is unavailable. Read it in the classic build even when delegating.
- [`reference/build-notebook-agent.md`](reference/build-notebook-agent.md) — **brief + handoff mechanics:** how to write the migration brief (intent, not literal SQL), inject it (⚠️ `{% raw %}`-wrapped), hand it to the notebook agent, surface the live URL, and iterate.
- [`reference/visual-qa-loop.md`](reference/visual-qa-loop.md) — **render gate:** headless Playwright screenshot (persistent profile, one-time login) → panel-by-panel diff vs. the source PNG → surgical fix batch → repeat. Run it *after* the cell-spec diff is clean.
- [`reference/sql-review.md`](reference/sql-review.md) — **SQL-fidelity gate:** ledger → independent re-derivation & diff → mistake-class checklist → read-back + differential probes. Runs on the native SQL cells under the app.
- [`reference/datasource-guide.md`](reference/datasource-guide.md) — author a Hex guide mirroring the Tableau data source (semantic layer for Threads/agent), published via `hex guide`.
- [`reference/gotchas.md`](reference/gotchas.md) — parsing correctness rules, Hex CLI quirks, **app layout** (first-class here).

## What you need before starting
- **Tableau access** — a Personal Access Token (for `scripts/tableau_fetch.py`) *or* exported `.twb`/`.twbx` files.
- **Hex CLI** installed and authed; the **target Hex data connection** the migrated cells will query; and the **headless-agent-threads feature enabled** for the workspace (the default build path uses `hex thread`).
- `credentials/tableau.env` filled in from `credentials/tableau.env.example` (pod URL + site + PAT). Gitignored.
- **Visual-QA render gate:** `pip install playwright && playwright install chromium`, plus a **one-time headed Hex login** into the screenshot profile (the customer signs in once; every later capture is headless). See [`visual-qa-loop.md`](reference/visual-qa-loop.md).
- **Hex-YAML editor validation** — the RedHat YAML VS Code extension, for the YAML round-trips this path uses (INPUT cells, dataframe-SQL companions, `appLayout` edits, and any hand-build). See [`building-cells.md`](reference/building-cells.md).

## Workflow at a glance
0. **Prioritize & organize** the customer's dashboards → one folder.
1. **Pilot 1–2 dashboards** end-to-end, QA, tune.
2. **Port each workbook:** resolve connection → parse XML + understand → name the **native-cell gaps** → build the **classic app** (gate the SQL layer natively, then native viz cells + `appLayout` on top; hand-build only if the notebook agent is unavailable) → **SQL-fidelity gate** + **cell-spec diff** + **visual-QA loop** → ship the guide.
3. **Batch the rest** with the folder loop + manifest.

---

# Step 0 — Prioritize & organize (do this FIRST, before any workbook)

Migration is the best moment a team ever gets to prune. Most Tableau sites are 60–80% dead weight — abandoned drafts, one-offs, near-duplicates. **Do not migrate what nobody uses.** Guide the customer through a short triage before a single `.twb` is fetched.

1. **Take inventory.** On Tableau Cloud/Server the fastest source is the site's *Views* admin export / "Content" list (carries **view counts** + **last-accessed**); otherwise ask. Per dashboard capture: name, owner, last-viewed, 90-day view count, and a one-line "what decision does this drive?"

2. **Prioritize on three axes**, then bucket:

   | Axis | Migrate-first | Drop / defer |
   |------|---------------|--------------|
   | **Usage** | viewed regularly, real audience | ~0 views in 90 days |
   | **Business value** | drives a recurring decision | ad-hoc / one-time / "nice to have" |
   | **Freshness / ownership** | actively maintained, clear owner | stale, orphaned |

   **Get the customer to confirm the buckets** — it's a business call: **Migrate**, **Archive/rebuild-later** (snapshot, don't port as-is), **Drop** (dead — say so). Collapse **near-duplicates** into one canonical version.

3. **Organize into ONE folder** (the batch loop points at a single directory of `.twb`s):
   - **Tableau Cloud/Server:** `scripts/tableau_fetch.py` (`--project` / `--name`) — downloads + auto-extracts `.twb` from `.twbx` into `tableau_exports/`.
   - **Local files:** customer exports `.twb`/`.twbx` (Tableau Desktop → *File → Export Packaged Workbook*) into one folder.

4. **Complexity triage — set expectations, and route the outliers.** The classic build has a real ceiling, so triage is also a **routing** decision. Flag these up front (detail in [`build-classic-app.md`](reference/build-classic-app.md) §Known ceilings and [`gotchas.md`](reference/gotchas.md)):
   - **Table calcs, running totals, % of total, LOD ratios, any ratio-of-aggregates** → ⚠️ a native chart **can't compute them**; they become **pre-computed SQL columns**. Cheap to handle *if* caught now, a SQL round-trip if discovered at build time.
   - **Pixel-critical / heavily-styled dashboards** → ⚠️ **the weakest fit for a classic app.** Native cells reproduce the *content and row structure*, not the chrome. Either agree to a native approximation, or migrate **that dashboard** with the sibling `tableau-migration` (generative) skill. Decide per dashboard, not for the whole batch.
   - **Maps** → Python cell (plotly), no native map.
   - **Detail/LOD text tooltips** → no clean equivalent (tooltips are aggregate-only, no `detail` channel).
   - **Web-page / iframe embeds** → no native equivalent (flag, like maps).
   - **External file/spreadsheet source** → rows aren't in the `.twb`; **ask the customer for the file**.
   - **Extract-backed datasource** (`.hyper`) → **ask which connection it's built on**.

   Put these in the brief as known gaps **with their agreed substitute** so the notebook agent doesn't silently approximate them.

# First pass — cap at 1–2 dashboards (pilot, then scale)

**Do not run the full folder first.** Migrate **one or two** dashboards end-to-end, then stop and tune.
- **Pick the pilot(s):** one *simple/representative*; if two, add one *representative-complex* (a dashboard with a table calc or a ratio tile, several parameters, or a facet surfaces gaps early). Don't make the single hardest edge case your only pilot.
- **Go all the way:** parse → brief + styling spec → gate the SQL → build the classic app → cell-spec diff → visual-QA loop → **customer's final visual confirm** vs. the Tableau original.
- **Tune, then scale:** fold fixes (connection mapping, calc translations, brief wording, format mappings, prompt phrasing that reliably yields native cells, layout grid choices, screenshot-selector tweaks) back into this playbook *before* batching the rest.

Why: the gates get the result close automatically, but a human confirm on a tiny first batch catches systematic errors before they multiply.

# Guiding the customer
- **State the priority order up front** (accuracy first, look & feel second, maintainability as the reason for this build) and that the deliverable is a **classic Hex app made of native cells**.
- **State the ceiling in the same breath:** a pixel-perfect Tableau dashboard won't come across pixel-for-pixel; you'll mirror structure and content natively, pre-compute table calcs and ratios in SQL, or route that dashboard to the generative skill. Get that agreed *before* building.
- **Name the human gates:** (1) **data connection** — you'll ask when the target is ambiguous; (2) **screenshot login** — the one-time headed Hex sign-in that powers the visual-QA loop; (3) **final visual confirm** — the gates drive the render to near-parity automatically, then the customer signs off on the pilot and each batch. (You only surface the *builder* as a question if the notebook agent is unavailable and you must hand-build.)
- **Tell them what to provide:** Tableau access (PAT) *or* exported files; which **Hex data connection** to target; and that the default build spends **Hex credits** (needs the headless-agent-threads feature).
- **Work in waves:** pilot → tune → batch a wave → QA → next wave.

---

# Porting a workbook (the core per-workbook loop)

1. **Resolve the data connection, then note its SQL dialect.** Match on metadata (type + database), not names/hosts. Fetch the published `.tdsx` if the workbook uses `sqlproxy`. Full procedure → [`connection-mapping.md`](reference/connection-mapping.md). ⚠️ **Never assume Snowflake.** (The notebook agent writes the actual dialect SQL against the schema it sees — but you still resolve *which* connection + tables so the brief is right.)

2. **Create the Hex project and inject the raw `.twb`.** The XML fits in one markdown cell (~121 KB, no chunking) — keeps the source of truth in the project:
   ```bash
   hex project create ...
   hex cell create -s "$(cat workbook.twb)"   # markdown cell holding the source XML
   ```
   Keep this `.twb` cell in the notebook but **never add it to the app layout** — it's a maintainer reference. ⚠️ **Wrap any injected reference text (the `.twb`, the brief, the styling spec) in `{% raw %}` … `{% endraw %}`** — Hex markdown cells Jinja-render `{{ }}`, and briefs are full of `{{ param }}` notation (and often a literal empty `{{ }}`), which ERRORs the whole `hex project run` even though every SQL cell is fine. See [`gotchas.md`](reference/gotchas.md).

3. **Parse the XML and understand the workbook.** The `.twb` is the **source of truth**; screenshots are QA only. Produce an intent-level plan, not finished SQL:
   - **Cluster worksheets** that share base table + join + shared filters + a compatible grain into shared **derivations** (a base df + companions for table calcs / ratios / KPIs). Strategy → [`tableau-semantics.md`](reference/tableau-semantics.md) §9.
   - ⚠️ **Sweep ALL filter scopes.** Data-source/context/workbook filters apply to every sheet; worksheet filters are per-chart. A missed shared-scope filter silently changes totals.
   - ⚠️ **Resolve field names** via encodings → internal-name → caption+formula, never by caption alone.
   - **Understand calcs/LOD/window/params** as *meaning* (LOD → per-partition aggregate; table calcs → window; params → input + scope). You describe these as intent in the brief; the notebook agent implements them. Full mapping → [`tableau-semantics.md`](reference/tableau-semantics.md).
   - **Map each tile to a native cell type, and catch what native cells can't do.** Per worksheet/zone: EXPLORE (which variant), METRIC, `pivot-table`, markdown, or Python 🐍. ⚠️ Flag every **table calc, running total, % of total, LOD ratio, or ratio-of-aggregates** — these need a **pre-computed SQL column**, not chart config — plus **maps** (Python), **detail-text tooltips**, and **iframe embeds** (gaps) *now*, while you still have the parse open → [`building-cells.md`](reference/building-cells.md), [`build-classic-app.md`](reference/build-classic-app.md) §Known ceilings.
   - **Extract the styling values now into a styling spec** (titles, cell types, encodings, per-member colors as **hex codes from the XML**, tooltip fields, number/date formats, and each tile's **row + width share** from the `<zone>` geometry). This drives the build, the cell-spec diff, and the visual-QA diff → [`build-classic-app.md`](reference/build-classic-app.md).
   - Export the original's PNGs for QA: `scripts/tableau_shots.py "<workbook name>"`.

4. **Builder — delegate by default; hand-build is the fallback.** There's no "which form" question: **build a classic app of native cells.** The only question is *who builds it*, and you only hand-build when the notebook agent isn't available (feature off / no Hex credits).

   | Builder | Presentation layer | SQL data layer | Cost | When |
   |---|---|---|---|---|
   | **Notebook agent (DEFAULT)** | agent builds native EXPLORE/METRIC/pivot cells + `appLayout` | native SQL cells — gated the same way regardless of who wrote them | Hex credits (+ your tokens if you pre-build the SQL) | **every migration**, unless the notebook agent is unavailable |
   | **Hand-build (FALLBACK)** | this coding agent clones templates → native cells + `appLayout` (YAML) | this coding agent hand-builds (YAML) | your model tokens | **only** when the notebook agent is unavailable |

   Default → [`build-classic-app.md`](reference/build-classic-app.md), using the brief/handoff mechanics in [`build-notebook-agent.md`](reference/build-notebook-agent.md), the capability map + templates in [`building-cells.md`](reference/building-cells.md), and the render gate [`visual-qa-loop.md`](reference/visual-qa-loop.md). The artifact is the same either way — only the builder changes.

   **SQL-first either way.** The app's data layer is always native, inspectable, gated SQL cells — the charts read those dataframes and never re-query. Two ways to get there: (a) **pre-build + gate the SQL yourself first** (YAML) when the population is subtle (aggressive shared filters, fan-out risk, a relative-date window) — pin the numbers before any chart is built; or (b) let the **notebook agent build the SQL cells too** and run the fidelity gate **post-hoc** on them. Default to (b); escalate to (a) for high-stakes/subtle-population workbooks. Either way the SQL is gated before the migration ships. ⚠️ **Table-calc and ratio tiles are a reason to pre-build:** the computed column has to exist in SQL before a chart can bind to it. Be honest about cost: the fallback isn't "free" — it spends the customer's frontier-model tokens and builds blind to the warehouse and the render.

5. **Build the classic app (default).** Write the **migration brief** + **styling spec** (intent, not literal SQL — the derivations and *what each represents*, plus params, the **cell type + encodings per tile**, the row-by-row layout with width shares, and the hex-code styling), inject them as project cells (⚠️ `{% raw %}`-wrapped), then hand off to the notebook agent with a **prescriptive** prompt: *"Build this as a CLASSIC HEX APP using native notebook cells — SQL, input parameters, and native chart cells (EXPLORE/METRIC/pivot) arranged in the App builder layout. Do NOT build a Generative app."* Name the dataframes the charts must read, tell it to **consolidate** (not one query per worksheet), that **table calcs and ratios are SQL columns**, and to keep the `.twb`/reference/SQL cells **out** of the layout. `hex thread create --json` → **give the customer the live URL immediately** so they can watch/intervene. Verify `genAppFiles` is **empty** and `appLayout` is populated. Full procedure + prompt template → [`build-classic-app.md`](reference/build-classic-app.md); brief/handoff mechanics → [`build-notebook-agent.md`](reference/build-notebook-agent.md).
   - **Fallback only (notebook agent unavailable):** clone-and-override native cells from `templates/` and assemble the `appLayout` yourself → [`building-cells.md`](reference/building-cells.md).

6. **SQL-fidelity gate (mandatory — the accuracy guarantee).** The gate reviews the SQL *whoever wrote it*. Read every SQL cell's values (`hex cell run --with-output`) and export its source; write a **translation ledger**, **independently re-derive** the intended SQL from the `.twb` and **diff** it (spawn a subagent where supported), run the **mistake-class checklist** (filter scope, relative-date off-by-one, `COUNT` vs `COUNTD`, fan-out join, caption-not-formula, LOD grain), and **prove** suspect filters/joins with differential probes. It runs on the native SQL cells under the app — **post-hoc** when the agent built the SQL, or *before* the build when you pre-built it. Any divergence → fix (agent-built SQL: `hex thread continue` naming the divergence, or edit the cell; pre-built/hand-built: edit the SQL) and re-check. Full procedure → [`sql-review.md`](reference/sql-review.md).

   > **The classic build gives the gate extra surface:** the pre-computed table-calc / ratio columns are ordinary SQL you can read and re-derive, instead of logic buried in app code. Gate those columns as carefully as the base population — they're what the chart actually plots.

7. **Cell-spec diff gate (classic-only — do it before screenshotting).** `hex project export` and check each viz cell's spec against the styling spec: `cellType` / `visualizationType`, `config.dataframe`, every encoding in `spec.fields[]` (channel, column, aggregation, `truncUnit`), **`dataType: DATE` on date axes** (not a numeric look-alike like `CLOSED_MONTH`), `displayFormat`, the **hex codes** in `colorMappings`/`chartConfig.series[]`, the **`seriesId == series.id == seriesGroups id`** linkage (a mismatch renders blank while the cell still reports COMPLETED), and the `appLayout` (every viz cell present, no `.twb`/reference/SQL cells, **no fixed `height` on chart EXPLOREs**). This is fidelity checking the generative build simply couldn't do — most look-&-feel bugs are catchable here without rendering anything. → [`build-classic-app.md`](reference/build-classic-app.md) §Verify accuracy + fidelity.

8. **Run and QA the render.** `hex project run` (async — poll `run status`). Confirm what it built via `hex project export`: **`genAppFiles` empty** (it's classic, not generative — re-prompt if non-empty), native viz cells present, SQL cells present + unchanged, params wired **upstream** of their consumers, `appLayout` populated. Then:
   - **Visual-QA loop:** headless Playwright screenshot (persistent profile) → panel-by-panel diff vs. the source PNG → surgical `hex thread continue` fix batch (or a YAML `appLayout` edit) → repeat until parity, then a final human confirm. ⚠️ **COMPLETED ≠ renders correctly** — a broken viz spec passes the run oracle, so the render gate is not optional → [`visual-qa-loop.md`](reference/visual-qa-loop.md).
   - **Layout fixes** are often faster as a direct export → edit `appLayout` → import round-trip than as a prompt → [`gotchas.md`](reference/gotchas.md) §App layout.

9. **Author a Hex guide for the data source (once per data source).** Ship a semantic layer, not just charts: mirror the Tableau data source as a retrieved Hex guide (canonical metrics + join patterns + migration risk areas) so the team can self-serve in Threads / the notebook agent. Built from the parse, reused across dashboards on that data source, published via `hex guide preview`/`publish`. Template → [`datasource-guide.md`](reference/datasource-guide.md).

---

# Batch migration (folder loop)

Point at a folder of `.twb` files and migrate them as a set. Three phases:

**Phase 1 — parallel, read-only (safe to fan out):** scan → parse each workbook (worksheets, marks, calcs, filters at all scopes, datasource, zone geometry) → resolve each connection → **cluster into shared derivations** → **map each tile to a native cell type and record the native-cell gaps** (table calcs/ratios needing SQL columns, maps, detail tooltips, embeds) → produce a per-workbook **plan + draft brief + styling spec**. **Batch every ambiguous-connection question into ONE ask**, and **ask once for the batch** about any dashboard whose pixel-critical styling should be routed to the generative skill instead (step 0.4) — don't stop per workbook.

**Phase 2 — sequential, mutating (one workbook at a time):** run the *Porting a workbook* loop for each — brief → build → **SQL-fidelity gate** → **cell-spec diff** → record both gate results in the manifest. **Write status to the manifest after each** so the batch is resumable and fail-soft. **Author each data source's guide once.**

**Phase 3 — verify (one batch):** collect all project links + original PNGs and present them for human visual QA in one pass.

### Manifest (`migrations.json`) — the resumable backbone
```json
[
  {
    "twb_file": "marketing_funnel.twb",
    "title": "Marketing Funnel",
    "hex_project_id": null,
    "connection_id": "019a59ac-8c0f-...",
    "builder": "agent",                 // agent (default) | handbuilt (notebook agent unavailable)
    "sql_source": "agent",              // agent (built + gated post-hoc) | prebuilt (gated first)
    "thread_id": null,                  // notebook-agent thread
    "status": "pending",                // pending → parsed → briefed → built → gated → spec-diffed → run → verified | failed
    "worksheets": 4,
    "derivations": 2,                   // shared df + companions (incl. pre-computed table calcs/ratios)
    "viz_cells": 6,                     // native EXPLORE/METRIC/pivot cells
    "precomputed_columns": [],          // e.g. ["running_arr (table calc)", "margin_pct (ratio)"]
    "native_gaps": [],                  // e.g. ["map → python cell", "detail tooltip dropped"]
    "gate": "",                         // e.g. "12 rows, KPIs tie; no divergence"
    "spec_diff": "",                    // e.g. "clean" | "2 color fixes, 1 date-axis fix"
    "notes": ""                         // e.g. "ambiguous connection: asked", "pixel-critical: native approximation agreed"
  }
]
```
On rerun, skip any workbook whose `status` is `verified`. Record `failed` + the error in `notes` and continue.

---

# Files in this skill
- `SKILL.md` — this playbook (workflow spine).
- `reference/` — `connection-mapping.md`, `tableau-semantics.md` (understand the workbook), `build-classic-app.md` (**the default build** — native cells + app layout), `building-cells.md` (**native-cell capability map** + hand-build fallback), `build-notebook-agent.md` (brief + handoff mechanics), `visual-qa-loop.md` (render gate), `sql-review.md` (fidelity gate), `datasource-guide.md`, `gotchas.md`.
- `templates/` — clone-and-override native-cell configs (METRIC + EXPLORE variants, `_filter_snippet.json`). The **target format of this build** — a reference for the delegated build and the source material for the hand-build fallback.
- `tableau-zoo/` — regression fixtures (`.twb` inputs + parity ground truth + Hex goldens).
- `scripts/tableau_fetch.py` — fetch `.twb`/`.twbx` from Tableau Cloud/Server (`--list` / `--name` / `--project`).
- `scripts/tableau_shots.py` — export PNGs of a workbook's dashboard + worksheets for the visual-QA gate.
- `scripts/hex_shots.py` — headless Playwright screenshot of the built Hex app (persistent profile, one-time login) for the visual-QA loop.
- `credentials/tableau.env.example` — template for Tableau PAT + pod + site. Copy to `tableau.env` (gitignored).
- `tableau_exports/`, `working/` — local downloads + scratch (gitignored).

## Sibling skill
**`tableau-migration`** is the same playbook delivering a **generative app** (a bespoke
code app — `genAppFiles`) instead of native cells. Prefer it for a dashboard where
**pixel fidelity outranks maintainability**, or one leaning on constructs native cells
can't express in-chart. Prefer *this* skill when the customer wants a native Hex dashboard
their analysts can edit. The Tableau-side parsing, the brief, and the SQL gate are
identical.

**Getting it:** where the two ship as separate plugins, install it alongside this one; in
a combined migrations plugin the two ship together and resolve as
`<plugin>:tableau-migration`. If neither is installed, the routing advice above still
applies — you just can't hand a dashboard off to it.

## Hex CLI cheat-sheet (verified against `hex 1.2026.07.21`)
- **Notebook agent (default builder):** `hex thread create "<prompt>" --project <id> --json` → `url` (**hand to the customer to watch/intervene**) + `thread_id`; poll `hex thread get <id>` (`RUNNING`→`IDLE`); iterate `hex thread continue <id> "<prompt>"`. Uses Hex credits; needs the headless-agent-threads feature.
- **Classic app (the form we want):** no CLI flag controls form — the prompt does. Be **prescriptive about cell types** and say *"do NOT build a Generative app."* Verify with `hex project export <id>` → `genAppFiles` **empty/absent**, native `cellType`s present, `appLayout.tabs[].rows[]` populated; re-prompt if it built generative.
- **Hex app screenshot (visual-QA gate):** one-time `python scripts/hex_shots.py --login` (headed; customer signs in), then `python scripts/hex_shots.py "<url>" -o working/shots/migrated.png` (headless). Needs `pip install playwright && playwright install chromium`.
- **Cells:** `hex cell create` makes only code/sql/markdown; **native viz cells (EXPLORE/METRIC/pivot), INPUT (parameter) cells, and connection-less dataframe-SQL companions are authored in YAML** — plan on a YAML round-trip on the hand-build path and for surgical fixes. ⚠️ Injected markdown reference cells (the `.twb`, brief, spec) must be `{% raw %}`-wrapped or their `{{ }}` tokens ERROR the run. `hex cell run <id> --with-output` returns result rows; after a YAML import use the **API id from `hex cell list`**, not the export `cellId`.
- **App layout:** `hex project export <id> -o f.yaml` → edit `appLayout` → `hex project import f.yaml`. Never put the `.twb`/reference/raw-SQL cells in the layout; never set a fixed `height` on a chart-type EXPLORE element. → [`gotchas.md`](reference/gotchas.md).
- **Guides (headless):** `hex guide preview <*.md>` → `preview_id`; `hex guide publish <preview_id>`. Markdown only.
