---
name: omni-migration
description: >-
  Migrate Omni Analytics (omni.co) dashboards into Hex, as either a CLASSIC app
  (native SQL, input, and EXPLORE/METRIC/pivot cells in an app layout) or a
  GENERATIVE app, by delegating the build to Hex's in-product notebook agent. Use
  when someone wants to convert, port, rebuild, or migrate Omni content (dashboards,
  workbooks, tiles, topics, the Omni semantic model) into Hex. This coding agent pulls
  each dashboard via the Omni API — tile queries, every model layer's YAML, and Omni's
  own generated SQL and results per tile — compiles the semantic queries into the SQL
  they mean, and writes a migration brief; Hex's notebook agent builds the chosen app
  form over gated SQL cells; this agent verifies with a SQL-fidelity gate anchored on
  result parity against Omni, a cell-spec diff (classic), and a visual-QA loop.
  Triggers: "migrate Omni to Hex", "port my Omni dashboards", "convert an Omni
  dashboard", "Omni → Hex", "Omni to Hex classic app / generative app".
---

# Omni → Hex Migration (classic or generative app)

A CLI-driven migration where this coding agent understands the Omni source and verifies
the result, and Hex's in-product notebook agent builds the dashboard. You fetch a
dashboard via the Omni API, read its **tile queries, model YAML (every layer), filters,
vis config, and layout** as the source of truth, capture **Omni's own generated SQL and
result rows** per tile, translate the Omni-specific semantics, and write a migration
brief into the Hex project. The notebook agent builds the dashboard on a natively-gated
SQL data layer, in **one of two forms you choose per dashboard**:

| | **Classic app** (path A) | **Generative app** (path B) |
|---|---|---|
| **What it is** | native cells — SQL, inputs, EXPLORE/METRIC/pivot charts — in an `appLayout` | a code app (`genAppFiles`) reading the gated SQL dataframes |
| **Best for** | the typical Omni tile grid; dashboards analysts will maintain | markdown/HTML-heavy dashboards, custom Vega-Lite, branded/embedded looks, data stories |
| **Editable by analysts** | ✅ every chart is a cell | ⚠️ it's code |
| **Look-&-feel verification** | cell-spec diff **+** render diff | render diff only |
| **Ceiling** | what native cells express (ratios + calcs in SQL; maps/custom vis → Python) | arbitrary — it's code |
| **Build doc** | [`build-classic-app.md`](reference/build-classic-app.md) | [`build-generative-app.md`](reference/build-generative-app.md) |

Both paths share everything else: the Omni parse, the brief, the SQL-fidelity gate, the
visual-QA loop, and the guide.

## What's different about Omni (read once)

**Omni is semantic-layer-first: a tile has no SQL — it has a query against a model.**
The Hex SQL is a *compilation* of the tile's fields + the model's views, topics, and
relationships, and the compile is where migrations go wrong (dropped topic filters,
fan-out across one-to-many joins, dashboard-local fields). But Omni also gives you the
best verification anchors of any BI tool: **its own generated SQL** (`query/run` with
`planOnly`) and **its own results** for every tile. Lean on both. Detail →
[`omni-semantics.md`](reference/omni-semantics.md).

## Why delegate the build to the notebook agent

This coding agent can't see the live warehouse schema or data, the workspace context, or
the rendered result. The notebook agent sees all three, so it builds; delegation spends
Hex credits.

> **Division of labor:** this coding agent owns **understanding the Omni dashboard** (the
> durable IP: resolving fields across model layers, compiling the semantic queries,
> mapping filters/controls with per-tile scope, translating calculations, reading the
> layout) and **verifying the result** (the fidelity gate). The notebook agent owns
> **building it in Hex**. Accuracy is guaranteed by the gate — which reviews whoever wrote
> the SQL — not by this agent hand-writing every query.

**Priority order (say this to the customer up front):** (1) **accuracy** of numbers and
visuals, (2) **similar look & feel**, (3) **maintainability** — which is what the
classic/generative choice trades against #2. Name the features with no clean Hex
equivalent early (AI summary tiles, access filters, uploaded data, bespoke markdown
CSS on the classic path) so "it isn't identical" is never a surprise. Philosophy:
**cover the basis, don't gold-plate.**

