# Native Hex cells — the capability map (and the hand-build fallback)

**Read this on every classic-path migration**, not only on the fallback. It is the
**capability map for the classic artifact**: what a native EXPLORE/METRIC/pivot cell can
and cannot express, how each Omni tile maps onto one, and the traps that make a cell run
green while rendering wrong. You need it while parsing (to name the gaps) and while
running the **cell-spec diff** — even when the notebook agent builds.

It is **also** the procedure for the **hand-build fallback**: this coding agent builds
the SQL and the native cells itself, cloning `templates/` and assembling the `appLayout`
in YAML. Use it **only** when the notebook agent isn't available (headless-agent-threads
off, or no Hex credits). On that fallback this agent is **blind to the schema, the data,
and the render**, so the SQL gate, the result-parity check, the cell-spec diff, and the
visual-QA loop all carry more weight. It spends the customer's model tokens instead of
Hex credits.

> ⚠️ **What EXPLORE/METRIC can and can't aggregate.** An EXPLORE chart cell and a METRIC
> cell aggregate **one column** with a single built-in aggregation (`Sum, Avg, Count,
> CountDistinct, Min, Max, Median, StdDev, Variance…`). There is **no calculated
> measure** in the cell spec. So an Omni measure that is a **ratio of aggregates**
> (`SUM(a)/SUM(b)`), a **custom-SQL measure**, or a **filtered measure** must be
> **pre-computed in SQL** at the tile's grain. Additive measures aggregate fine in
> EXPLORE straight off the shared cell. ⚠️ And **never let EXPLORE re-aggregate a
> `count_distinct` measure** that was already computed at a finer grain — distinct
> counts don't sum.

---

## Native-cell templates (clone-and-override library)

Real, valid exported cell configs live in `templates/`. **Clone one, override a few
fields, import.** This beats building native cells from the JSON schema (which fails on
hidden required fields like `displayTableConfig`, `showAllBaseTableDetailFields`).

| File | Cell type | Covers (Omni equivalent) |
|------|-----------|--------------------------|
| `metric.json` | METRIC | **Single value / KPI** tile |
| `explore_bar.json` | EXPLORE (bar) | Bar/Column; **grouped** via `chartConfig.series[].barGrouped=true`, **horizontal** via `orientation`, **stacked** = default |
| `explore_line.json` | EXPLORE (line) | Line/time-series; **area** = flip `series[].type` to `area` |
| `explore_faceted.json` | EXPLORE (bar + facet) | Small multiples / a tile split into panels |
| `explore_pivot.json` | EXPLORE (`pivot-table`) | Table / pivoted table (also carries a filter example) |
| `explore_pie.json` | EXPLORE (pie/donut) | Pie/Donut; **donut** via `series[].radius`, data labels via `series[].text.dataLabels` |
| `explore_area.json` | EXPLORE (area) | Area / stacked area |
| `explore_scatter.json` | EXPLORE (scatter) | Scatter/Bubble (two measures) |

### How to clone-and-override
1. Load the template JSON, assign a **new `cellId`** — import **won't change an existing
   cell's type**, so native replacements need new ids (then repoint the `appLayout`).
2. Set `config.dataframe` to the upstream SQL cell's output dataframe.
3. Rewrite `config.spec.fields[]`: each field's `value` (column), `dataType`,
   `aggregation` (for measures), `truncUnit` (for a DATE axis), `displayFormat`.
   ⚠️ **Preserve the seriesId linkage — the #1 way a cloned chart silently renders
   blank.** In a template, every field's `seriesId` equals `chartConfig.series[].id`
   equals the id in `chartConfig.seriesGroups`. Mismatch → the series binds to nothing
   and the chart draws empty/partial — **yet the cell still runs COMPLETED**. Safest:
   reuse the template's series id on all fields and leave `chartConfig` alone. After
   building, assert `{field.seriesId} == {series.id} == {seriesGroups ids}`.
   - Reset template residue: `colorMappings: {}`, `spec.details.fields: []`,
     `displayTableConfig.columnProperties: []`; fix `chartConfig.orientation` / drop
     `series[].normalize` if the template's differ from the tile.
   - ⚠️ **COMPLETED ≠ renders correctly.** Never report a chart "built" on COMPLETED alone.
