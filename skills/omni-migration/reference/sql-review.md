# SQL-fidelity review gate

A mandatory review pass (SKILL.md step 6) — **the accuracy guarantee, on both build
paths, no matter who wrote the SQL.** On the delegated build it runs **post-hoc** on the
agent's cells; on pre-built SQL it runs before any presentation work. It exists to catch
the **dangerous error class**: SQL that runs (COMPLETED) but is **semantically wrong**.

> **What's different about Omni.** An Omni tile has **no SQL** — it's a semantic query
> (topic, fields, filters, sorts, pivots, limit) that Omni compiles against the model at
> run time. So the ported SQL is a **compilation**, not a lift, and the classic
> compile-time mistakes (lost joins, fan-out, dropped topic filters) are the main risk.
>
> **But Omni also gives this gate the strongest anchors of any source tool:**
> 1. **Omni's own compilation.** `POST /api/v1/query/run` with `planOnly: true` returns
>    the SQL Omni generates for the tile (`summary.display_sql`). `omni_fetch.py` saves
>    it per tile in `sql/`. The ported SQL is diffed against it — a divergence beyond
>    consolidation and parameterization is the first thing to explain.
> 2. **Omni's own results.** The same call without `planOnly` returns the rows. When Hex
>    points at the same warehouse, the Hex SQL cell's rows should **tie to Omni's rows**
>    — the **result-parity check** (§4) turns "does this SQL look right?" into "do the
>    numbers match?". Use it on every cluster.

The Omni-specific error classes this gate must catch:

- a **join dropped or added** — a field from a joined view pulled in without the join
  path Omni would use (`join_paths_from_topic_name`), or a join added that Omni didn't;
- **fan-out** — a measure on the "one" side of a one-to-many join summed after the join
  (Omni corrects for fan-out using the relationship type; naive SQL double-counts);
- a **topic `always_where` / default filter dropped** — silently widens the population
  of every tile on that topic;
- a **measure definition mis-compiled** — `count` vs `count_distinct`, a filtered
  measure's filter lost, a custom-SQL measure's `${}` references resolved to the wrong
  column, `sum_distinct`/median semantics lost;
- a **workbook-level field missed** — a field defined in the dashboard's
  `workbookModel`, not the shared model, compiled from the wrong definition (or not at
  all);
- a **dashboard filter wired wrong** — mapped to the wrong field on a tile, applied to a
  tile that opted out, wrong default, or the Hex quoting trap (quoted string param →
  zero rows);
- a **relative-date window off** — Omni filter expressions (`7 days ago`, `this month`,
  `before`, `between`) evaluated in the **query timezone** with the model's **week
  start**; a naive port uses UTC and Sunday;
- a **limit or sort dropped** — Omni tiles carry a row `limit` (and often a default
  one); a top-N tile without its `ORDER BY … LIMIT` shows all rows;
- an **Excel-style calculation** reproduced wrong (or not at all) — running totals,
  percent of total, offsets computed over the result grid after the query;
- **dialect drift** — only if the warehouse changed.

The fix is not "re-read the SQL and see if it looks right." It's four things together —
**structured + independent + targeted + result-anchored**:

## 1. Write the translation ledger (structured)

Per tile, grouped by the SQL cluster it maps to, an explicit **source → target** mapping:

| Ledger field | From the Omni export + model (source) | In the SQL (target) |
|---|---|---|
| **Topic / base view** | the query's `table` / topic + `join_paths_from_topic_name` | the `FROM` base table |
| **Joins** | every view the fields touch → relationship (`on_sql`, `relationship_type`, join type) | the `JOIN … ON` + how fan-out is handled |
| **Dimensions** | each dimension field + its model `sql` (resolved `${}`), timeframe (`[month]`) | the select expression / truncation |
| **Measures** | each measure + `aggregate_type` (+ filters, custom SQL) | the aggregate emitted |
| **Topic filters** | `always_where` / default filters on the topic | the `WHERE` |
| **Tile filters** | the query's `filters` (Omni filter expressions) | the `WHERE` / `HAVING` |
| **Dashboard filters** | each dashboard filter + the field it maps to on this tile | the Hex input + bare `{{ param }}` |
| **Pivots / sorts / limit / totals** | `pivots`, `sorts`, `limit`, row/column totals | `GROUP BY`/pivot, `ORDER BY`, `LIMIT`, totals query |
| **Calculations** | Excel-style formulas over the result | window functions / companion query / Python 🐍 |
| **Omni's SQL** | the generated SQL for the tile (`sql/*.sql`) | — the reference compilation to diff against |

Keep it in the migration plan alongside the `sql_cell → [tiles]` mapping. Use the status
legend (✅/🔸/🐍/⚠️) from [`omni-semantics.md`](omni-semantics.md).

## 2. Independent re-derivation & diff (independent)

**On Claude Code: spawn a subagent.** Give it *only* the tile's query JSON, the relevant
model YAML (views, topic, relationships, and the `workbookModel` overrides), and the
cluster's ledger rows — **not** the SQL that was built — and ask it to independently
compile the SQL each tile should produce, then diff three ways — its compilation, Omni's
generated SQL, and the built SQL — and report every divergence. A fresh context is the
whole value.

**Without subagents:** re-compile each cluster from scratch, deliberately without
looking at what was built, then compare.

