# Omni semantics → Hex (Phase 1: understand the dashboard)

The reference for **Phase 1** — reading an Omni dashboard and turning it into an
intent-level plan for the brief. Phase 2 (plan → Hex) lives in the build-path docs.

## The one thing to internalize first

**Omni is semantic-layer-first. A tile has no SQL — it has a query against a model.**
Each tile stores a query JSON (`table`/topic, `fields`, `filters`, `sorts`, `pivots`,
`limit`, `calculations`, …) that names fields like `order_items.total_revenue` and
`users.created_at[month]`. Omni turns that into warehouse SQL at run time by compiling
it against the **model** (views → dimensions/measures, topics → joins, relationships →
join keys and fan-out). So:

- Unlike **Mode** (the SQL *is* the source and ports verbatim), the Hex SQL is a
  **compilation** — and the compile is where migrations go wrong.
- Unlike **Tableau** (you reverse-engineer a viz language with no ground truth), Omni
  **hands you its own compilation and its own results**: `POST /v1/query/run` with
  `planOnly: true` returns the generated SQL, and the same call without `planOnly`
  returns the rows. Both are captured by `scripts/omni_fetch.py`.

So the method is: **read the query JSON + model to understand intent; use Omni's
generated SQL as the reference compilation; prove the port with result parity.**

## The source files (what `omni_fetch.py` saves)

| File | What it is | Use it for |
|---|---|---|
| `queries.json` | every saved tile query (`GET /v1/documents/{id}/queries`), with `modelId` filled in | the per-tile definition |
| `dashboard.v2.json` | `GET /v2/documents/{id}`: `queryPresentations` (tiles + `visConfig`), `controls` (filters), `containers` (layout), `settings` | vis, filters, layout. **422 on classic-layout dashboards** — then use `export.json` |
| `export.json` | `GET /unstable/documents/{id}/export` (org key only): `dashboard`, `workbookModel`, `queryModels`, `colorPalettes`, `fileUploads` | workbook/query-level model overrides, palettes, classic layouts, uploads |
| `models/<id>/*.yaml` | model YAML per layer (shared = `combined`, workbook/query = `extension`) | field definitions, topics, relationships |
| `sql/*.sql` | Omni's generated SQL per tile (`planOnly`) | the reference compilation for the SQL gate |
| `results/*.json` | Omni's rows per tile (`--results`) | result-parity baseline |
| `dashboard.png` | Omni's rendered dashboard (`--png`) | visual-QA reference |

⚠️ **Key everything off `identifier`, not `id`** — `id` is null for workbook-type
documents. ⚠️ **`queries.json` may include queries not placed on the dashboard** — use
the layout (`containers` / `queryPresentations`) to decide which tiles are in scope.

## How to use

1. **Resolve the connection** (`connection-mapping.md`) and decide **same warehouse or
   not**. Same warehouse ⇒ Omni's generated SQL runs as-is in Hex's dialect and result
   parity should tie exactly.
2. **Inventory the tiles** from the layout; classify each by type (§5) and mark the ones
   with no SQL equivalent.
3. **Resolve each tile's fields against every model layer** (§1) — shared, workbook,
   query. A field can be redefined in any layer.
4. **Map filters and controls** (§3) to Hex inputs with the right per-tile scope.
5. **Translate calculations** (§4) to SQL.
6. **Consolidate** tiles into shared SQL cells (§6).
7. **Record each translation** with the status legend (bottom), and extract the styling
   spec from the vis config (§5).

---

## 1. The model — where the meaning lives

### Layers (pull all of them)
- **Schema model** — auto-generated from the database; read-only.
- **Shared model** — the governed layer (views, topics, relationships). Most fields live here.
- **Workbook model** — per document, extends the shared model. **Fields defined or
  overridden in a single dashboard live here** — easy to miss, and a same-named shared
  field may mean something different.
- **Query model** — per tile (`queryJson.model_extension_id`), extends the workbook
  model. Rare but real (tile-level custom fields).