4. **METRIC (Omni single value)** **displays a single value, it does not aggregate.** It
   reads `valueColumn` at `valueRowIndex: 0`; `valueAggregate` is **rejected by the
   import API** (500 "unknown API error", though it passes schema validation). Feed it a
   **1-row SQL**:
   - **Warehouse-scalar query (default, CLI-friendly)** — a normal SQL cell, e.g.
     `SELECT SUM(<col>) AS total FROM <base> WHERE <population>`; `hex cell create
     --data-connection-id …` mints it.
   - **Dataframe-SQL over the shared df** (`dataFrameCell: true`, `dataConnectionId:
     null`) reuses the consolidated cell, but `hex cell create` **cannot** mint it —
     author it in YAML.
   Then `valueVariableName` = that 1-row dataframe, `valueColumn`, `valueRowIndex: 0`,
   `valueAggregate: null`, `displayFormat`. Omni single-value tiles often show a
   **comparison** (vs. prior period) → `showComparison`/`comparisonColumn`, fed a
   two-column 1-row query.
5. Put the cell in `cells[]`, add a matching `appLayout` element, import, `hex project run`.
6. **Validate against the Hex file-format JSON Schema before importing** — necessary,
   not sufficient.
   - **Live:** name the file `*.hex.yaml` and use the **[RedHat YAML extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml)** (schema auto-loads from SchemaStore).
   - **CLI / CI:** validate against `https://static.hex.site/hex-file-schema.json`.
   - If `hex project import` returns "unknown API error", bisect: import the base export,
     then add cells back one at a time.

### Feature references (how to mirror Omni)
- **Date axis → a DATE column at a grain, never a numeric proxy.** An Omni timeframe
  field (`created_at[month]`, `created_at[week]`) becomes a DATE column truncated in SQL
  **or** the raw DATE with `truncUnit` on the field. ⚠️ Don't bind a pre-bucketed
  numeric column (a `month_number`, a `fiscal_quarter` integer) to a date axis.
  **Confirm the real warehouse type** (`SELECT YEAR(<col>)` probe — `gotchas.md`).
- **Pivots → `pivot-table`** with `row`/`column`/`value` channel fields; an Omni pivoted
  **chart** (series per pivot value) → EXPLORE with the pivot field on `color`.
- **Faceting:** a `config.spec.fields[]` field with `channel: "h-facet"`/`"v-facet"`,
  `fieldType: "COLUMN"`.
- **Per-cell filters** (a tile-only filter that isn't a population filter):
  `{"column": ..., "fieldType": "COLUMN", "predicate": {"op": "IS_ONE_OF", "arg": [...]},
  "queryPath": [], "columnType": "STRING"}` — chart cells: `config.spec.filters`;
  pivot/table cells: `config.displayTableConfig.filters`. Population filters go in the
  SQL `WHERE` via `{{ param }}` instead.
- **Valid EXPLORE channels:** `base-axis, cross-axis, color, opacity, tooltip, h-facet,
  v-facet, row, column, value, source, destination`. There is **no `detail` channel**.
- **Sort + limit:** Omni tile queries carry an explicit `sorts` and `limit`. Reproduce a
  **top-N** in SQL (`ORDER BY … LIMIT n`), not by trusting the chart's default sort.

---

## Dashboard objects beyond charts

| Omni object | Hex |
|---|---|
| **Single value / KPI tile** | METRIC cell fed a 1-row SQL (above). |
| **Markdown tile (static)** | Markdown cell. |
| **Markdown tile with Mustache references** | Markdown cell with Hex Jinja over a 1-row dataframe, or a METRIC; custom HTML/CSS is a declared gap on this path. |
| **Image** | Markdown cell via **file upload (drag-drop)**, *not* by URL. |
| **Dashboard filter / control** | INPUT parameter cell + per-cell filters or a SQL `WHERE`. |
| **Table tile with conditional formatting** | `pivot-table` / table cell; conditional colors best-effort. |
| **Custom Vega-Lite vis** | Python cell (Altair renders Vega-Lite) 🐍, or the generative path. |
| **Spreadsheet tile / file upload** | No warehouse rows — ask the customer for the source; load as a file. |

---

## Styling — what maps from Omni

Styling lives in `config.spec.chartConfig` (data labels `series[].text.dataLabels`, donut
`series[].radius`, legend `settings.legend.position`, colors via `colorMappings`).

> A field used **only** as a color/series split still lives in the tile's query
> `fields` — keep it in the SQL and on the chart (see `gotchas.md`).

| Styling | In the Omni export? | Map it? |
|---------|---------------------|---------|
| Chart type, stacking, dual-axis | Yes (tile vis config) | **Yes** |
| **Colors / palette** | Yes (vis config + `colorPalettes`) | **Yes, high value** → `colorMappings` |
| **Number/date formats** | Yes (field `format` in the model + vis overrides) | **Yes, high value** → `displayFormat` |
| **Data labels** | Yes | **Yes** → `series[].text.dataLabels` |
| Axis titles, legend | Partial | Best-effort |
| Theme fonts, spacing, custom CSS | Partial | **No** on this path — declared gap (generative territory) |

Map **chart type, colors, number formats, and data labels** — they drive most of the
visual fidelity and all four are **assertable in the cell-spec diff**.
