# Build a Hex classic app (the default build)

The **default deliverable**: a **classic Hex app** — native notebook cells (SQL, INPUT
parameters, EXPLORE charts, METRIC tiles, pivot/table, markdown, Python) arranged in an
**`appLayout`**. The build is still **delegated to Hex's notebook agent** (it can see the
live warehouse schema, the workspace context, and its own render); what changes from the
generative variant of this skill is **what it builds**: real Hex cells a maintainer can
open, click, and edit — *not* a bespoke code app (`genAppFiles`).

> **Why classic.** The dashboard stays **native Hex**: every chart is a cell with a
> readable spec, the numbers are in SQL cells, filters are INPUT cells, and the customer's
> analysts can maintain it with no code. It's also **fully diff-able** — the exported YAML
> carries chart type, encodings, colors and formats, so fidelity can be verified
> *mechanically* against the styling spec, not only by eye. The trade is ceiling: native
> cells cannot reproduce a bespoke HTML/CSS/D3 Mode report page (see **Known ceilings**).

> **Division of labor is unchanged.** This coding agent owns *understanding the Mode
> source* and *verifying the result*; the notebook agent owns *building it in Hex*. The
> classic form only changes **what** it builds — not who guarantees accuracy.

## The core principle: split the layers (still)

1. **Data layer — native + gated (the accuracy guarantee).** SQL derivation cells
   (agent-built + gated post-hoc, or pre-built + gated first for subtle population), run
   through the full **SQL-fidelity gate** ([`sql-review.md`](sql-review.md)).
2. **Presentation layer — native viz cells over those dataframes.** EXPLORE/METRIC/pivot
   cells bind to the SQL cells' output dataframes. They **aggregate and filter over their
   input dataframe**, so one SQL cell feeds many charts — no per-chart re-query.