- **Branch models** — development; ignore unless the customer says the dashboard runs on
  a branch.

Resolve a field by walking **query → workbook → shared** and taking the most specific
definition.

### Views
```yaml
schema: ecomm
table_name: order_items          # defaults to the view name; or `sql:` for a SQL-based view
dimensions:
  id: { primary_key: true }
  sale_price: {}                 # a raw column maps to a same-named dimension automatically
  created_at: { timeframes: [raw, date, week, month, quarter, year] }
  is_high_value: { sql: '${sale_price} > 100' }
measures:
  count: { aggregate_type: count }
  total_revenue: { sql: '${sale_price}', aggregate_type: sum, format: currency_2 }
  completed_revenue:
    sql: ${sale_price}
    aggregate_type: sum
    filters: { status: { is: Complete } }
```
- **References:** `${field}` (same view), `${view.field}` (another view). Resolve them
  recursively to physical columns. Exports may also contain `${TABLE}.col` — treat it as
  the view's table alias.
- **Aggregations:** `sum, count, count_distinct, average, min, max, median, list,
  percentile` (+ `percentile: N`), and `*_distinct_on` variants (sum/avg distinct on a
  key, via `custom_primary_key_sql`) — those need a dedupe-then-aggregate pattern in SQL.
- **Filtered measures** (`filters:` on a measure) → `SUM(CASE WHEN <filter> THEN … END)`.
- **Timeframes:** `created_at[month]` = the dimension truncated to month. Keep it a DATE
  (`DATE_TRUNC('month', …)`), never a string.
- **Formats:** `currency_2`, `percent_1`, `number_0`, Excel-style strings → Hex
  `displayFormat` / app formatting.
- **SQL-based views** (`sql:`) → a CTE. **Query views** (`.query.view`, `query:` block) →
  plan the query view's own query (`planOnly`) and inline that SQL as a CTE.
- **Also watch for:** `groups` / `bin_boundaries` (CASE bucketing), `level_of_detail`
  (fixed-grain measures → a pre-aggregated subquery), `dynamic_top_n`, `duration`.

### Topics and relationships
```yaml
# <topic>.topic
base_view: order_items
joins: { users: {}, inventory_items: { products: {} } }
always_where_filters: { order_items.status: { not: Cancelled } }
default_filters: { order_items.created_at: { ... } }
access_filters: [ { field: users.region, user_attribute: region } ]

# relationships
- join_from_view: order_items
  join_to_view: users
  on_sql: ${order_items.user_id} = ${users.id}
  relationship_type: many_to_one   # one_to_many | one_to_one | many_to_many
  join_type: always_left
```
- A tile's `table` / `join_paths_from_topic_name` names the topic. Only the views the
  tile's fields touch are joined, along the topic's `joins` tree.
- **`always_where_filters` / `always_where_sql` apply to every query on the topic** —
  the #1 thing a hand compile drops. `always_having_*` likewise for measures.
- **`default_filters`** pre-populate the query's filters; the saved tile query usually
  already carries them — check, don't double-apply.
- **Fan-out:** when a tile crosses a `one_to_many` (or `many_to_many`) relationship, Omni
  corrects measure aggregation so the "one" side isn't double-counted. A naive
  `JOIN … SUM()` port double-counts. Aggregate each side at its own grain first, or use
  distinct-key aggregation. **Omni's generated SQL shows exactly how it handled it** —
  read it, and reproduce the same shape.
- **`access_filters`** (row-level security by user attribute) → see §7.

### YAML filter syntax (measures, topics)
`is`, `not`, `greater_than[_or_equal_to]`, `less_than[_or_equal_to]`, `between: [a, b]`,
`contains`, `starts_with`, `not_<op>`, lists `is: [CA, OR]`, nulls `is: null`, and
`or: [...]`. Topic-level filters use fully qualified `view.field`.

---

## 2. Tile queries

