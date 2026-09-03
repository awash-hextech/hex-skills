# Native Hex cells — the capability map (and the hand-build fallback)

**Read this doc on every classic-app migration**, not only on the fallback. It is the
**capability map for the target artifact**: what a native EXPLORE/METRIC/pivot cell can
and cannot express, how each Mode object maps onto one, and the traps that make a cell run
green while rendering wrong. You need that while parsing the report (to name the gaps) and
while running the **cell-spec diff** (to know what a correct spec looks like) — even when
Hex's notebook agent does the actual building.

It is **also** the procedure for the **hand-build fallback**: *this coding agent* builds
the SQL and the native chart/KPI cells itself, cloning the templates in `templates/` and
assembling the `appLayout` in YAML. Use the fallback **only** when the notebook agent
isn't an option: the headless-agent-threads feature is off or the customer has no Hex
credits. The artifact is identical either way — only the builder changes.

**Know what the fallback costs.** It spends the customer's **frontier-model subscription
tokens** (not "free" — just a different budget than Hex credits), and this agent is
**blind to the warehouse schema, the data, and the rendered result**. So the SQL-fidelity
gate, the cell-spec diff, and the visual-QA gate carry more weight there. **The default
builder** ([`build-classic-app.md`](build-classic-app.md)) is **Hex's notebook agent**,
which *can* see the schema + workspace context + its own render.

> **Mode makes the SQL half of the fallback much cheaper than Tableau's.** When the
> warehouse is unchanged, the Mode query text *is* the SQL — you lift it, swap Liquid for
> Hex params, and validate it runs. The re-derivation-from-a-viz-language burden is gone.
> The chart-building half (below) is identical work either way.

How to turn the Phase-1 SQL cells into native Hex chart/KPI cells by cloning templates.
(The SQL shape itself — clustering Mode queries into shared SQL cells — is a Phase-1
concern; see "Consolidate" in [`mode-semantics.md`](mode-semantics.md).)

> ⚠️ **What EXPLORE/METRIC can and can't aggregate.** A Hex EXPLORE chart cell and the
> METRIC (KPI/big-number) cell aggregate **one column** with a single built-in
> aggregation (`Sum, Avg, Count, CountDistinct, Min, Max, Median, StdDev, Variance…`).
> There is **no per-field formula / calculated-measure** in the cell spec. So a **ratio of
> aggregates** (`SUM(a)/SUM(b)` — margin %, conversion rate) or any derived measure must
> be **pre-computed in SQL** — a thin companion query grouped to the chart's grain that
> reads the shared dataframe and emits the ratio as a column. The higher-fidelity
> alternative is a semantic-model MEASURE. Additive measures aggregate fine in EXPLORE
> straight off the shared cell.

---

## Native-cell templates (clone-and-override library)

Real, valid exported cell configs live in `templates/`. **Clone one, override a few
fields, import.** This beats building native cells from the JSON schema (which fails on
hidden required fields like `displayTableConfig`, `showAllBaseTableDetailFields`).

| File | Cell type | Covers (Mode equivalent) |
|------|-----------|------------------------------|
| `metric.json` | METRIC | **Big Number** tile / single-value KPI |
| `explore_bar.json` | EXPLORE (bar) | Bar/Column; **grouped** via `chartConfig.series[].barGrouped=true`, **horizontal** via `orientation`, **stacked** = default |
| `explore_line.json` | EXPLORE (line) | Line/time-series; **area** = flip `series[].type` to `area` |
| `explore_faceted.json` | EXPLORE (bar + facet) | Small-multiples / a chart split into panels |
| `explore_pivot.json` | EXPLORE (`pivot-table`) | Table / Pivot Table (also carries a filter example) |
| `explore_pie.json` | EXPLORE (pie/donut) | Pie/Donut; **donut** via `series[].radius`, data labels via `series[].text.dataLabels` |
| `explore_area.json` | EXPLORE (area) | Area / stacked area |
| `explore_scatter.json` | EXPLORE (scatter) | Scatter/Bubble (two measures) |