## Reference docs (read on demand)
- [`reference/connection-mapping.md`](reference/connection-mapping.md) — resolve the Omni connection → Hex data connection; decide same-warehouse-or-not (which decides whether result parity ties exactly).
- [`reference/omni-semantics.md`](reference/omni-semantics.md) — **understand the dashboard:** model layers, views/measures/topics/relationships, tile query JSON + filter objects → SQL, controls → Hex inputs, calculations → window functions, vis config + layout → Hex, consolidation, access filters. What you distill into the brief.
- [`reference/build-notebook-agent.md`](reference/build-notebook-agent.md) — **brief + handoff mechanics, both paths:** what the brief must contain, agent-built vs. pre-built SQL, `{% raw %}` wrapping, the thread, the live URL.
- [`reference/build-classic-app.md`](reference/build-classic-app.md) — **path A:** known ceilings, styling spec, prescriptive prompt, "is it classic?" check, the **cell-spec diff gate**.
- [`reference/build-generative-app.md`](reference/build-generative-app.md) — **path B:** when it's the right call, styling spec, the prompt, "is it generative?" check.
- [`reference/building-cells.md`](reference/building-cells.md) — the **native-cell capability map** (read on every classic build) + the hand-build fallback with `templates/`.
- [`reference/sql-review.md`](reference/sql-review.md) — **SQL-fidelity gate:** ledger → independent re-derivation & 3-way diff against Omni's SQL → mistake-class checklist → **result parity vs. Omni** → probes.
- [`reference/visual-qa-loop.md`](reference/visual-qa-loop.md) — **render gate, both paths:** Omni's PNG download (or a headless capture) vs. a headless Hex screenshot → tile-by-tile diff → fix batch → repeat.
- [`reference/datasource-guide.md`](reference/datasource-guide.md) — carry the Omni semantic model into Hex as a guide per topic (optionally a semantic model).
- [`reference/gotchas.md`](reference/gotchas.md) — Omni parsing landmines, Hex CLI quirks, app layout.

