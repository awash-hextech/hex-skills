# Build via Hex's notebook agent — brief + handoff mechanics

The **shared mechanics** for the default build: how to write the **migration brief**,
inject it, hand the work to Hex's in-product notebook agent (`hex thread`), and
iterate. The default deliverable is a **Generative app** — this doc covers the brief
and the thread; the app-specific prompt, the `genAppFiles` verification, and the
styling spec live in [`build-generative-app.md`](build-generative-app.md). Use this
doc once you've parsed the report (Phase 1).

## Why the notebook agent is the better builder here

This coding agent (the one reading this skill) is **blind to the things that make the
SQL correct and the dashboard usable**:

- It **cannot see the warehouse** — not the live schema, column types, or the data. It
  infers them from the Mode export + a few probes.
- It **cannot see the customer's Hex context** — Context Studio descriptions,
  endorsed/undorsed tables, semantic models, existing guides, prior projects.
- It **cannot see the rendered result** — every chart is built blind.

The **notebook agent has all three**. It runs inside the workspace, reads the live
schema and the curated context, writes correct dialect SQL against tables it can
actually inspect, and iterates against what it renders. For building *in Hex*, it is
simply better-equipped than this agent. So the division of labor is:

> **This coding agent owns *understanding the Mode source* and *verifying the
> result*. The notebook agent owns *building it in Hex*.** Accuracy is guaranteed by
> the fidelity gate (which reviews whoever's SQL — see
> [`sql-review.md`](sql-review.md)), not by this agent hand-writing every query.

The cost is Hex credits.

## Two ways to author the SQL layer

The presentation is always a Generative app; these differ only in **who first authors
the native SQL cells underneath it** (both end gated the same way):

- **Agent-built SQL (default).** You write the brief; the notebook agent builds the
  **SQL cells, the parameters, and the app**. You then run the fidelity gate
  **post-hoc** on the SQL it built (read its values, diff against the Mode query).
  Simplest, and it leans fully on the agent's schema + context sight.
- **Pre-built SQL.** You build + gate the SQL cells first, then the agent builds the app
  on top of them. Choose this when the **data population is subtle** (a `{% form %}`
  param that rewrites the `WHERE`, a definition that hides a join, a relative-date
  window) and you want the numbers pinned and gated *before* any app work. It costs a
  YAML round-trip (`hex cell create` can't mint INPUT or dataframe-SQL companion cells).
  **Because Mode SQL is already the warehouse dialect (when the connection is
  unchanged), pre-building here is cheap** — often just *paste the query, swap the Liquid
  for Hex params, validate it runs.* Lean on it more readily than you would for Tableau.

When unsure, default to **agent-built** and rely on the post-hoc gate; escalate to
**pre-built** for high-stakes or subtle-population reports. Either way, tell the agent to
build a Generative app that *reads* the SQL dataframes and never re-queries
([`build-generative-app.md`](build-generative-app.md)).

---

## Writing the migration brief

The brief is a **markdown cell in the project** — persistent, re-readable by the agent
across `continue` turns, and visible to the customer. It carries everything the agent
needs and can't get from this skill (which it can't read). It is the skill's real
deliverable: **a faithful, precise transcription of the Mode report.**

### Describe *intent*, not literal SQL

⚠️ **Do not paste finished SQL for the agent to copy** *(when the warehouse is
unchanged and you're pre-building, the Mode query text IS the SQL — that's a different
path; see below).* For the **agent-built** path, the agent can see the warehouse schema
and the customer's context; you can't. If you dictate exact SQL, you throw away its
biggest advantage and re-introduce your blind spots. Instead, describe **what each query
is meant to represent** and let the agent implement it against the schema it can see.

> Frame it explicitly in the brief: *"These are the SQL derivations of the Mode report
> and what each is meant to represent. Use your judgment and the warehouse schema +
> workspace context you can see to build them correctly."*

> **Mode nuance:** the Mode query text is a *strong reference* even on the agent-built
> path — include it (in a `{% raw %}`-wrapped reference cell) as "this is the exact SQL
> the report ran; reproduce its meaning against the live schema" and name any Liquid it
> carries. Same-warehouse migrations can legitimately reproduce it near-verbatim; that's
> the anchor Tableau never gave you. Still describe **intent** so the agent can adapt
> types/columns it can see and you can verify against meaning, not just text.

### What the brief must contain

Enumerate everything — the agent builds only what you name, so a missed query is a
missed chart.

1. **What the report is + who it's for** — one or two sentences of purpose.
2. **Data source** — the resolved connection, database/schema, tables, and the **join**
   (keys + expected cardinality), stated as facts for the agent to confirm. **State
   same-warehouse-or-not** so the agent knows whether the source SQL is copy-paste or a
   dialect port.
3. **Shared filters / population** — every filter that applies to all charts on a query,
   described as intent, including any **data-population parameter** that rewrites the
   `WHERE`. Flag relative-date windows and off-by-one risk.