### How to clone-and-override
1. Load the template JSON, assign a **new `cellId`** — import **won't change an existing cell's type**, so native replacements need new ids (then repoint the `appLayout`).
2. Set `config.dataframe` to the upstream SQL cell's output dataframe.
3. Rewrite `config.spec.fields[]`: set each field's `value` to the column, its `dataType`, `aggregation` (for measures), `truncUnit` (for a DATE axis), and `displayFormat`. ⚠️ **Preserve the seriesId linkage — this is the #1 way a cloned chart silently renders blank.** In a template, every field's `seriesId` equals `chartConfig.series[].id` equals the id in `chartConfig.seriesGroups`. The chart renders from `chartConfig.series`, so if you regenerate the fields' `seriesId` but leave `series[].id`/`seriesGroups` at the template's value (or vice-versa), the series binds to nothing and the chart draws empty/partial — **yet the cell still runs COMPLETED**. Safest: **reuse the template's existing series id** on all fields and leave `chartConfig` alone. If you must regenerate, change all three in lockstep. After building, assert `{field.seriesId} == {series.id} == {seriesGroups ids}`.
   - Also reset template residue to your data: `colorMappings: {}`, `spec.details.fields: []`, `displayTableConfig.columnProperties: []`, and fix `chartConfig.orientation` / drop `series[].normalize` if the template's differ from what you want (e.g. a faceted template ships `normalize: "base-axis"` = 100%-stacked, wrong for a rate chart).
   - ⚠️ **COMPLETED ≠ renders correctly.** The run-status oracle only proves the query ran; a broken viz spec passes it. Chart correctness is a **human visual-QA gate** — never report a chart "built" on COMPLETED alone.
4. For METRIC (Mode Big Number): it **displays a single value, it does not aggregate.** A METRIC reads one column at one row (`valueColumn` at `valueRowIndex: 0`); `valueAggregate` is **rejected by the import API** (any value — `"SUM"`, `"Sum"` — 500s with an opaque "unknown API error", though it passes JSON-schema validation). So for a computed KPI, feed it a **1-row SQL** and point the METRIC at that. Two ways to make that 1-row cell:
   - **Warehouse-scalar query (CLI-friendly — default).** A normal SQL cell against the resolved connection, e.g. `SELECT SUM(<col>) AS TOTAL FROM <base>`. `hex cell create --data-connection-id …` mints it directly. (Mode Big Numbers usually already *are* a small aggregate query — lift it.)
   - **Dataframe-SQL over the shared df** (`dataFrameCell: true`, `dataConnectionId: null`, e.g. `SELECT SUM(<col>) AS TOTAL FROM <shared_df>`) reuses the consolidated cell instead of re-querying — **but `hex cell create` CANNOT mint this** (it ERRORs); it must be **authored in YAML**. Use this only when you're already editing YAML; otherwise take the warehouse-scalar path.

   Then set the METRIC's `valueVariableName` = that 1-row dataframe, `valueColumn` = its column, `valueRowIndex: 0`, `valueAggregate: null`, + `displayFormat`. Mode Big Numbers often show a **comparison** (vs. prior period) — map it to the METRIC's `showComparison`/`comparisonColumn` fields, feeding a two-value or two-column 1-row query.
