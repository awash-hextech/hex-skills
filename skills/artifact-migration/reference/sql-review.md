# SQL-fidelity review gate

A mandatory review pass (SKILL.md step 8) — **the accuracy guarantee, and it reviews the
SQL no matter who wrote it.** On the pre-built path (the default here) it runs on your own
SQL before the app is built; on the agent-built path it runs **post-hoc** on the agent's
cells. It exists to catch the **dangerous error class**: SQL that is *syntactically fine*
— it runs, the oracle returns COMPLETED — but is **semantically wrong**.

> **⚠️ This gate has no source query to diff against.** Tableau gave you a viz spec to
> reconstruct from; Mode gave you literal warehouse SQL. An artifact gives you **neither**
> — its "query" was a hardcoded array. So the reference this gate diffs against is the
> **grounding ledger** ([`data-grounding.md`](data-grounding.md)), and the independent
> re-derivation (§2) carries proportionally more weight than in the sibling skills. Textual
> diffing has nothing to bite on; re-derivation is the whole gate.

The artifact-specific error classes to catch:

- **🚨 A mock constant survived** — an artifact value hardcoded into a `CASE`, a `VALUES`
  list, a `UNION ALL` of literals, or an inline `pd.DataFrame([...])`. *The signature
  failure of this migration.* §5.
- **🚨 A panel with no cell behind it** — a number rendered in the app that traces to
  nothing gated. §5.
- **SQL tuned to match the artifact's picture** — a filter or a coefficient chosen so the
  chart resembles the mockup rather than the data.
- **An invented metric given a real-looking definition** — the artifact showed
  `health_score`; someone improvised a formula and shipped it under that label.
- **Grain mismatch** — the panel draws daily, the table is monthly (or vice versa), papered
  over with an interpolation or a silent re-bucket.
- **Client-side logic not moved into SQL** — a `.filter()` that changed the population left
  in app code, so the gated cell and the displayed number disagree.
- **Ratio-of-aggregates** — a per-row ratio averaged instead of `SUM(a)/SUM(b)`.
- **Join fan-out**, **`COUNT` vs `COUNT(DISTINCT …)`**, **date-type drift** — the classics.

The fix is three things together — **independent + structured + targeted**:

1. **Structured** — the ledger makes the intended mapping explicit.
2. **Independent** — a *fresh-context* pass re-derives the intended SQL from the grounding
   ledger and **diffs** it against what was built.
3. **Targeted** — a checklist of known mistake classes, plus **probes** that *prove*
   behavior with real queries.

Run this per SQL cluster (per shared SQL cell), not per panel.

---

## 1. Write the translation ledger (structured)

Extend the grounding ledger with the target SQL. Per derivation:

| Ledger field | From the artifact (source) | In the SQL (target) |
|---|---|---|
| **Data shape** | the array/values as the page uses them | the cell that replaces it |
| **Provenance** | 🎭 / 📋 / 🗄️ / 🔌 | — |
| **Disposition** | Ground / Drop / Stub | (Stub/Drop → no cell; confirm none exists) |
| **Grain** | one row per *what*, on the page | the query's grain (+ keys) |
| **Columns** | artifact column → | warehouse column (+ aggregate) |
| **Population** | the filters the panel implies | the `WHERE` |
| **Derived logic** | the JS that transformed it | the aggregate / window function |
| **Joins / model** | (usually none — it was one array) | the `FROM … JOIN …` + expected cardinality |

⚠️ **The "source" column is a description, not values.** Never record the artifact's
numbers as expected output — that turns the ledger into the anti-pattern the grounding gate
exists to prevent ([`data-grounding.md`](data-grounding.md) §5).

Keep it in the migration plan/manifest alongside the `sql_cell → [panels]` mapping. Use the
legend (✅/🔸/🐍/⚠️) from [`artifact-semantics.md`](artifact-semantics.md) — check ✅/🔸 rows
hard, treat 🐍/⚠️ as deliberately deferred.

## 2. Independent re-derivation & diff (independent)

> **The point is independence.** Re-derive from the ledger, don't re-read the answer.
> **This is the load-bearing step in this skill** — with no source query, it's the only
> thing standing between "the SQL runs" and "the SQL is right."

**On Claude Code (and hosts with subagents): spawn a subagent.** Give it *only* the
grounding ledger rows (shape, target table, column mapping, grain, population, derived
logic) — **not** the SQL that was built, and **not** the artifact's values — and ask it to
**independently derive the SQL each panel needs**, then diff its derivation against the
actual built SQL and report every divergence. A fresh context is the whole value.

**On hosts without subagents: fresh-context self-review.** Re-open the ledger and
**re-compute** each cluster's intended SQL from scratch, deliberately *without* looking at
what was built — then compare. Not "does this look right"; **"here's what it should be —
does it match?"**

Output is a **divergence list**: for each mismatch, the derivation, what the ledger implies,
what the built SQL does, and which checklist class (§3) it falls under.

## 3. Targeted checklist — the known mistake classes

- ☐ **Every Ground row has exactly one gated cell**, and every Drop/Stub row has **none**.
- ☐ **No mock constants** — §5's sweep is clean.
- ☐ **Target table + columns match the ledger** — the cell queries the table the customer
  named, not a plausible neighbor the agent found.
- ☐ **Grain matches the panel.** If the ledger recorded a grain change (🔸), the panel's
  label reflects it.
- ☐ **Population / filters.** The `WHERE` matches the ledger's intent; relative-date
  windows checked for off-by-one.
- ☐ **Derived logic landed in SQL.** Every number-changing JS transform
  ([`artifact-semantics.md`](artifact-semantics.md) §6) is in the cell, not the app.