```json
{"modelId": "…", "table": "order_items",
 "fields": ["orders.region", "order_items.created_at[month]", "order_items.total_revenue"],
 "filters": {"order_items.created_at": {"type":"date","kind":"TIME_FOR_INTERVAL_DURATION",
             "ui_type":"PAST","left_side":"12 months ago","right_side":"12 months"}},
 "sorts": [{"column_name": "order_items.total_revenue", "sort_descending": true}],
 "pivots": [], "limit": 1000, "calculations": [], "column_totals": {}, "row_totals": {}}
```

| Query key | Hex meaning |
|---|---|
| `table` / `join_paths_from_topic_name` | base view + topic → `FROM` + joins |
| `fields` | dimensions → `SELECT` + `GROUP BY`; measures → aggregates; calc names → §4 |
| `filters` | `WHERE` (dimension) / `HAVING` (measure); multiple keys are ANDed |
| `sorts` | `ORDER BY` (`null_sort` too) |
| `limit` | `LIMIT`. Default **1000**, max 75,000, `null` = unlimited. ⚠️ A tile silently truncated at 1000 rows in Omni will show *more* in Hex — decide with the customer which is correct, then match it |
| `pivots` | pivot columns → `pivot-table` column channel / series split; or a SQL pivot |
| `column_totals` / `row_totals` | totals → pivot totals or a companion query |
| `fill_fields` | fill missing dates/values → a date spine `LEFT JOIN` |
| `userEditedSQL` | **raw-SQL tile** — the SQL is the source (Mode-like). Port it; note it **bypasses** `always_where` and access filters in Omni, so don't add them |
| `controls` | field/timeframe switchers bound to this tile (§3) |

### Filter objects → SQL
| `type` / `kind` | SQL |
|---|---|
| `string` `EQUALS` (values list) | `IN (…)`; `is_negative` → `NOT IN`; `case_insensitive` → `LOWER()` |
| `string` `CONTAINS` / `STARTS_WITH` / `ENDS_WITH` / `SQL_LIKE` / `IS_EMPTY` | `LIKE '%x%'` / `'x%'` / `'%x'` / `LIKE` / `= '' OR IS NULL` |
| `number` `EQUALS` / `GREATER_THAN` / `LESS_THAN` / `BETWEEN` | `=`/`>`/`<`/`BETWEEN` (**inclusive**) |
| `date` `BETWEEN` | `>= start AND < end` (**start-inclusive, end-exclusive**) |
| `date` `BEFORE` / `ON_OR_AFTER` | `<` / `>=` |
| `date` `TIME_FOR_INTERVAL_DURATION` / `TIME_FOR_UNIT_DURATION` (`left_side` "12 months ago", `right_side` "12 months") | relative window — resolve against **now in the query timezone**, with complete vs. partial periods as Omni does. Take the exact bounds from Omni's generated SQL, then express them relative (`DATEADD`) in Hex |
| `boolean` / `null` | `= TRUE/FALSE` / `IS [NOT] NULL` |
| `composite` (`conjunction`, `filters`) | `( … OR … )` |
| `user_attribute` | ⚠️ per-viewer value → §7 |
| `query` | filter by another query's results → a subquery / semi-join |

⚠️ Omni **silently ignores a malformed filter object**. If the generated SQL lacks a
filter the JSON appears to have, trust the SQL — that's what the dashboard actually shows.

---

## 3. Dashboard filters and controls → Hex inputs

From `dashboard.v2.json` → `controls.data.<id> = {config, map}` (or the export for
classic dashboards):

- **Filter controls** (`date`, `string`, `number`, `boolean`) → one **Hex input
  parameter** each. `config.fieldName` is the target field; `filterControlType`
  (`multiValueEquals`, `singleValueEquals`, `timeframe`, `singleDay`) picks the input
  type (multiselect, dropdown, date range, date). Carry the default and options.
- **Per-tile scope is in `map`.** No `map` → the filter applies to every tile with that
  field. `{"<tileKey>": false}` → **that tile ignores the filter**. `{"<tileKey>":
  "<otherField>"}` → on that tile, the filter targets a **different field**. Reproduce
  exactly — this is the most common filter-wiring bug.
