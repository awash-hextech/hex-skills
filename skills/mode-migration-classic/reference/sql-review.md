# SQL-fidelity review gate

A mandatory review pass (SKILL.md step 6) — **the accuracy guarantee, and it reviews
the SQL no matter who wrote it.** In the default (notebook-agent) build it runs
**post-hoc** on the agent's cells: export its SQL, read its values with `hex cell run
--with-output`, and diff against the Mode query + your independent re-derivation. In the
hand-build fallback it runs on your own SQL before charts. Same gate either way. It
exists to catch the **dangerous error class**: SQL that is *syntactically fine* — it
runs, the run-status oracle returns COMPLETED — but is **semantically wrong**.

> **Mode gives this gate an anchor Tableau never had.** The Mode query text is itself
> warehouse SQL. When the connection is **unchanged**, a ported cell that diverges
> *textually* from the source query (beyond the Liquid→param swap and consolidation) is
> the first thing to explain — the reference is concrete, not a reconstruction from a viz
> language. When the connection **changed**, the query is no longer a copy-paste and the
> dialect-translation error classes reappear (see the checklist).

The Mode-specific error classes this gate must catch: a **Liquid param wired wrong**
(quoted when it should be bare → zero rows; wrong default; wrong scope), a **`{% if %}`
branch dropped** (only the default branch ported), a **definition inlined incorrectly**
(wrong snippet, or a join lost when it was folded into a CTE), a **dataset reference left
dangling or rebuilt at the wrong grain**, a **dialect drift** (only when the warehouse
changed — week anchoring, `QUALIFY`, date tokens), a **join that fanned out**, a
**consolidation that changed the population** (two Mode queries merged into one cell but
they didn't actually share a `WHERE`).

The fix is not "re-read the query and see if it looks right." It's three things together
— **independent + structured + targeted**:

1. **Structured** — a translation ledger makes the source→target mapping explicit.
2. **Independent** — a *fresh-context* pass re-derives the intended SQL straight from the
   Mode query + Liquid and **diffs** it against what was built.
3. **Targeted** — a checklist of the known mistake classes, and **differential probes**
   that *prove* a filter/join/branch behaves using real queries, not reading.

Run this per SQL cluster (per shared SQL cell), not per chart — the cluster carries the
filters, joins, and grain.

---

## 1. Write the translation ledger (structured)

Before building any charts, record — per Mode query, grouped by the SQL cluster it maps
to — an explicit **source → target** mapping. This is the artifact the review diffs
against.

For each query capture:

| Ledger field | From the Mode report (source) | In the SQL (target) |
|---|---|---|
| **Base query SQL** | the query's `raw_query` text (verbatim) | the ported `SELECT` (verbatim if same-warehouse; translated if dialect changed) |
| **Liquid params** | every `{% form %}` field + `{{ @param }}` use | the Hex input cell + bare `{{ param }}` refs (no quotes) |
| **Branches** | every `{% if %}`/`{% case %}` path | the Jinja branches (all of them) reproduced |
| **Definitions** | each `{{ @definition }}` include | the CTE it was inlined as (or the upstream cell) |
| **Datasets** | any cross-report dataset ref | the upstream cell that rebuilt it (+ its grain) |
| **Grain** | the query's row grain | the query's grain (+ keys) |
| **Joins / model** | tables + join keys + expected cardinality | the `FROM … JOIN …` |
| **Aggregation** | the measures + kinds (SUM / AVG / COUNT / **COUNT DISTINCT**) | the aggregate emitted |

Keep it in the migration plan/manifest alongside the `sql_cell → [charts]` mapping. Reuse
the status legend (✅/🔸/🐍/⚠️) from [`mode-semantics.md`](mode-semantics.md) — check ✅/🔸
rows hard, treat 🐍/⚠️ as deliberately deferred.

## 2. Independent re-derivation & diff (independent)

> **The point is independence.** Re-derive from the source, don't re-read the answer.

**On Claude Code (and hosts with subagents): spawn a subagent.** Give it *only* the Mode
query SQL + Liquid (and the resolved definitions/dataset SQL) and the cluster's ledger row
— **not** the SQL that was built — and ask it to **independently derive the SQL each
chart's query should produce in Hex** (resolving the Liquid to Hex params, inlining
definitions, covering every branch), then diff its derivation against the actual built SQL
and report every divergence. A fresh context is the whole value.

**On hosts without subagents: fresh-context self-review.** Re-open the Mode query and
**re-compute** each cluster's intended Hex SQL from scratch — deliberately *without*
looking at what was built — then compare. Not "does this look right"; **"here's what it
should be — does it match?"**

Either way the output is a **divergence list**: for each mismatch, the query, what the
source implies, what the built SQL does, and which checklist class (§3) it falls under. No
divergences → gate passes. Any divergence → fix and re-run step 4's oracle.

## 3. Targeted checklist — the known mistake classes

Run every cluster against this.

- ☐ **Liquid param wiring.** Every `{% form %}` field → a Hex input; every `{{ @param }}`
  → a **bare** `{{ param }}` (string params NOT quoted — quoted = `''value''` = zero rows,
  silent). Defaults and options carried. Scope correct (population param in the shared
  `WHERE`; display param on its cell). → [`gotchas.md`](gotchas.md).
- ☐ **Branch coverage.** Every `{% if %}`/`{% case %}` path is reproduced (as Jinja or a
  SQL `CASE`), not just the default branch. A branch that changes grain/population is
  proven with a probe (§4). → [`mode-semantics.md`](mode-semantics.md) §1b.
- ☐ **Definitions inlined faithfully.** Each `{{ @definition }}` resolved to the correct
  SQL, folded in as a CTE without losing a join or a filter. → [`mode-semantics.md`](mode-semantics.md) §2.
- ☐ **Dataset refs resolved.** No dangling cross-report reference; the upstream rebuild is
  at the **right grain**.
- ☐ **Dialect drift (only if warehouse changed).** Week anchoring, `QUALIFY` support, date
  tokens, percentile/median syntax, boolean type — verified against the target dialect's
  docs. (Same-warehouse → the SQL is verbatim; this class is N/A.) → [`mode-semantics.md`](mode-semantics.md) "Dialect step".
- ☐ **Consolidation didn't change the population.** Two Mode queries merged into one cell
  only if they truly share a `WHERE` + grain; otherwise the merge silently added/removed
  rows. Prove with a count probe.
- ☐ **Aggregation kind.** `SUM` vs `AVG` vs `MIN/MAX`, and critically **`COUNT` vs
  `COUNT(DISTINCT …)`** — a silent count-vs-distinct swap is a classic wrong-number.
- ☐ **Join grain / fan-out / dedupe.** Cardinality preserved (default many-to-one); a
  one-to-many join that fans out inflates every downstream `SUM`/`COUNT`. Prove it (§4).
- ☐ **Real data types (dates especially).** Type confirmed against the **warehouse**, not
  a column name; dates stay `DATE`. → [`gotchas.md`](gotchas.md).
- ☐ **Ratio-of-aggregates.** Margin %, conversion rate computed as `SUM(a)/SUM(b)` in SQL,
  **not** as an EXPLORE aggregating a pre-divided column. → [`mode-semantics.md`](mode-semantics.md) §6.
- ☐ **Notebook cell reads the dataframe, not the warehouse.** A ported Python/R cell reads
  the upstream SQL cell's df, not a fresh query. → [`gotchas.md`](gotchas.md).
- ☐ **Deferred items are intentional.** Every 🐍/⚠️ ledger row is a *deliberate* gap noted
  for the customer, not an accidental drop.

## 4. Differential probes — prove behavior with the oracle

> **First: you can now read values directly.** `hex cell run <cell_id> --with-output`
> returns the result rows, so for a magnitude check (does this cluster's total / row count
> / distinct count match what the source rendered?) just **run it and read the number**.
> For same-warehouse migrations, compare directly against the Mode query's last-run value
> — they should tie exactly. The divide-by-zero probes below are still valuable when you
> want the assertion itself to be the pass/fail signal.

Turn each assertion into an expression that **raises divide-by-zero (→ ERRORED) exactly
when the assertion is violated**. General form:

```sql
SELECT 1.0 / (CASE WHEN <assertion-holds> THEN 1 ELSE 0 END)
```

**COMPLETED = assertion holds = good. ERRORED = assertion violated = bug.**

⚠️ **ERRORED is overloaded — anchor the oracle first.** A row-level throw (a date/cast
function hitting an unexpected type, an overflow) *also* returns ERRORED, indistinguishable
from the divide-by-zero you're testing for. Before trusting any probe: **(1)** run **anchor
probes** — a known-COMPLETED (`SELECT 1`) and a known-ERRORED (`SELECT 1/0`); **(2)** keep
`<assertion-holds>` an **aggregate comparison** (a scalar `CASE WHEN COUNT(*) … END`),
never row-wise arithmetic that can throw. → [`gotchas.md`](gotchas.md).

- **A param actually moved the number** (catches a mis-wired / no-op param):
  ```sql
  SELECT 1.0 / (CASE WHEN
    (SELECT COUNT(*) FROM base) > (SELECT COUNT(*) FROM base WHERE <param predicate>)
  THEN 1 ELSE 0 END)
  ```
  ERRORED ⇒ the predicate removed **zero** rows — the `''value''` quoting trap, a wrong
  column, or a param that didn't bind.
- **A branch changes the result** (catches a dropped `{% if %}` path): run the cell with
  each param value that selects a different branch (`hex cell run` after setting the input)
  and confirm the row count / grain differs as the source's branch implies.
- **A join didn't fan out** (many-to-one preserved):
  ```sql
  SELECT 1.0 / (CASE WHEN
    (SELECT COUNT(*) FROM base) = (SELECT COUNT(*) FROM base JOIN dim ON <key>)
  THEN 1 ELSE 0 END)
  ```
  ERRORED ⇒ the join inflated the row count.
- **Result isn't empty** (catches an over-filtered / mis-translated window or the quoting trap):
  ```sql
  SELECT 1.0 / COUNT(*) FROM (<your query>)
  ```
  ERRORED ⇒ zero rows.

⚠️ Probes are **throwaway scaffolding** — `hex cell delete <cell_id>` them before handoff.

> Probes prove *behavior* (a param fired, a branch differs, a join held, rows exist). For
> **magnitude**, read the value with `--with-output` and tie it to the Mode last-run number
> (same-warehouse) or confirm at visual QA (step 7).

---

## Gate outcome

- **Pass** — ledger complete, independent re-derivation shows no divergence, checklist
  clean, probes COMPLETED, magnitudes tie to the Mode source (same-warehouse). Proceed.
- **Fail** — any divergence or a probe ERRORED. Fix the SQL, re-run the step-4 oracle, then
  re-run this gate for the affected cluster. Don't build charts on unreviewed SQL.
- **Deferred (🐍/⚠️)** — recorded in the ledger + migration notes as a known gap; not a
  blocker.

**In batch mode** this runs per report in Phase 2 (sequential) — on the delegated build,
right after the notebook agent finishes and before you mark the report verified; on the
hand-build, right after oracle-validation and before native cells. Record the gate result
in the manifest `gate`/`notes`. The independent-review subagent is safe to spawn per
report; keep the human visual-QA gate in the main thread (Phase 3).
