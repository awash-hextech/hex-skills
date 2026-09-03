# Mode semantics → Hex (Phase 1: understand the report)

The reference for **Phase 1** of a migration — reading a Mode report and turning it
into an intent-level plan for the brief. Phase 2 (that plan → a classic app of native
Hex cells) lives in `build-classic-app.md`, with the native-cell capability map in
`building-cells.md`.

## The one thing to internalize first

**Mode is SQL-native.** Every Mode query is a warehouse SQL statement that already
ran, in the warehouse's own dialect, against a named data source. There is **no viz
language to reverse-engineer** — unlike Tableau, where the durable IP was translating
VizQL/LOD/table-calcs into SQL, in Mode the SQL *is the source of truth and ports
close to verbatim.*

So the work re-centers on the layers Mode wraps around that SQL:

1. **Liquid templating** — parameters (`{% form %}` + `{{ @param }}`), branching
   (`{% if %}` / `{% case %}` / `{% assign %}`), and definition includes
   (`{{ @definition }}`). This is the single richest source of migration mistakes.
2. **Query / dataset dependencies** — definitions inlined into queries; one report
   reading another report's query as a **dataset**.
3. **Python / R notebook cells** — `datasets['Query Name']` → a Hex dataframe.
4. **Chart definitions** — Mode's chart-builder JSON → Hex EXPLORE/METRIC.
5. **The presentation layer** — Report Builder layout or a bespoke HTML/Liquid report
   page → native cells in a Hex `appLayout` (with the HTML page's styling as a declared
   gap).

## How to use

1. **Resolve the data source → Hex connection** (`connection-mapping.md`) and decide
   **same warehouse or not**. This gates everything below.
2. **If the warehouse is unchanged** (common): the SQL ports near-verbatim. Skip the
   dialect step; do the Liquid/definition/dataset/notebook translation.
3. **If the warehouse changes** (Mode on Redshift → Hex on Snowflake, etc.): *also* do
   a real **dialect translation pass** (see "Dialect step") — now the SQL is not a
   copy-paste.
4. Sweep the report for Liquid, definitions, dataset refs, notebook cells, and chart
   defs (see `gotchas.md` for the parsing landmines).
5. Consolidate into as few SQL cells as the queries allow (§"Consolidate" below).
6. Sanity-check totals against the source's last run (parity). Same warehouse +
   same snapshot ⇒ parity is **exact**; a gap is a bug.

## Dialect step: only when the warehouse changes

If Hex points at the **same** warehouse Mode queried, the query text is already in the
right dialect — **don't rewrite it.** Lift it verbatim, swap the Liquid for Hex params,
validate it runs.

If the customer is **also switching warehouses**, the SQL is no longer portable —
function names, date semantics, format tokens, and keywords like `QUALIFY` all vary.
**Open the target warehouse's function reference and verify each construct the query
uses.** When unsure, actually fetch/search the docs (you have WebFetch/WebSearch) rather
than guessing — a wrong name fails loudly, a wrong *semantic* (Monday vs Sunday week,
ASC vs DESC rank) fails silently as a parity gap.

| Warehouse | Function reference |
|---|---|
| Snowflake | https://docs.snowflake.com/en/sql-reference-functions |
| BigQuery | https://cloud.google.com/bigquery/docs/reference/standard-sql/functions-and-operators |
| Amazon Redshift | https://docs.aws.amazon.com/redshift/latest/dg/c_SQL_functions.html |
| Databricks SQL | https://docs.databricks.com/aws/en/sql/language-manual/sql-ref-functions.html |
| PostgreSQL | https://www.postgresql.org/docs/current/functions.html |
| DuckDB | https://duckdb.org/docs/sql/functions/overview |

What actually varies between dialects (confirm each against the docs): `QUALIFY`
support; `DATE_TRUNC` week anchoring (Monday vs Sunday) + date-part unit names; date
parsing tokens (`YYYY` vs `%Y`); conditional shorthand (`IFF`/`IF`/`IIF`); regex
function names; percentile/median syntax; string-index base + `SUBSTR`/`SUBSTRING`
naming; boolean type; identifier quoting + case-folding.

---

## 1. Liquid — the real translation work