- Two filters on the same field of the same tile are **ORed**.
- **Hidden controls** (in no container) still apply — they're fixed population filters.
- **`FIELD_SELECTION` kind `FIELD`** (metric switcher) → a Hex dropdown that swaps the
  measure column via Jinja (`{{ metric }}`-selected column, or a `CASE` on the input).
- **`FIELD_SELECTION` kind `TIMEFRAME`** (grain switcher `[date]/[week]/[month]`) → a
  dropdown driving `DATE_TRUNC({{ grain }}, …)`.
- `TOP_N`, `PERIOD_OVER_PERIOD`, `DYNAMIC_FILTER`, `MULTI_FIELD_FILTER`,
  `FIELD_PICKER` → no 1:1 input; build with a Jinja-driven SQL pattern and flag 🔸.
- **Cross-filtering** (`settings.crossfilterEnabled`) → classic: Hex chart cross-filter
  where supported; generative: app click handlers. Best-effort, flag 🔸.
- **Hex auto-quotes string params** — reference them bare: `WHERE region = {{ region }}`
  (multiselect: `IN ({{ regions | array }})` per Hex Jinja conventions). Quoting them
  gives `''value''` → zero rows.

---

## 4. Calculations (Excel-style, post-query) → SQL

Omni table calculations run **on the result grid after the query**, stored as an AST in
`calculations[]`:

```json
{"calc_name":"calc_pct","label":"% of Total","format":"0.0%",
 "sql_expression":{"type":"call","operator":"Omni.OMNI_PERCENT_OF_TOTAL",
   "operands":[{"type":"field","field_name":"orders.total_revenue","for_calc":true}]}}
```

Translate each to a **window function over the tile's result** (in the tile's SQL cell,
or a thin dataframe-SQL companion):

| Omni calc | SQL |
|---|---|
| percent of total | `x / SUM(x) OVER ()` (per pivot column if pivoted) |
| running total | `SUM(x) OVER (ORDER BY <sort>)` |
| offset / previous row (`OFFSET`, `C1` refs) | `LAG(x, n) OVER (ORDER BY <sort>)` |
| percent change | `(x - LAG(x)) / NULLIF(LAG(x), 0)` |
| rank | `RANK() OVER (ORDER BY x DESC)` |
| arithmetic on columns | plain expression |
| lookups / IF / text functions | `CASE` / string functions; complex ones → Python 🐍 |