5. Put the cell in `cells[]`, add a matching `appLayout` element, import, then `hex project run`.
6. **Validate against the Hex file-format JSON Schema before importing — but know it's necessary, not sufficient.**
   - **Live, while editing (recommended):** name the working file `*.hex.yaml` and install the **[RedHat YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml)**; it auto-loads the schema from **[SchemaStore](https://www.schemastore.org/)** for real-time validation, autocomplete, and hover docs.
   - **CLI / CI:** validate against the hosted schema `https://static.hex.site/hex-file-schema.json` (fetch it at run time — it tracks the current Hex format).
   - **Necessary, not sufficient:** a spec can pass schema validation and still be rejected by the import API (e.g. METRIC `valueAggregate`). If `hex project import` returns "unknown API error", bisect: import the base export, then add cells back one at a time to isolate the offending cell.

### Feature references (how to mirror Mode)
- **Date axis → a DATE column at a grain, NEVER a numeric proxy.** If a Mode chart's x-axis is a **date field**, the Hex field bound to that channel MUST be `dataType: DATE`, with the grain carried as `truncUnit` (`year`/`quarter`/`month`/`week`/`day`). ⚠️ **The trap:** don't bind a numeric column whose *name* matches the grain (`closed_month`, `order_quarter`, a `..._period` bucket) to a date axis just because the label fits — it's often a pre-bucketed **NUMBER**, so the chart renders a number line, not a time axis. **Confirm the field's real warehouse type** (`SELECT YEAR(<col>)` probe — see `gotchas.md`); if numeric, use the true DATE column at the chart's grain instead.
- **Faceting → small-multiples/trellis:** a `config.spec.fields[]` field with `channel: "h-facet"` or `"v-facet"`, `fieldType: "COLUMN"`.
- **Per-cell filters → a Mode chart/report filter that isn't a data-population param:** shape `{"column": ..., "fieldType": "COLUMN", "predicate": {"op": "IS_ONE_OF", "arg": [...]}, "queryPath": [], "columnType": "STRING"}`. Chart cells: `config.spec.filters`. Pivot/table cells: `config.displayTableConfig.filters`. (Data-population params go into the SQL `WHERE` via `{{ param }}` instead.)
- **Pivot / table → Mode Table / Pivot Table:** `config.spec.visualizationType: "pivot-table"` with `row`/`column`/`value` channel fields.
- **Valid EXPLORE channels:** `base-axis, cross-axis, color, opacity, tooltip, h-facet, v-facet, row, column, value, source, destination`. There is **no `detail` channel**.

---

## Report objects beyond charts

A Mode report also holds non-chart objects. Handle them, don't silently drop them.

| Mode object | Hex |
|---|---|
| **Big Number** | METRIC cell fed a 1-row SQL (above). |
| **Text / Markdown block** | **Markdown/Text cell** — port the formatted text to markdown. |
| **Image** | Hex renders images in a **Markdown/Text cell via file upload (drag-drop)** — *not* by URL. Download the image, add it to a markdown cell, place it in the `appLayout`. |
| **Filter (report filter bar)** | **input-parameter cell** + per-cell filters / cross-filter. |
| **Parameter control (`{% form %}` field)** | **input-parameter cell** (see `mode-semantics.md` §1a). |
| **Python/R notebook output** | **Python cell** reading the upstream SQL dataframe (see `mode-semantics.md` §3). |
| **Bespoke HTML / Liquid section, Chart.js/D3** | ⚠️ **No clean native-cell equivalent — the classic build's hard ceiling.** Reproduce the standard chart shapes as EXPLORE, the prose/structure as markdown, non-standard visuals as a Python cell, and **flag arbitrary D3/JS + the custom CSS as declared gaps**. If pixel fidelity to the HTML page is the requirement, route that report to the sibling `mode-migration` (generative) skill. |

---

## Styling — what maps from Mode

Styling lives in `config.spec.chartConfig` (data labels `series[].text.dataLabels`, donut `series[].radius`, legend `settings.legend.position`, colors via `colorMappings`). Split it — don't try 1:1:

> The field a color/series split rides on lives in the chart's encodings. Make sure your parse kept it — a column that appears *only* as an encoding is still in use (see `gotchas.md`).

| Styling | In the Mode export? | Map it? |
|---------|----------------|---------|
| Chart type, stacking, dual-axis/combo | Yes (chart JSON) | **Yes** |
| **Colors / palette** (per series) | Yes (chart color config / HTML CSS) | **Yes, high value** → `colorMappings` |
| **Number/date formats** ($, %, decimals) | Yes (chart format config) | **Yes, high value** → `displayFormat` |
| **Data labels** (show/hide + field) | Yes | **Yes** → `series[].text.dataLabels` |
| Axis titles, legend on/off | Partial | Best-effort |
| Fonts, exact spacing, bespoke CSS | Partial (HTML reports only) | **No** — declared gap; Hex defaults (generative-app territory) |

Bottom line: map **chart type, colors, number formats, and data-labels-on/off** from the export — those drive most of the visual fidelity, and all four are **assertable in the cell-spec diff** ([`build-classic-app.md`](build-classic-app.md)). Leave cosmetic-only knobs as sensible Hex defaults; deep HTML-report styling is a declared gap in this build (it's what the sibling generative skill is for).