Mode embeds [Liquid](https://mode.com/help/articles/using-liquid/) in query SQL. Every
Liquid construct must resolve to either (a) inlined static SQL, or (b) a Hex input
parameter + Jinja `{{ var }}`. Sweep **every** query for these.

### 1a. Parameters — `{% form %}` + `{{ @param }}`

Mode declares report parameters in a `{% form %}` block (often at the top of a query)
and references them elsewhere as `{{ @param_name }}`.

```sql
{% form %}
  start_date:
    type: date
    default: "2024-01-01"
  segment:
    type: select
    options: [All, Enterprise, SMB]
    default: All
{% endform %}

SELECT ... FROM deals
WHERE closed_date >= '{{ @start_date }}'
  {% if @segment != 'All' %} AND segment = '{{ @segment }}' {% endif %}
```

Translate to Hex:

| Mode | Hex |
|---|---|
| `{% form %}` field | an **INPUT (parameter) cell** — one per field |
| `type: date` | date input; carry the default |
| `type: text` / `number` | text / number input |
| `type: select` (`options:`) | dropdown; carry `options` + default |
| `type: checkbox` / boolean | toggle |
| `{{ @param }}` in SQL | Hex Jinja `{{ param }}` (name it identically) |
| `{% if @segment != 'All' %}…{% endif %}` | Hex Jinja `{% if segment != 'All' %}…{% endif %}` (Hex SQL cells support Jinja control flow) |

⚠️ **The quoting trap is inverted from Mode.** Mode requires you to quote a string
param yourself (`'{{ @segment }}'`). **Hex does the opposite — it auto-quotes string
params, so you must DROP the quotes.** Writing `'{{ segment }}'` in a Hex SQL cell
produces `''value''` and matches nothing (the query COMPLETEs but returns zero rows —
silent). Reference string params **bare**: `WHERE segment = {{ segment }}`. See
`gotchas.md`.

⚠️ **Classify each parameter's scope before wiring it** (same rule as any Hex build):
- **Data-population parameter** (rewrites the `WHERE` / changes totals — e.g. a date
  window, a segment filter): it belongs in the **shared SQL** and moves *every* chart on
  that query. In the brief, note it applies to all downstream cells.
- **Chart/display parameter** (a measure switcher, a per-chart Top-N): attach it to the
  named cells it affects. A measure switcher becomes `CASE {{ param }} WHEN … END`.
- Map the control to the domain (range→number/slider, list→dropdown, boolean→toggle,
  date→date input); carry the default.

⚠️ **Place the input cell UPSTREAM of the SQL that uses it** — Hex runs cells as a
dependency graph; an input below its consumer leaves `{{ var }}` unresolved and the run
ERRORs. See `gotchas.md`.

### 1b. Branching — `{% if %}` / `{% case %}` / `{% unless %}` / `{% assign %}`

Mode uses Liquid control flow to build dynamic SQL. **Sweep every branch** — a
`{% form %}` select that swaps the `WHERE` or the `GROUP BY` means the query has
*multiple shapes*, and the migrated cell must reproduce all of them (usually via Hex
Jinja `{% if %}`), not just the default branch.

- `{% assign x = ... %}` → a Jinja `{% set x = ... %}` or fold the value in.
- `{% case @param %}{% when 'a' %}…{% endcase %}` → Hex Jinja `{% if %}/{% elif %}`, or a
  SQL `CASE` if it's selecting a column/expression.
- ⚠️ A branch that changes the **grain or the population** is a fidelity risk — flag it
  (🔸) and prove each branch with a probe in the gate.

### 1c. Mode's built-in Liquid filters / objects

Mode ships helpers (`{{ form.start_date | date: "%Y-%m-%d" }}`, `{{ @param | default: … }}`,
run-time objects like `{{ run_at }}`, `{{ @report }}`). Translate each to its Hex
equivalent:
- date/number **formatting** filters → move formatting to the Hex display layer (chart
  `displayFormat` / a Python cell), not the SQL.
- `| default:` → the Hex input's default value.
- run-time objects (`run_at`, current user) → Hex has `now()`-style SQL + user context;
  map deliberately or flag.

---

## 2. Definitions & datasets — resolve dependencies

- 🔸 **Definitions** (`{{ @definition_name }}`) are reusable SQL snippets defined once and
  included in many queries — Mode's "Definitions" feature. In the export they appear as
  the include site (`{{ @name }}`) plus a definitions listing. **Resolve each to its SQL
  and inline it** as a **CTE** in the consuming cell, or (if reused across many cells)
  build it as its own upstream SQL cell the others read. Never leave a `{{ @definition }}`
  unresolved — Hex has no equivalent include and it will error. Carry heavily-reused
  definitions into the **data-source guide** as canonical metrics (`datasource-guide.md`).
- 🔸 **Dataset references** — a Mode report can read **another report's query result** as
  a dataset (Mode "Datasets"). This is a **cross-report dependency**. Resolve the upstream
  report's query and either (a) rebuild it as an upstream SQL cell in the same Hex project,
  or (b) if the dataset is shared widely, migrate it once and reference it. Flag it in the
  manifest `notes` so the batch order respects the dependency.

---

## 3. Python / R notebook cells → Hex Python cells

Mode's notebook is a Jupyter environment where query results are exposed as pandas
dataframes.

| Mode notebook | Hex |
|---|---|
| `datasets['Query Name']` (or `datasets[n]`) | the **output dataframe** of the corresponding Hex SQL cell — reference it by that cell's variable name |
| a Python cell (pandas / matplotlib / plotly / seaborn) | a Hex **Python code cell** (same libraries; Hex renders plotly/matplotlib natively) |
| `mode.export_html(...)` / HTML output embedded in the report | render in a Python cell (or a markdown cell if it's static) — there's no app-code layer to fold it into here |
| an **R** cell | Hex supports R, but Python is the default — **port the logic to Python** unless the customer needs R; flag R cells that use R-only packages |

⚠️ **Do not re-query the warehouse from the Python cell.** Mode notebooks read the
*already-run* query results; the Hex Python cell should likewise read the upstream SQL
cell's dataframe, not open a new warehouse connection. This keeps the gated-SQL layer
the single source of numbers.

Per-row/text-heavy outputs, custom tables, and bespoke matplotlib that a native chart
can't express → keep as a Python cell (🐍), don't force it into EXPLORE.

---

## 4. Charts → Hex EXPLORE / METRIC

Mode charts are simpler than Tableau viz and map closely to Hex's model — a chart is
built on **one query's result set** with x/y/series encodings. Read the chart JSON
(`scripts/mode_fetch.py` saves it) for the real config; don't eyeball the picture.

| Mode chart type | Hex |
|---|---|
| Line / Area | EXPLORE line/area (`explore_line.json` / `explore_area.json`) |
| Bar / Column / Stacked / Grouped | EXPLORE bar (`explore_bar.json`; `barGrouped`, `orientation`, stacking) |
| Pie / Donut | EXPLORE pie (`explore_pie.json`) |
| Scatter / Bubble | EXPLORE scatter (`explore_scatter.json`) |
| Combo (bar + line) | EXPLORE with mixed `series[].type` (dual axis) |
| **Big Number** (single value ± comparison) | **METRIC** cell (`metric.json`) — feed it a 1-row SQL; see `building-cells.md` |
| Table | EXPLORE `pivot-table` or a table cell |
| Pivot Table | EXPLORE `pivot-table` (`explore_pivot.json`) |
| Map | Hex has no native map → **Python** `plotly.express.scatter_geo/choropleth` (🐍) |

Carry from the chart JSON: exact **title**, x/y fields + aggregation, series/color
split, sort, **per-series colors as hex codes**, and **number/date formats**. A field
used only as a color/series split is still in use — don't drop it (see `gotchas.md`).

⚠️ **Ratio-of-aggregates.** A Hex EXPLORE/METRIC aggregates a **single column** with one
built-in aggregation — it cannot compute `SUM(a)/SUM(b)` (margin %, conversion rate). If
a Mode chart plots a ratio, pre-compute it in SQL (a thin grouped companion query that
reads the shared dataframe and emits the `ratio` column). See §"Consolidate" and
`building-cells.md`.

---

## 5. The presentation layer → native cells in an `appLayout`

Mode reports present in one of two ways, and they fit the classic build very differently:

- **Report Builder** (drag-and-drop layout of charts, big numbers, text, filters) → **the
  good fit.** It's already a grid of discrete tiles, which is exactly what native cells in
  an `appLayout` are. Describe the row-by-row layout + each tile's **width share** + the
  filter wiring in the brief; map tile → cell type; the app layout mirrors the rows.
- **Bespoke HTML / Liquid report page** (custom HTML/CSS, `{% for row in query %}` loops,
  Chart.js/D3 embeds) → ⚠️ **the classic build's ceiling.** Reproduce the *content and row
  order* with native cells (EXPLORE for standard chart shapes, markdown for prose/headers,
  a pivot cell for `{% for %}`-rendered tables, a Python cell for a non-standard visual),
  and **declare the custom CSS/typography and any hand-written D3/JS as gaps** with the
  substitute you agreed with the customer. If pixel fidelity to the HTML page is the
  requirement, route that report to the sibling **`mode-migration`** (generative) skill —
  decide per report, before building.

Report-level **filters** (Mode's filter bar) → Hex **INPUT parameter cells** + per-cell
filters / cross-filter, wired per the styling spec. Remember they must sit **upstream** of
the SQL that reads them (`gotchas.md`).

---

## 6. Consolidate into shared SQL cells — one query feeds many charts

Mode already tends toward one-query-per-chart, which is the **anti-pattern** to carry
into Hex (duplicated logic, drift). Consolidate where the queries allow.

**Mental model:** Hex's EXPLORE cells **aggregate and filter over their input
dataframe**, so you don't need a pre-aggregated SQL per chart — **one SQL cell can feed
many charts.**

**Cluster Mode queries into shared Hex SQL cells** when they share ALL of:
- the same **base table(s) + join shape**,
- the same **population** (same `WHERE` after Liquid resolution — including shared
  params),
- a **compatible grain** — build at the **finest grain any chart in the cluster needs**
  (plus its date/id keys); each chart rolls up from there.

Then emit **one SQL cell per cluster**, selecting the **union of every column + measure**
the cluster's charts reference. Often several Mode charts are literally the *same query*
with different chart types on top — those collapse to one Hex SQL cell trivially.

**Keep queries separate when:** different base table / join shape; one needs row-level
detail while another needs a heavy pre-aggregation; a **ratio-of-aggregates** or a
scalar KPI off an unrelated aggregation (emit a thin companion — ⚠️ a **dataframe-SQL
cell** `dataFrameCell: true, dataConnectionId: null`, which `hex cell create` **can't**
mint; author in YAML — see `building-cells.md`).

**Build only what's *used*.** Port only the queries a migrated report actually renders
(and any their definitions/datasets depend on). Carry unused-but-valuable definitions to
the **data-source guide** instead of the dashboard SQL.

**Make it reviewable:** record the `sql_cell → [charts]` mapping in the plan/manifest.
Target the **fewest SQL cells that don't force an incompatible grain**.

---

## 7. Security / row-level — detect + flag (v1)

Mode implements access via **workspace permissions, private/shared spaces, and (on some
plans) parameterized row filters** — not an in-query RLS DSL like Tableau's `USERNAME()`.
If a query filters on the current user (`{{ @mode_user }}`-style, a `WHERE user_email =
current_user`, or a join to a permissions table), **detect it and report it for manual
recreation** — recreate as a Hex/warehouse-side row filter + Hex sharing settings, don't
auto-apply in v1. Surface it in the migration notes.

---

## Status legend (how to record each translation)

| | Meaning |
|---|---|
| ✅ **SQL** | Ported into the cluster SQL (verbatim when same-warehouse; translated when the dialect changed). |
| 🔸 **Verify** | Ported but flagged (Liquid branch / definition inline / dataset ref / dialect gap / relative-date window) — sanity-check the total. |
| 🐍 **Python** | No SQL/EXPLORE equivalent — build as a Python cell (map, per-row detail, ported notebook logic, non-warehouse source). |
| ⚠️ **Manual** | No faithful equivalent — flag for the customer to recreate (arbitrary D3/JS in an HTML report, R-only logic, a user-based RLS policy). |

Record each query's translation + status in the migration plan/manifest so the parity
gate knows what to check and what was deliberately deferred.
