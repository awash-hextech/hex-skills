# Build path A — a Hex classic app (native cells + app layout)

One of the skill's two build paths (chosen per dashboard in SKILL.md step 4). The
deliverable is a **classic Hex app**: native notebook cells — SQL, INPUT parameters,
EXPLORE charts, METRIC tiles, pivot/table, markdown, Python — arranged in an
**`appLayout`**. The build is **delegated to Hex's notebook agent**; this coding agent
writes the brief and verifies the result.

> **Why classic fits Omni well.** An Omni dashboard is already a **grid of discrete
> tiles**, each one a semantic query + a chart. That maps almost 1:1 onto native Hex
> cells in an app layout, and the result is a dashboard the customer's analysts can
> open, click, and edit with no code. It is also **mechanically diff-able**: the
> exported YAML carries chart type, encodings, colors and formats, so fidelity is
> checked against the styling spec, not only by eye. Choose this path by default unless
> the dashboard leans on bespoke presentation (see **Known ceilings**).

## The core principle: split the layers

1. **Data layer — native + gated (the accuracy guarantee).** SQL cells that reproduce
   the compiled Omni queries (agent-built + gated post-hoc, or pre-built + gated first),
   run through the full **SQL-fidelity gate** ([`sql-review.md`](sql-review.md)).
2. **Presentation layer — native viz cells over those dataframes.** EXPLORE/METRIC/pivot
   cells bind to the SQL cells' output dataframes and **aggregate and filter over them**,
   so one SQL cell feeds many tiles — no per-tile re-query.

Native viz cells can't author SQL, so data logic can't leak into the presentation. Watch
the **opposite** failure: the agent writing a separate pre-aggregated SQL cell per tile.
Omni encourages that shape (every tile is its own query), so say *consolidate* —
tiles on the same topic with compatible filters share one SQL cell at the finest grain
they need ([`omni-semantics.md`](omni-semantics.md) §Consolidate).

---

## Known ceilings — name these BEFORE the build

| Omni feature | Classic-app outcome |
|---|---|
| **Markdown tiles with Mustache templating** (`{{ }}` over query results, custom HTML/CSS) | ⚠️ Static text → markdown cell. Values interpolated from a query → a markdown cell using Hex Jinja over a 1-row dataframe, or a METRIC tile. Custom HTML/CSS styling does **not** come across. If the dashboard is mostly bespoke markdown/HTML, use the **generative path**. |
| **Custom Vega-Lite vis** | Standard shapes → EXPLORE. Anything else → **Python cell** (Altair can render the Vega-Lite spec almost as-is) or the generative path. |
| **Ratio-of-aggregates measures** (margin %, conversion rate) | EXPLORE/METRIC aggregate **one column with one built-in aggregation**. **Pre-compute the ratio in SQL** at the tile's grain (or use a Hex semantic-model measure). |
| **Single-value / KPI tile** | METRIC cell — it **displays**, it doesn't aggregate. Feed it a **1-row SQL**; comparisons via `showComparison`/`comparisonColumn`. |
| **Excel-style calculations** (formulas over the result grid: running totals, % of total, `OFFSET`, lookups) | Reproduce in **SQL** (window functions) in the tile's SQL cell, or a Python cell. Never leave them for the chart to compute. |
| **Row/column totals on a pivot** | `pivot-table` totals where it supports the aggregation; otherwise a companion SQL cell. |
| **Maps** | No native map cell → **Python** `plotly.express` (🐍). |
| **Exact fonts / spacing / theme** | Hex defaults. Mirror the *structure* (rows + column spans), not the pixels. |

Everything else — chart types, per-series colors, number/date formats, data labels,
faceting, filters, the grid layout — maps well and is expected at parity. The full
native-cell capability map is [`building-cells.md`](building-cells.md) — read it on every
classic build.

---

## The styling spec (drives the prompt AND both diff baselines)

Distill the parse into a **styling spec**, one block per tile. On this path it is
checked **twice**: mechanically against the exported cell specs, and visually against
the render. Extract values from the export, never eyeball them:

- **Exact title + subtitle** (verbatim from the tile).
- **Cell type** — EXPLORE bar/line/area/pie/scatter, `pivot-table`, METRIC, markdown,
  Python 🐍.
- **Metrics + formulas** — the derivation each tile reads and the measure it shows;
  mark any **ratio** to pre-compute in SQL.
- **Encodings** — x / y + aggregation, color/series split, sort, facet, pivot.
- **Filter wiring** — which INPUT cells drive this tile.
- **Colors as hex codes** — from the tile's vis config and the export's
  `colorPalettes` (resolve the export-local palette key to its colors).
- **Tooltip / label fields**, **time ranges** (resolved), **number + date formats**.
- **Layout slot** — the row, and the tile's `gridPosition` on Omni's **24-column** grid
  (→ Hex 0–120 span = `x×5` to `(x+w)×5`).

---