Output: a **divergence list** — tile, what the source implies, what the built SQL does,
and the checklist class (§3). No divergences → continue to §4.

## 3. Targeted checklist — the known mistake classes

- ☐ **Join path.** Every view a tile touches is joined exactly as the topic's
  relationships define (keys, join type), and no extra joins were added.
- ☐ **Fan-out handled.** For every one-to-many relationship a tile crosses, measures on
  the "one" side are aggregated before the join (or use a distinct-key pattern).
  Proved with the fan-out probe (§5).
- ☐ **Topic filters kept.** Every `always_where` / default filter is in the `WHERE`.
- ☐ **Measure semantics.** `aggregate_type` matches — especially **`count` vs
  `count_distinct`**, filtered measures keep their filter, custom-SQL measures resolve
  every `${}`.
- ☐ **Workbook-level fields.** Any field defined in `workbookModel` is compiled from that
  definition, not a same-named shared-model field.
- ☐ **Dashboard filter wiring.** Each filter → one Hex input; bare `{{ param }}` (no
  quotes); default and options carried; applied to exactly the tiles Omni applied it to.
- ☐ **Relative dates.** Window bounds, timezone, and week start match Omni; inclusive vs
  exclusive end dates checked.
- ☐ **Sort + limit.** Top-N tiles keep `ORDER BY … LIMIT`.
- ☐ **Totals + calculations.** Pivot totals and Excel-style calculations reproduced and
  checked against Omni's result grid.
- ☐ **Real data types.** Dates stay DATE; types confirmed against the warehouse.
- ☐ **Ratio-of-aggregates** computed as `SUM(a)/SUM(b)` in SQL, never by averaging a
  pre-divided column.
- ☐ **Consolidation didn't change the population.** Tiles merged into one SQL cell only
  if they share topic, filters, and a compatible grain.
- ☐ **Dialect drift (only if warehouse changed).**
- ☐ **Deferred items are intentional.** Every 🐍/⚠️ row is a deliberate, noted gap.

## 4. Result-parity check against Omni (result-anchored)

The strongest check in the skill. For each tile (or at least one tile per cluster):

1. **Omni side:** `python scripts/omni_fetch.py --dashboard <id> --results` re-runs each
   tile's saved query via `POST /api/v1/query/run` (`resultType: json`) and saves the
   rows per tile under `omni_exports/<dash>/results/`. Long-running queries fall back to
   Omni's job flow, whose Arrow payload is decoded when `pyarrow` is installed (saved raw
   otherwise).
2. **Hex side:** `hex cell run <cell_id> --with-output` on the SQL cell (or on a thin
   probe cell that groups the shared cell to the tile's grain).
3. **Compare** row counts, key totals, and a few spot rows. Same warehouse + same
   snapshot ⇒ they should **tie exactly**. Any gap is a bug until explained.

Run it at the **default** filter values first; then re-run both sides with one
non-default value per dashboard filter to prove the filter wiring. Omni side: copy the
tile's `query` from `queries.json`, change the filter value, and run it with the Omni
CLI (`omni query run --body @q.json -o json`, with `"resultType": "json"` in the body)
or the same `POST /v1/query/run` call the script makes.

⚠️ **Parity is only meaningful against the same data.** If Hex points at a different
account/snapshot or the warehouse changed, expect drift and fall back to the probes in
§5 plus a human magnitude check. Record which case applies in the manifest.

## 5. Differential probes — prove behavior with the oracle

Turn each assertion into an expression that **raises divide-by-zero (→ ERRORED) exactly
when the assertion is violated**:

```sql
SELECT 1.0 / (CASE WHEN <assertion-holds> THEN 1 ELSE 0 END)
```

**COMPLETED = holds. ERRORED = violated.** ⚠️ ERRORED is overloaded — run anchor probes
first (`SELECT 1` → COMPLETED, `SELECT 1/0` → ERRORED) and keep the assertion an
aggregate comparison, never row-wise arithmetic that can throw. → [`gotchas.md`](gotchas.md).

- **A join didn't fan out:**
  ```sql
  SELECT 1.0 / (CASE WHEN
    (SELECT COUNT(*) FROM base) = (SELECT COUNT(*) FROM base JOIN dim ON <key>)
  THEN 1 ELSE 0 END)
  ```
- **A topic filter / dashboard filter actually moved the number:**
  ```sql
  SELECT 1.0 / (CASE WHEN
    (SELECT COUNT(*) FROM base) > (SELECT COUNT(*) FROM base WHERE <predicate>)
  THEN 1 ELSE 0 END)
  ```
  ERRORED ⇒ the predicate removed zero rows (quoting trap, wrong column, unbound param).
- **Result isn't empty:** `SELECT 1.0 / COUNT(*) FROM (<your query>)`.

⚠️ Probes are throwaway — `hex cell delete <cell_id>` them before handoff.

---

## Gate outcome

- **Pass** — ledger complete, re-derivation shows no divergence, checklist clean, result
  parity ties (or drift explained), probes COMPLETED.
- **Fail** — fix the SQL, re-run, re-gate the affected cluster. Don't build tiles on
  unreviewed SQL.
- **Deferred (🐍/⚠️)** — recorded in the ledger + manifest as a known gap.

In batch mode this runs per dashboard in Phase 2; record the result in the manifest
`gate` and `parity` fields.