## What you need before starting
- **Omni access** — an **Organization API key** (recommended: the dashboard export needs it, and it sees all content) or a Personal Access Token (no export; sees only that user's content). Into `credentials/omni.env` from `credentials/omni.env.example` (gitignored).
- **Hex CLI** installed and authed; the **target Hex data connection**; and the **headless-agent-threads feature** enabled (the build uses `hex thread`).
- **Visual-QA render gate:** `pip install playwright && playwright install chromium`, plus a **one-time headed login** for Hex (`scripts/hex_shots.py --login`). Omni's reference image normally comes from its PNG download API — no Omni browser login needed unless that fails.
- **Optional:** `pip install pyarrow` (decodes Omni's Arrow payloads for long-running tile queries); the RedHat YAML VS Code extension for YAML round-trips.

## Workflow at a glance
0. **Prioritize & organize** the customer's dashboards → one folder; **recommend a build path per dashboard** and get it confirmed.
1. **Pilot 1–2 dashboards** end-to-end (ideally one per build path if both are in play), QA, tune.
2. **Port each dashboard:** resolve connection → fetch + parse (queries, model layers, Omni's SQL + results) → brief → build the **chosen app form** over gated SQL → **SQL-fidelity gate** (with result parity) + **cell-spec diff** (classic) + **visual-QA loop** → ship the guide.
3. **Batch the rest** with the folder loop + manifest.

---

# Step 0 — Prioritize, organize, and choose build paths (do this FIRST)

Migration is the best moment a team gets to prune. **Do not migrate what nobody uses.**

1. **Take inventory.** `python scripts/omni_fetch.py --list` lists every dashboard,
   **most-viewed first** (`_count.views` from `GET /v1/documents`), with folder, owner,
   and last update, and writes `omni_exports/inventory.json`. For richer usage (viewers
   over time, last viewed), an Omni admin can pull the **Analytics** app's Content
   dashboards (admin-only; not exposed via API). Per dashboard capture: name, owner,
   folder, views, last updated, and a one-line "what decision does this drive?"

2. **Prioritize on three axes**, then bucket:

   | Axis | Migrate-first | Drop / defer |
   |------|---------------|--------------|
   | **Usage** | viewed regularly, real audience | ~0 views recently |
   | **Business value** | drives a recurring decision | ad-hoc / one-time |
   | **Freshness / ownership** | maintained, clear owner | stale, orphaned, personal scratch |

   **Get the customer to confirm the buckets**: **Migrate**, **Archive/rebuild-later**,
   **Drop**. Collapse near-duplicates into one canonical dashboard.

3. **Organize into ONE folder:** `python scripts/omni_fetch.py --folder "<path>"` (or
   `--dashboard <id> …`) downloads each dashboard into `omni_exports/<dashboard>/` —
   tile queries, v2 document, export, every model layer's YAML, connections, and **Omni's
   generated SQL per tile**. Add `--results --png` to capture the parity baseline and the
   reference image in the same pass.

4. **Complexity triage + build-path recommendation (per dashboard).** Read each
   dashboard's tiles and recommend a path:

   | Signal in the dashboard | Recommend |
   |---|---|
   | Standard charts, tables, KPIs in a grid; the team wants to edit it | **Classic** (default) |
   | Several markdown tiles with Mustache values, custom HTML/CSS, or a narrative layout | **Generative** |
   | Custom Vega-Lite (`code` vis), heatmaps/sankeys/funnels as the centerpiece | **Generative** (classic → Python cells) |
   | Embedded/branded dashboard where pixel look matters more than editability | **Generative** |
   | Heavy Excel-style calculations | Either — they become SQL regardless |

   **When unsure, recommend classic** — it's the more maintainable artifact and the
   better-verified one (cell-spec diff). **Present the recommendation for the whole wave
   in one ask** and let the customer override per dashboard; it's their call, and a
   mixed workspace legitimately splits across both paths. Record it as `build_path` in
   the manifest.

   Also flag known gaps up front (detail in [`omni-semantics.md`](reference/omni-semantics.md)
   §5, §7 and [`gotchas.md`](reference/gotchas.md)): **AI summary tiles** (no SQL
   equivalent), **access filters / user attributes** (RLS decision needed), **spreadsheet
   tiles and file uploads** (ask for the source), **dashboard-local workbook fields**,
   **tiles silently capped at 1000 rows**, **raw-SQL tiles** (`userEditedSQL`), and
   **broken tiles** (the plan reports `missing_fields`/`invalid_calculations` — broken in
   Omni too). Put each in the brief with its agreed substitute.

# First pass — cap at 1–2 dashboards (pilot, then scale)

**Do not run the full folder first.** Migrate one or two dashboards end-to-end, then stop
and tune.
- **Pick the pilot(s):** one simple/representative dashboard; if the wave uses both paths,
  pilot one of each. A dashboard on a topic with a one-to-many join surfaces fan-out
  issues early.
- **Go all the way:** fetch → brief + styling spec → gate the SQL (with result parity) →
  build → spec diff (classic) → visual-QA loop → **customer's final visual confirm**.
- **Tune, then scale:** fold fixes (connection mapping, filter translations, timezone
  handling, brief wording, prompt phrasing that reliably yields the right form, layout
  mapping) back into this playbook *before* batching.

# Guiding the customer
- **State the priority order up front** and **the build path per dashboard** with the
  trade-off in one sentence (classic = editable + mechanically verified; generative =
  closer look, it's code).
- **Name the human gates:** (1) **data connection** — asked when ambiguous, plus
  same-warehouse-or-not; (2) **build path** — confirmed in Step 0; (3) **access filters**
  — a decision, never a silent drop; (4) **Hex screenshot login** — one-time; (5) **final
  visual confirm** per pilot and batch.
- **Tell them what to provide:** an Omni Organization API key (or PAT, with its limits);
  which Hex data connection to target; that the build spends **Hex credits**.
- **Work in waves:** pilot → tune → batch a wave → QA → next wave.

---

# Porting a dashboard (the core per-dashboard loop)

1. **Resolve the data connection and note same-warehouse-or-not.** Chain: tile `modelId`
   → model → Omni connection (dialect, database, schema) → match a Hex connection on
   type + database, not host. Ask when zero or several match. Same warehouse ⇒ Omni's
   generated SQL runs as-is and result parity should tie exactly. ⚠️ **Never assume
   Snowflake.** → [`connection-mapping.md`](reference/connection-mapping.md).

2. **Create the Hex project and inject the source references.** Keep the source of truth
   in the project — never in the app:
   ```bash
   hex project create ...
   hex cell create -t markdown -l "Omni tile queries" -s "{% raw %}$(cat omni_exports/<dash>/queries.json){% endraw %}"
   hex cell create -t markdown -l "Omni SQL: <tile>"  -s "{% raw %}$(cat omni_exports/<dash>/sql/<tile>.sql){% endraw %}"
   ```
   ⚠️ **Wrap every injected reference in `{% raw %}` … `{% endraw %}`** — markdown tiles
   are Mustache `{{ }}`, and the brief quotes Hex Jinja; an unwrapped cell ERRORs the
   whole run. Keep reference cells **out of the app layout**. → [`gotchas.md`](reference/gotchas.md).

3. **Read the dashboard and understand it.** The fetched files are the source of truth;
   the PNG is QA only. Produce an intent-level plan, not finished SQL:
   - **Inventory the tiles** from the layout (`containers`, or the export for classic
     layouts) — `queries.json` can include queries that aren't on the dashboard. Classify
     each tile by type → [`omni-semantics.md`](reference/omni-semantics.md) §5.
   - **Resolve every field across model layers** (query → workbook → shared), resolving
     `${}` references to columns, timeframes to truncations, and measures to aggregates
     (incl. filtered and distinct-on measures). → §1.
   - **Compile each tile's query**: topic + join path, topic `always_where` filters,
     tile filters (filter objects → SQL), sorts, limit, pivots, totals — and **read
     Omni's generated SQL** for the tile to confirm the joins and fan-out handling. → §2.
   - **Map dashboard filters and controls** to Hex inputs, **with per-tile scope** from
     each control's `map` (excluded tiles, retargeted fields), metric/timeframe
     switchers, defaults. → §3.
   - **Translate calculations** to window functions over the tile's result. → §4.
   - **Cluster tiles into shared SQL cells** — same topic, population, and join path;
     separate cells for fan-out-sensitive measures, top-N, and calc-dependent tiles. → §6.
   - **Flag security**: access filters, user-attribute filters, access grants. → §7.
   - **Extract the styling spec** (titles, chart types, encodings, hex colors via
     `colorPalettes`, formats, markdown content, grid position) → the build-path doc.
   - **Reference image:** `omni_exports/<dash>/dashboard.png` (from `--png`), or
     `python scripts/omni_shots.py "<dashboard url>"` if the download failed.

4. **Confirm the build path** recorded in Step 0 (classic or generative) — and the
   builder: **the notebook agent by default**; this coding agent hand-builds **only** when
   the notebook agent is unavailable (headless-agent-threads off / no Hex credits), which
   in practice means the classic form from `templates/` →
   [`building-cells.md`](reference/building-cells.md).

   **SQL-first on both paths.** The presentation always reads native, inspectable, gated
   SQL cells and never re-queries. Either (a) **pre-build + gate the SQL yourself** — the
   default when a topic crosses a one-to-many join, uses filtered/custom/distinct-on
   measures, dashboard-local fields, or calculations; cheap here because Omni's generated
   SQL is already in hand (parameterize its filter literals, validate, tie to results) —
   or (b) let the **notebook agent build the SQL** from the brief and gate it **post-hoc**.

5. **Build.** Write the **migration brief** + **styling spec**, inject them
   (`{% raw %}`-wrapped), and hand off with the path's prompt — app form is set by
   **prompt wording alone**:
   - **Classic:** *"Build this as a CLASSIC HEX APP using native notebook cells … Do NOT
     build a Generative app."* → [`build-classic-app.md`](reference/build-classic-app.md)
   - **Generative:** opens with *"Build this as a GENERATIVE APP (App builder →
     Generative app), not a classic notebook app."* →
     [`build-generative-app.md`](reference/build-generative-app.md)

   `hex thread create --json` → **give the customer the live URL immediately**. Then
   `hex project export` and **verify the form**: `genAppFiles` empty (classic) or
   non-empty (generative); re-prompt if wrong. Brief contents + handoff →
   [`build-notebook-agent.md`](reference/build-notebook-agent.md).

6. **SQL-fidelity gate (mandatory — the accuracy guarantee).** For every SQL cluster:
   translation ledger → **independent re-derivation** (subagent) → **3-way diff** against
   the built SQL and Omni's generated SQL → mistake-class checklist (dropped topic filter,
   fan-out, workbook-local field, filter scope, relative-date window + timezone, limit,
   calculations, count vs. count-distinct, quoting trap) → **result parity**: Hex rows vs.
   Omni rows for the same tile, at default filters and one non-default value per filter →
   probes. Any divergence → fix (`hex thread continue` naming it, or edit the cell) and
   re-check. → [`sql-review.md`](reference/sql-review.md).

7. **Cell-spec diff (classic path only — before screenshotting).** Assert each viz cell's
   type, dataframe, encodings, DATE axes, formats, hex colors, `seriesId` linkage, and the
   `appLayout` against the styling spec. → [`build-classic-app.md`](reference/build-classic-app.md).

8. **Run and QA the render.** `hex project run` (async — poll `run status`). Then the
   **visual-QA loop**: Omni PNG vs. headless Hex screenshot → tile-by-tile diff (layout,
   numbers, filter behavior, colors, titles, formats) → one numbered `hex thread continue`
   fix batch per round → repeat until clean → final human confirm.
   ⚠️ **COMPLETED ≠ renders correctly.** → [`visual-qa-loop.md`](reference/visual-qa-loop.md).

9. **Carry the semantic model across (once per topic).** Author a Hex guide per Omni topic
   the migrated dashboards use — canonical measures with compiled SQL, join patterns and
   fan-out rules, always-on filters, risk areas — and publish via `hex guide
   preview`/`publish`. Optionally port must-be-exact measures into a Hex semantic model.
   → [`datasource-guide.md`](reference/datasource-guide.md).

---

# Batch migration (folder loop)

**Phase 1 — parallel, read-only (safe to fan out):** fetch each dashboard (mind Omni's
60 requests/minute limit — run the fetches sequentially, parse in parallel) → parse tiles,
model layers, filters, calcs → resolve each connection → cluster tiles into SQL cells →
**recommend a build path** → draft brief + styling spec. **Batch every ambiguous-connection
question, every build-path confirmation, and every access-filter decision into ONE ask.**

**Phase 2 — sequential, mutating (one dashboard at a time):** brief → build → SQL gate
(with parity) → spec diff (classic) → record results in the manifest. **Write status after
each** so the batch is resumable. **Author each topic's guide once.**

**Phase 3 — verify (one batch):** collect all project links + Omni PNGs for human visual
QA in one pass.

### Manifest (`migrations.json`) — the resumable backbone
```json
[
  {
    "omni_identifier": "ab12cd34",
    "title": "Revenue Overview",
    "folder": "Sales/Exec",
    "views": 412,
    "hex_project_id": null,
    "connection_id": "019a59ac-8c0f-...",
    "same_warehouse": true,             // true → Omni SQL runs as-is, parity ties exactly
    "build_path": "classic",            // classic | generative (confirmed with customer in Step 0)
    "builder": "agent",                 // agent (default) | handbuilt (notebook agent unavailable)
    "sql_source": "prebuilt",           // prebuilt (gated first) | agent (gated post-hoc)
    "thread_id": null,
    "status": "pending",                // pending → fetched → parsed → briefed → built → gated → spec-diffed → run → verified | failed
    "tiles": 9,
    "sql_cells": 3,                     // shared SQL cells after clustering
    "topics": ["order_items"],
    "layout": "v2",                     // v2 | classic (v2 GET returned 422)
    "gaps": [],                         // e.g. ["AI summary tile → static text", "access filter on region → warehouse RLS"]
    "gate": "",                         // e.g. "3 clusters, no divergence"
    "parity": "",                       // e.g. "9/9 tiles tie at defaults; region filter ties"
    "spec_diff": "",                    // classic only: "clean" | "2 color fixes"
    "notes": ""
  }
]
```
On rerun, skip any dashboard whose `status` is `verified`. Record `failed` + the error in
`notes` and continue.

---

# Files in this skill
- `SKILL.md` — this playbook (workflow spine).
- `HOW-IT-WORKS.md` — the human-facing explainer: architecture, both paths, the gates.
- `reference/` — `connection-mapping.md`, `omni-semantics.md`, `build-notebook-agent.md`, `build-classic-app.md` (path A), `build-generative-app.md` (path B), `building-cells.md`, `sql-review.md`, `visual-qa-loop.md`, `datasource-guide.md`, `gotchas.md`.
- `templates/` — clone-and-override native-cell configs (METRIC + EXPLORE variants, `_filter_snippet.json`) — the classic path's target format and the hand-build source. *(Shared with the Mode and Tableau skills — Hex-side, source-agnostic.)*
- `scripts/omni_fetch.py` — list dashboards (by views) and fetch each one's tile queries, v2 document, export, model YAML (all layers), connections, Omni's generated SQL per tile, and optionally result rows (`--results`) and the rendered PNG (`--png`).
- `scripts/omni_shots.py` — headless Playwright screenshot of an Omni dashboard (persistent profile, one-time login) when the PNG download fails.
- `scripts/hex_shots.py` — headless Playwright screenshot of the built Hex app.
- `credentials/omni.env.example` — template for the Omni instance URL + API key. Copy to `omni.env` (gitignored).
- `omni_exports/`, `working/` — local downloads + scratch (gitignored).

## Omni API cheat-sheet (verified against the public OpenAPI spec)
- **Auth:** `Authorization: Bearer <key>`, base `https://<instance>.omniapp.co/api`. Org key for export; 60 req/min.
- **List:** `GET /v1/documents?include=_count,labels&sortField=visits` → `records[].identifier` (use it, not `id`).
- **Tiles:** `GET /v1/documents/{identifier}/queries` (runnable queries with `modelId`); `GET /v2/documents/{identifier}` (tiles, `visConfig`, `controls`, `containers`; 422 on classic layouts).
- **Export:** `GET /unstable/documents/{identifier}/export` → `dashboard`, `workbookModel`, `queryModels`, `colorPalettes`, `fileUploads` (beta).
- **Model YAML:** `GET /v1/models/{id}/yaml?mode=combined|extension` → `files{}`.
- **Generated SQL:** `POST /v1/query/run {query, planOnly: true, cache: "SkipCache"}` → `summary.display_sql` (or `summary.sql`).
- **Results:** `POST /v1/query/run {query, resultType: "json"}` → rows; 408 → `GET /v1/query/wait?jobIds=…`.
- **PNG:** `POST /v1/dashboards/{id}/download {format: "png"}` → poll `…/download/{job}/status` → `GET …/download/{job}`.
- **CLI (optional):** `brew tap exploreomni/tap && brew install omni`; `omni documents get-queries <id>`, `omni models yaml-get <id>`, `omni query run --body @q.json -o json`.

## Hex CLI cheat-sheet (verified against `hex 1.2026.07.21`)
- **Notebook agent:** `hex thread create "<prompt>" --project <id> --json` → `url` (**hand to the customer**) + `thread_id`; poll `hex thread get <id>` (`RUNNING`→`IDLE`); iterate `hex thread continue <id> "<prompt>"`. Uses Hex credits; needs headless-agent-threads.
- **App form:** no CLI flag — the prompt decides. Verify with `hex project export <id>`: classic → `genAppFiles` empty + native `cellType`s + `appLayout` populated; generative → `genAppFiles` non-empty. Re-prompt if wrong.
- **Screenshots:** one-time `python scripts/hex_shots.py --login`, then `python scripts/hex_shots.py "<url>" -o working/shots/migrated.png`. Omni reference: `omni_fetch.py --png` (or `omni_shots.py`).
- **Cells:** `hex cell create` makes only code/sql/markdown; native viz cells, INPUT cells, and dataframe-SQL companions are authored in YAML. `hex cell run <id> --with-output` returns rows (after a YAML import use the API id from `hex cell list`). ⚠️ `{% raw %}`-wrap injected reference cells.
- **App layout (classic):** `hex project export <id> -o f.yaml` → edit `appLayout` (Omni 24-col grid ×5 → 0–120) → `hex project import f.yaml`. No reference/raw-SQL cells in the layout; no fixed `height` on chart EXPLOREs.
- **Guides:** `hex guide preview <*.md>` → `preview_id`; `hex guide publish <preview_id>`.