In the classic build the split is easier to hold than in the generative one: native viz
cells **can't** author SQL, so the data logic can't leak into the presentation layer. What
you must watch instead is the **opposite** failure — the agent pre-aggregating a separate
SQL cell per chart (Mode's own anti-pattern, carried across). Tell it to consolidate
(§"Consolidate" in [`mode-semantics.md`](mode-semantics.md)).

### Reuse the Mode query SQL when the warehouse is unchanged

When the target Hex connection is the **same warehouse** Mode queried, the Mode query
**already ran against this warehouse in this dialect** — do **not** re-invent it. Lift it
into a SQL cell (Liquid → Hex params), and validate it runs (`hex cell run
--with-output`). Re-derivation from intent is for when the **warehouse changed** (a
dialect port) or the query is a tangle of `{% if %}` branches you're consolidating. Either
way the result is a native SQL cell that goes through the gate.

---

## Known ceilings — name these BEFORE the build

A classic app is native cells, so anything with no native-cell analogue is a **gap you
declare up front**, not a surprise at QA. Put each in the brief with its agreed
substitute, and tell the customer during Step 0 triage:

| Mode feature | Classic-app outcome |
|---|---|
| **Bespoke HTML/Liquid report page** (custom CSS, `{% for row in query %}` loops) | ⚠️ **No native equivalent.** Reproduce the *content* as native cells (charts, METRIC tiles, markdown, pivot) in the same row order; the custom CSS/typography does **not** come across. If pixel fidelity to an HTML report is the requirement, use the **generative variant** of this skill instead. |
| **Chart.js / D3 / hand-written JS embeds** | ⚠️ Standard chart shapes → EXPLORE. Arbitrary JS visuals → **Python cell** (plotly/matplotlib) or flagged as dropped. |
| **Ratio-of-aggregates** (margin %, conversion rate) | EXPLORE/METRIC aggregate **one column with one built-in aggregation** — no calculated measure. **Pre-compute the ratio in SQL** (a thin companion query at the chart's grain) or use a semantic-model MEASURE. |
| **Big Number tile** | METRIC cell — but it **displays**, it doesn't aggregate. Feed it a **1-row SQL**; comparisons via `showComparison`/`comparisonColumn`. |
| **Maps** | No native map cell → **Python** `plotly.express.scatter_geo`/`choropleth` (🐍). |
| **Images** | Markdown cell via **file upload** (drag-drop), *not* by URL. |
| **Exact fonts / spacing / bespoke chrome** | Hex defaults. Mirror the *structure* (rows + column spans), not the pixels. |

Everything else — chart types, per-series colors, number/date formats, data labels,
faceting, filters, parameters, the row-by-row layout — maps well and is expected at
parity. The full native-cell capability reference (what each template covers, the field
and `seriesId` mechanics, the METRIC 1-row rule) is
[`building-cells.md`](building-cells.md) — read it as the **capability map** for the
classic build, not only as the hand-build fallback.

---

## The styling spec (drives the prompt AND both diff baselines)

Before the build, distill the parse into a **styling spec** — one block per report
section. In the classic build it is checked **twice**: mechanically against the exported
cell specs, and visually against the render. Extract values, never eyeball them:

Per section:
- **Exact title + subtitle** (verbatim from the chart JSON / HTML).
- **Cell type** — the Hex cell each tile becomes (EXPLORE bar/line/area/pie/scatter,
  `pivot-table`, METRIC, markdown, Python 🐍).
- **Metrics + formulas** — the query each tile reads and what it computes; mark any
  **ratio** that needs pre-computing in SQL.
- **Encodings** — x / y + aggregation, color/series split, sort, facet.
- **Filter wiring** — which INPUT cells drive this tile (and any cross-filter).
- **Colors as hex codes** — from the chart JSON (`color` / series palette) or the HTML
  report's CSS, **not** guessed from a screenshot.
- **Tooltip / label fields** — the measures shown and their formatted labels.
- **Time ranges** — the relative-date / date-range window, already resolved.
- **Number + date formats** — currency, %, decimals, thousands, date granularity.
- **Layout slot** — which row, and the tile's width as a share of the row (this becomes
  the 0–120 grid span).

Keep it tight and factual — it's a spec, not prose.

---

## The handoff prompt

App form is controlled by **prompt wording alone** — there is no CLI flag. A prompt that
opens by demanding a generative app gets one; a **chart-type-prescriptive** prompt gets
native cells. So be explicit and prescriptive:

> *"Build this as a **CLASSIC HEX APP** using **native notebook cells** — SQL cells, input
> parameter cells, and native chart cells (EXPLORE / METRIC / pivot-table) arranged in the
> App builder layout. **Do NOT build a Generative app** and do not put the dashboard in
> app code — every chart must be a real Hex cell with an editable spec.*
>
> *Read the `Migration brief` + `Styling spec` cells — they are the full spec for
> migrating a Mode report into this project.*
>
> *[Pre-built SQL:] The SQL derivation cells already exist and are validated — **use them
> as the data source; do NOT write new SQL or rewrite those cells.** The charts read these
> dataframes: `<df1>`, `<df2>`, …*
> *[Agent-built SQL:] Build the SQL derivations named in the brief first. **Consolidate** —
> one SQL cell should feed several charts; do not write one pre-aggregated query per chart.*
>
> *Then build one native cell per tile in the Styling spec, using the cell type it names:
> exact titles, the given encodings and aggregations, the given colors (hex codes),
> tooltip/label fields, time ranges, and number/date formats. Big numbers → METRIC cells
> fed a 1-row query. Ratios of aggregates must be pre-computed in SQL, not in the chart.*
>
> *Create input parameter cells for the report's parameters (defaults + options per the
> brief), place them **upstream** of the SQL that reads them, and wire them to filter the
> right cells.*
>
> *Finally, assemble the **app layout** to mirror the source report row-by-row: KPI/filter
> band on top, then each row's tiles left→right at the widths the spec gives. Keep the
> Mode source-reference cells and the raw SQL cells **out** of the app layout.
> [If multiple reports:] use **tab navigation**, one tab per report."*

Hand it off:

```bash
hex thread create --new-project "$(cat prompt.txt)" --json   # or --project <id> if cells exist there
```

- **⚠️ Surface the returned `url` to the customer immediately** — the build runs several
  minutes; let them watch and redirect it live.
- **Multiple reports in scope → tab navigation** (one tab per source report), named in
  the prompt.

## Verify it actually built a classic app

The prompt is the only lever, so **confirm the form** post-build:

```bash
hex project export <project_id> -o app.yaml
```