- ☐ **Ratio-of-aggregates** — `SUM(a)/SUM(b)`, not an average of a pre-divided column.
- ☐ **Aggregation kind** — `SUM` vs `AVG` vs `MIN/MAX`, and critically **`COUNT` vs
  `COUNT(DISTINCT …)`**.
- ☐ **Join grain / fan-out / dedupe** — cardinality preserved; prove it (§4).
- ☐ **Param wiring** — every control → a Hex input; **bare** `{{ param }}` for strings
  (quoted = `''value''` = zero rows, silent). Inputs **upstream** of consumers. →
  [`gotchas.md`](gotchas.md).
- ☐ **Real data types (dates especially)** — confirmed against the **warehouse**, not a
  column name; dates stay `DATE`.
- ☐ **Python cells read the dataframe, not the warehouse** — no re-query that could drift
  from the gated cell.
- ☐ **No invented metric shipped under the artifact's label** — every metric has a
  customer-confirmed definition, or it was dropped.
- ☐ **Deferred items are intentional** — every 🐍/⚠️ row is a deliberate, noted gap.

## 4. Differential probes — prove behavior with the oracle

> **First: you can read values directly.** `hex cell run <cell_id> --with-output` returns
> the result rows, so for a magnitude check just **run it and read the number**. ⚠️ Compare
> it to the **warehouse**, never to the artifact — the artifact's number is not a target
> ([`visual-qa-loop.md`](visual-qa-loop.md)).

Turn each assertion into an expression that **raises divide-by-zero (→ ERRORED) exactly
when the assertion is violated**:

```sql
SELECT 1.0 / (CASE WHEN <assertion-holds> THEN 1 ELSE 0 END)
```

**COMPLETED = assertion holds = good. ERRORED = assertion violated = bug.**

⚠️ **ERRORED is overloaded — anchor the oracle first.** A row-level throw (a date function
on an unexpected type, an overflow, a bad cast) *also* returns ERRORED, indistinguishable
from the divide-by-zero you're testing for, so a probe can **falsely "confirm"** a wrong
hypothesis. Guard it: **(1)** run **anchor probes** — a known-COMPLETED (`SELECT 1`) and a
known-ERRORED (`SELECT 1/0`); **(2)** keep `<assertion-holds>` an **aggregate comparison**
(a scalar `CASE WHEN COUNT(*) … END`), never row-wise arithmetic that can throw.

- **Result isn't empty** (over-filtered window, or the `''value''` quoting trap):
  ```sql
  SELECT 1.0 / COUNT(*) FROM (<your query>)
  ```
- **A param actually moved the number** (mis-wired / no-op param):
  ```sql
  SELECT 1.0 / (CASE WHEN
    (SELECT COUNT(*) FROM base) > (SELECT COUNT(*) FROM base WHERE <param predicate>)
  THEN 1 ELSE 0 END)
  ```
- **A join didn't fan out:**
  ```sql
  SELECT 1.0 / (CASE WHEN
    (SELECT COUNT(*) FROM base) = (SELECT COUNT(*) FROM base JOIN dim ON <key>)
  THEN 1 ELSE 0 END)
  ```
- **The grain is what the ledger says** — read the row count with `--with-output` and
  confirm it matches the period × grain the panel draws (12 rows for 12 months, not 365).

⚠️ Probes are **throwaway scaffolding** — `hex cell delete <cell_id>` them before handoff.

## 5. 🚨 The mock-constant sweep (unique to this skill — do not skip)

The check that catches this migration's signature failure. Run it **every time**, on both
the SQL and the app code.

1. **Pick the distinctive values** — ~10 from the artifact: an odd revenue figure, a
   placeholder entity name ("Acme Corp", "Product A"), a suspiciously round total, a
   percentage.
2. **Export and grep:**
   ```bash
   hex project export <project_id> -o app.yaml
   grep -niE '1240000|1\.24M|Acme|Product A|<other distinctive values>' app.yaml
   ```
3. **Sweep structurally** for the shapes that smuggle constants in even when the exact
   digits changed:
   ```bash
   grep -niE 'VALUES *\(|UNION ALL|CASE WHEN .* THEN [0-9]|pd\.DataFrame\(\[|SELECT .* AS .*, *[0-9]{4,}' app.yaml
   ```
4. **Check the app code specifically** — `genAppFiles` in the export, for literal data
   arrays. A generative app handed the artifact source will happily copy its arrays.
5. **Walk the panels** — each displays a value from a gated cell or a Stub empty state.
   **A number with no cell behind it is a gate failure**, not a cosmetic issue.

Any hit is a **finding until explained** (a legitimate `CASE` for bucketing is fine; a
`CASE` that reproduces the mockup's values is not). Record the sweep result in the manifest
`gate`.

---

## Gate outcome

- **Pass** — ledger complete, independent re-derivation shows no divergence, checklist
  clean, probes COMPLETED, **mock sweep clean**, every panel traces to a gated cell or a
  Stub. Proceed.
- **Fail** — any divergence, a probe ERRORED, or **any unexplained mock-constant hit**. Fix,
  re-run the oracle, re-run the gate for the affected cluster. Don't build on unreviewed
  SQL, and never ship on an unexplained sweep hit.
- **Deferred (🐍/⚠️)** — recorded in the ledger + migration notes as a known gap; not a
  blocker.

**In batch mode** this runs per artifact in Phase 2 (sequential) — record the gate result in
the manifest `gate`/`notes`. The independent-review subagent is safe to spawn per artifact;
keep the human visual-QA confirm in the main thread (Phase 3).