## The handoff prompt

App form is controlled by **prompt wording alone**. Be prescriptive:

> *"Build this as a **CLASSIC HEX APP** using **native notebook cells** — SQL cells, input
> parameter cells, and native chart cells (EXPLORE / METRIC / pivot-table) arranged in the
> App builder layout. **Do NOT build a Generative app** and do not put the dashboard in
> app code — every chart must be a real Hex cell with an editable spec.*
>
> *Read the `Migration brief` + `Styling spec` cells — they are the full spec for
> migrating an Omni dashboard into this project.*
>
> *[Pre-built SQL:] The SQL cells already exist and are validated — **use them as the
> data source; do NOT write new SQL or rewrite those cells.** The charts read these
> dataframes: `<df1>`, `<df2>`, …*
> *[Agent-built SQL:] Build the SQL derivations named in the brief first, using the joins,
> measure definitions and always-on filters it spells out. **Consolidate** — one SQL cell
> should feed several tiles; do not write one pre-aggregated query per tile.*
>
> *Then build one native cell per tile in the Styling spec, using the cell type it names:
> exact titles, encodings, aggregations, colors (hex codes), label fields, time ranges,
> and number/date formats. Single-value tiles → METRIC cells fed a 1-row query. Ratios
> and Excel-style calculations are computed in SQL, not in the chart.*
>
> *Create input parameter cells for the dashboard filters (defaults + options per the
> brief), place them **upstream** of the SQL that reads them, and wire each to the tiles
> the brief names.*
>
> *Finally, assemble the **app layout** to mirror the Omni dashboard grid row-by-row at the
> widths the spec gives. Keep the Omni reference cells and raw SQL cells **out** of the app
> layout. [If multiple dashboards:] use **tab navigation**, one tab per dashboard."*

```bash
hex thread create --new-project "$(cat prompt.txt)" --json   # or --project <id> if cells exist there
```

**⚠️ Surface the returned `url` to the customer immediately.**

## Verify it actually built a classic app

```bash
hex project export <project_id> -o app.yaml
```

- **`genAppFiles` absent or empty**, native `cellType`s present, `appLayout.tabs[].rows[]`
  populated → classic. ✅
- **`genAppFiles` non-empty** → it built a generative app. Re-prompt:
  > *"Rebuild this as a classic Hex app with native notebook cells: replace the generative
  > app with real EXPLORE / METRIC / pivot cells bound to the existing SQL dataframes, and
  > assemble them in the App builder layout. Remove the generative app."*
- **Native cells but no `appLayout`** → `continue` it, or build the layout yourself via
  export → edit `appLayout` → import ([`gotchas.md`](gotchas.md) §App layout).
- **Split held + consolidated** — SQL cells present and (pre-built) unchanged, charts
  bound to those dataframes, no per-tile pre-aggregated SQL.

## Verify accuracy + fidelity (three gates)

1. **SQL-fidelity gate** (incl. the Omni result-parity check) — [`sql-review.md`](sql-review.md).
2. **Cell-spec diff (do this before screenshotting).** For each tile in the styling spec,
   read its cell in `app.yaml` and assert:
   - `cellType` / `config.spec.visualizationType` matches the spec'd cell type;
   - `config.dataframe` is the intended upstream SQL cell's output;
   - every encoding exists in `config.spec.fields[]` with the right `channel`, `value`,
     `aggregation`, and `truncUnit` for a date axis; **date axes are `dataType: DATE`**;
   - `displayFormat` matches the spec'd format; `colorMappings` / `chartConfig.series[]`
     carry the spec'd **hex codes**;
   - **`{field.seriesId} == {chartConfig.series[].id} == {seriesGroups ids}`** — a
     mismatch renders blank while the cell still runs COMPLETED
     ([`building-cells.md`](building-cells.md));
   - `appLayout` contains every viz cell, **no** reference/raw-SQL cells, **no fixed
     `height` on chart-type EXPLOREs**.
   Fix with one `hex thread continue` batch, or edit the YAML and re-import.
3. **Visual-QA loop on the render** — [`visual-qa-loop.md`](visual-qa-loop.md). Run it
   after the spec diff is clean; it catches what only a render shows (blank series,
   collapsed heights, clipped rows, live filter behavior).

## When to hand-build instead

Only when the notebook agent is unavailable (headless-agent-threads off, no Hex
credits). Same artifact; this coding agent clones `templates/` and assembles the
`appLayout` → [`building-cells.md`](building-cells.md).

## Cheat-sheet

- `hex thread create "$(cat prompt.txt)" --project <id> --json` → `url` (hand to customer) + `thread_id`.
- `hex project export <id> -o app.yaml` → `genAppFiles` **empty**, native `cellType`s, `appLayout` populated.
- Spec-diff each viz cell against the styling spec (types, encodings, colors, formats, seriesId linkage, layout).
- `hex thread continue <id> "<numbered fix list>"` → iterate.