- **`genAppFiles` absent or empty**, **and** EXPLORE/METRIC/pivot `cellType`s present,
  **and** `appLayout.tabs[].rows[]` populated → it's a classic app. ✅
- **`genAppFiles` non-empty** → it built a generative app. Re-prompt:
  > *"Rebuild this as a classic Hex app with native notebook cells: replace the generative
  > app with real EXPLORE / METRIC / pivot cells bound to the existing SQL dataframes, and
  > assemble them in the App builder layout. Remove the generative app."*
- **Native cells present but no `appLayout`** (charts only in the notebook) → the app view
  is unbuilt. `continue` it to assemble the layout, or build the layout yourself via
  export → edit `appLayout` → import ([`gotchas.md`](gotchas.md) §App layout).
- **Confirm the split held** — SQL cells present and (pre-built) **unchanged** (diff the
  export), charts bound to those dataframes, params wired and **upstream** of their
  consumers.
- **Confirm it consolidated** — a separate pre-aggregated SQL cell per chart is the Mode
  anti-pattern carried over; `continue` it to consolidate where the population + grain
  allow.

## Verify accuracy + fidelity

Three gates. The first two are mandatory; the third replaces "hope the render is right."

1. **SQL-fidelity gate on the native SQL cells** — [`sql-review.md`](sql-review.md).

2. **Spec-diff gate on the viz cells (classic-only — do this before screenshotting).**
   The exported YAML carries the whole chart spec, so most look-&-feel errors are catchable
   without rendering anything. For each tile in the styling spec, read the cell in
   `app.yaml` and assert:
   - `cellType` / `config.spec.visualizationType` matches the spec'd cell type;
   - `config.dataframe` is the intended upstream SQL cell's output;
   - every spec'd encoding exists in `config.spec.fields[]` with the right `channel`,
     `value` (column), `aggregation`, and `truncUnit` for a date axis;
   - **date axes are `dataType: DATE`**, not a numeric look-alike column;
   - `displayFormat` matches the spec'd number/date format;
   - `colorMappings` / `chartConfig.series[]` carry the spec'd **hex codes**;
   - **`{field.seriesId} == {chartConfig.series[].id} == {seriesGroups ids}`** — a
     mismatch renders a blank or partial chart while the cell still runs COMPLETED
     ([`building-cells.md`](building-cells.md));
   - `appLayout` contains every viz cell, **no** reference/raw-SQL cells, and **no fixed
     `height` on chart-type EXPLORE elements** (a fixed height collapses the chart body).

   Fix divergences with one `hex thread continue` batch, or edit the YAML directly and
   re-import when a surgical fix is faster.

3. **Visual-QA loop on the render** — [`visual-qa-loop.md`](visual-qa-loop.md). Still
   required: the spec diff proves the spec is right, the screenshot proves it *renders*
   right (blank series, clipped layout, collapsed chart heights, overflowing labels).
   Run it after the spec diff is clean so the loop isn't spending rounds on things the
   YAML already told you.

## When to fall back to a hand-build instead

Delegation to the notebook agent is the default for every migration. Drop to
**this coding agent hand-building** the cells ([`building-cells.md`](building-cells.md))
**only** when the notebook agent is unavailable — the headless-agent-threads feature is
off, or there are no Hex credits. That's a capability constraint, not a style preference.
The target artifact is identical (native cells + `appLayout`); only the builder changes,
and this agent is blind to the schema and the render, so both gates carry more weight.

If the customer can't do the one-time screenshot login, you can still ship the classic app
and the spec-diff gate still runs — you just lose the automated render gate and fall back
to a side-by-side human visual QA.

## Cheat-sheet

- `hex thread create "$(cat prompt.txt)" --project <id> --json` → `url` (hand to customer) + `thread_id`.
- `hex project export <id> -o app.yaml` → assert `genAppFiles` **empty**, native `cellType`s present, `appLayout` populated, SQL cells unchanged; re-prompt if it built generative.
- Spec-diff each viz cell in `app.yaml` against the styling spec (types, encodings, colors, formats, seriesId linkage, layout).
- `hex thread continue <id> "<numbered fix list>"` → iterate (form fix, spec fix, and the visual-QA loop).
- Data layer native + gated; charts read those dataframes, never re-query.