4. **Parameters + scope** — for each `{% form %}` field: control type, default,
   domain/options, and **which cells it affects** (all charts on a query vs. named ones).
   Data-population params belong in the shared filter; chart-scoped params attach to
   their cells. Note the Hex **auto-quoting** rule (bare `{{ param }}`, no quotes).
5. **The queries / derivations needed** — each Mode query as **intent + the query it came
   from**, plus its resolved **definitions** (inlined CTEs) and any **dataset**
   dependency. Flag `{% if %}` branches. Reuse the status legend (✅/🔸/🐍/⚠️) from
   [`mode-semantics.md`](mode-semantics.md).
6. **The charts** — one line per chart: title (exact), chart type, x / y + aggregation,
   color/series, sort, number format, and which query/derivation it reads. (Big numbers →
   METRIC.)
7. **Notebook logic** — any Python/R notebook cells, described as intent + which dataframe
   they read (🐍); note anything R-only or externally-dependent.
8. **Layout** — the row-by-row order the report assembles into (Report Builder rows, or
   the HTML report's structure).
9. **Styling** — colors per series + number/date formats (high-value fidelity); leave
   cosmetic-only knobs to Hex defaults.
10. **Gaps** — bespoke D3/JS, R-only logic, non-warehouse sources, maps: name them as
    known gaps (🐍/⚠️) so the agent doesn't silently approximate them.

Keep it tight — intent, not prose. A report's worth of brief is a page or two.

---

## The handoff

1. **Inject the brief** as a markdown cell (`hex cell create -t markdown -l "Migration brief"`).
   ⚠️ **Wrap the brief body in `{% raw %}` … `{% endraw %}`** — and the styling spec, and
   any injected Mode query reference. Hex markdown cells Jinja-render `{{ }}`, and a Mode
   brief/reference is *saturated* with `{{ @param }}` and `{% form %}` / `{% if %}` tokens
   — an unwrapped cell ERRORs the whole `hex project run` even though every SQL cell is
   fine. `{% raw %}` tells Jinja to skip the block; the markdown still renders. See
   [`gotchas.md`](gotchas.md).
   When the **agent builds the SQL**, attach the data connection to the project (a
   one-line seed SQL cell via `hex cell create --data-connection-id …` does this). When
   you **pre-built the SQL**, the QA'd cells are already there.
2. **Start the thread with the generative-app prompt.** It **must open** with *"Build this
   as a GENERATIVE APP (App builder → Generative app), not a classic notebook"* and tell
   the agent to build the SQL derivations + params, then a Generative app that *reads
   those dataframes* (never re-queries), matching the styling spec. Full prompt template →
   [`build-generative-app.md`](build-generative-app.md). (Pre-built SQL: add *"the SQL
   cells already exist — use them as the data source, don't rewrite them."*)
3. **⚠️ Surface the live URL to the customer immediately.** `hex thread create --json`
   returns a `url`. Give it to them **as the build starts** so they can *watch the agent
   work in real time and stop/redirect it* if it drifts. Don't poll silently.
4. **Prompt framing decides the output *form* — there's no CLI flag.** Always **verify the
   form** after the build (`hex project export` → is `genAppFiles` non-empty?) and
   re-prompt if it built classic.
5. **Poll** `hex thread get <id>` until `Status: IDLE`; iterate with `hex thread continue
   <id> "<fix>"`.

## Verify + gate (always)

The build is not done until it's gated. The notebook agent is capable but still a black
box that can be confidently wrong — **verify, don't trust.**

- **Confirm what it built** — `hex project export`: `genAppFiles` non-empty, SQL cells
  present + (pre-built) unchanged, the app reads the right dataframes, params wired.
- **Run the SQL-fidelity gate on the SQL** — read every SQL cell's values with `hex cell
  run <id> --with-output`, diff the SQL against the Mode query + your re-derivation, run
  the mistake-class checklist + differential probes. Full procedure →
  [`sql-review.md`](sql-review.md). The gate reviews *whoever* wrote the SQL — post-hoc on
  the agent's cells is a first-class use.
- **Fix divergences** — either `hex thread continue <id> "<name the exact divergence>"`,
  or edit the cell directly when a surgical fix is faster.
- **Verify the render with the visual-QA loop** — headless screenshot → panel-by-panel
  diff vs. the source Mode PNG → surgical fix batch → repeat, then a final human confirm.
  → [`visual-qa-loop.md`](visual-qa-loop.md).

## Cheat-sheet

- `hex thread create "<prompt>" --project <id> --json` → `url` (hand to customer) + `thread_id`.
- `hex thread get <id>` → `Status: RUNNING｜IDLE`; `hex thread messages <id>` → its reasoning.
- `hex thread continue <id> "<prompt>"` → iterate.
- Needs the headless-agent-threads feature enabled for the workspace. Uses Hex credits.