⚠️ Calculations depend on the result's **sort and limit** — apply them after the same
`ORDER BY`/`LIMIT`, and verify against Omni's result rows (parity) because the generated
SQL may not include them (they're computed outside the warehouse).

---

## 5. Tiles and vis config → Hex

From `queryPresentations.data[k]`: `{name, type, query, visConfig: {chartType,
visConfig: {visType, config}}, resultConfig, subTitle, description, isSql}`. Omni charts
are Vega-Lite based.

| Omni `chartType` / tile type | Classic path | Generative path |
|---|---|---|
| `kpi` (`omni-kpi`), `summaryValue` | METRIC fed a 1-row SQL | KPI card |
| `table` (`omni-table`) + `resultConfig` (column order, hidden cols, conditional formatting) | `pivot-table` / table cell | table component |
| `bar*`, `column*` (grouped/stacked/%) | EXPLORE bar (orientation, grouping, `normalize`) | chart |
| `line`, `lineColor`, `area*` | EXPLORE line/area | chart |
| `barLine` (combo) | EXPLORE dual series | chart |
| `point*` | EXPLORE scatter | chart |
| `pie` | EXPLORE pie/donut | chart |
| `heatmap`, `boxplot`, `funnel`, `sankey`, `treemap` | 🔸 pivot-table w/ conditional color, or Python 🐍 | chart (closer) |
| `map`, `regionMap`, `svgMap` | Python 🐍 (plotly) | map component |
| `markdown` (`omni-markdown`, Mustache `{{#result}}…{{/result}}`, `{{controls.<id>.summary}}`, HTML/`<style>`) | static → markdown; values → Jinja over 1-row df; CSS ⚠️ gap | **best fit** — reproduce content + CSS |
| `code` (raw Vega / Vega-Lite) | Python 🐍 (Altair renders the spec) | reproduce the spec |
| `singleRecord` | markdown/table | detail card |
| `omni-ai-summary-markdown` (Blobby summary) | ⚠️ no SQL equivalent — drop, static text, or a Hex Magic/Threads pointer (agree with customer) | same |
| `spreadsheet` / `csv` upload tiles | ⚠️ no warehouse rows — ask the customer | same |
| `linked` (`sourceQueryPresentationKey`) | same SQL cell as its source tile | same |

**Layout:** `containers` is a tree — a filter-bar `stack`, then `page` → `grid` (**24
columns**) whose tile `stack`s carry `gridPosition {x, y, w, h}` and
`metadata.attachedQueryKey`. Rows = tiles sharing a `y` band, ordered by `x`. Classic:
Hex span = `x*5 … (x+w)*5` on the 0–120 grid. Multiple `page`s → Hex tabs.

**Colors:** vis config references palettes by key; the export rewrites them to
`export-palette-N` and lists their colors in `colorPalettes`. Resolve to hex codes for
the styling spec.

---

## 6. Consolidate into shared SQL cells

Every Omni tile is its own query; don't port that 1:1 into Hex. Cluster tiles that share
a **topic, population filters (topic + dashboard), and join path**, and emit one SQL cell
at the **finest grain** the cluster needs; charts aggregate over it.

**Don't consolidate** when tiles differ in: tile-level filters that change the
population, fan-out-sensitive measures (a `count_distinct` or a one-side measure across
a one-to-many join can't be re-aggregated from a finer grain), limits/top-N, or
calculations that need a specific sort. Those get their own SQL cell (or a companion
cell over the shared one). Prove every merge with a row-count probe or result parity.

---

## 7. Security and row-level access — detect + flag

- `access_filters` on a topic, `user_attribute` filters in queries, and
  `required_access_grants` on views/fields mean **different viewers see different rows**.
- ⚠️ **The generated SQL reflects the calling user's attributes.** With an org key, plan
  with `?userId=<membershipId>` for a representative user, and parameterize the filter.
- Hex equivalent: data-connection-level security / warehouse RLS, or a Hex input bound to
  the viewer (agree with the customer's admin). **Never silently drop an access filter**
  — flag ⚠️ and get a decision; dropping it widens what every viewer can see.

---

## Getting the SQL (quick reference)

```
POST /api/v1/query/run   {"query": <tile query>, "planOnly": true, "cache": "SkipCache"}
→ summary.display_sql   (some responses: summary.sql)
```
`omni_fetch.py` does this for every tile. Use it as the **reference compilation** in the
brief and in [`sql-review.md`](sql-review.md). If the plan lists `missing_fields` or
`invalid_calculations`, the tile is broken in Omni too — tell the customer before
migrating it.

## Dialect step: only when the warehouse changes

Same warehouse → the generated SQL is already the target dialect. Different warehouse →
translate the compiled SQL (date functions, `DATE_TRUNC` argument order, `QUALIFY`,
`ILIKE`, week start, boolean type, quoting/case of identifiers) and expect result parity
to need explanation.

---

## Status legend (how to record each translation)

- ✅ **direct** — maps cleanly (a dimension/measure/filter with a plain SQL equivalent).
- 🔸 **approximate** — reproducible but needs care (fan-out, relative dates, calculations,
  metric switchers, cross-filtering); prove with parity or a probe.
- 🐍 **Python** — needs a Python cell (custom Vega, maps on the classic path, complex
  calculations).
- ⚠️ **gap** — no faithful equivalent (AI summary tiles, access filters pending a
  decision, uploaded data without a source). Agree the substitute with the customer.
