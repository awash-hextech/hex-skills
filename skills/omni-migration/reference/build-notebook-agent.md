# Build via Hex's notebook agent — brief + handoff mechanics

The **shared mechanics** for both build paths: how to write the **migration brief**,
inject it, hand the work to Hex's in-product notebook agent (`hex thread`), and iterate.
The path-specific parts — the prompt that fixes the app *form*, the "did it build the
right form?" check, and the path's verification gates — live in
[`build-classic-app.md`](build-classic-app.md) and
[`build-generative-app.md`](build-generative-app.md). Use this doc once you've parsed the
dashboard (Phase 1) and chosen its build path (SKILL.md step 4).

## Why the notebook agent is the better builder here

This coding agent (the one reading this skill) is **blind to the things that make the
SQL correct and the dashboard usable**:

- It **cannot see the warehouse** — not the live schema, column types, or the data. It
  infers them from the Omni model YAML + a few probes.
- It **cannot see the customer's Hex context** — Context Studio descriptions,
  endorsed tables, semantic models, existing guides, prior projects.
- It **cannot see the rendered result** — every chart is built blind.

The **notebook agent has all three**. It runs inside the workspace, reads the live
schema and the curated context, writes correct dialect SQL against tables it can
actually inspect, and iterates against what it renders. So the division of labor is:

> **This coding agent owns *understanding the Omni source* (compiling each tile's
> semantic query into the SQL it means) and *verifying the result*. The notebook agent
> owns *building it in Hex*.** Accuracy is guaranteed by the fidelity gate (which reviews
> whoever's SQL — see [`sql-review.md`](sql-review.md)), not by this agent hand-writing
> every query.

The cost is Hex credits.

## Two ways to author the SQL layer

The presentation differs by path (native cells vs. a generative app); underneath, both
paths sit on **native, gated SQL cells**. These two options differ only in **who first
authors those SQL cells**:

- **Agent-built SQL (default for simple dashboards).** You write the brief — including
  the **compiled SQL intent** for each tile cluster (see below) — and the notebook agent
  builds the SQL cells, the parameters, and the presentation. You run the fidelity gate
  **post-hoc** on the SQL it built.
- **Pre-built SQL (default when the model is non-trivial).** You build + gate the SQL
  cells first (YAML round-trip; `hex cell create` can't mint INPUT or dataframe-SQL
  companion cells), then the agent builds the presentation on top. **Lean on this more
  than you would for Mode.** Omni tiles carry no SQL — the SQL only exists after the
  model is compiled — so the joins, fan-out handling, topic-level `always_where`
  filters, and measure definitions are exactly the kind of subtle population logic you
  want pinned and **result-parity-checked against Omni** *before* any chart work.
  And it's cheap: `omni_fetch.py` already saved **Omni's own generated SQL** per tile
  (`sql/*.sql`), so pre-building is often *take Omni's SQL for the cluster, swap its
  literal filter values for Hex params, validate it runs, tie it to Omni's results.*
  Escalate to pre-built whenever a topic joins a one-to-many relationship, a measure
  is a custom-SQL / filtered measure, or the dashboard uses Excel-style calculations.

Either way, tell the agent the presentation must **read those SQL dataframes**, and to
**consolidate** (one SQL cell feeding several tiles) rather than write one
pre-aggregated query per tile.

---

## Writing the migration brief

The brief is a **markdown cell in the project** — persistent, re-readable by the agent
across `continue` turns, and visible to the customer. It carries everything the agent
needs and can't get from this skill. It is the skill's real deliverable: **a faithful,
precise transcription of the Omni dashboard.**

### Describe *intent* — and give the compiled model logic as facts

⚠️ The agent can see the warehouse; you can't. So on the agent-built path, describe
**what each tile query means** and let the agent implement it against the schema it can
see. But unlike Mode — where the source SQL was right there — **the meaning of an Omni
tile lives in the model**, which the notebook agent *can't* read. So the brief must
carry the model logic the tile depends on, resolved:

> *"These are the data derivations behind the Omni dashboard and what each represents.
> Omni defines them in a semantic model you can't see, so the joins, measure
> definitions, and always-on filters are spelled out below as facts. Use your judgment
> and the warehouse schema you can see to build them correctly."*

Include Omni's own generated SQL for each tile (`omni_exports/<dash>/sql/*.sql` — see
[`omni-semantics.md`](omni-semantics.md) §Getting the SQL) in a `{% raw %}`-wrapped
reference cell as *"the exact SQL Omni ran for this tile; reproduce its meaning."* On the
same warehouse it's directly runnable — the agent's job is consolidation and
parameterization, not re-inventing the joins.

### What the brief must contain

Enumerate everything — the agent builds only what you name, so a missed tile is a
missed chart.

1. **What the dashboard is + who it's for** — one or two sentences of purpose.
2. **Data source** — the resolved Hex connection, database/schema, the base tables per
   **topic**, and every **join** (keys, `relationship_type`, join type) the tiles
   traverse, stated as facts for the agent to confirm. **State same-warehouse-or-not.**
3. **Model logic the tiles depend on** — for every field a tile uses: the dimension's
   SQL expression and the measure's aggregation (incl. `count_distinct`, filtered
   measures, custom-SQL measures), with `${view.field}` references **resolved** to
   columns. Note fan-out: *"`order_items` → `users` is many-to-one; `users` →
   `orders` is one-to-many — aggregate `users` measures before joining or use
   COUNT DISTINCT on the key."*
4. **Shared filters / population** — topic `always_where` filters, default topic
   filters, and every **dashboard filter** that applies to all tiles on a query,
   described as intent. Flag relative-date windows, the **query timezone**, week start
   day, and off-by-one risk.
5. **Parameters + scope** — for each dashboard filter/control: control type, default,
   options, and **which tiles it affects** (Omni filters map to specific fields per
   tile; some tiles opt out). Population filters belong in the shared `WHERE`;
   tile-scoped ones attach to their cells. Note the Hex **auto-quoting** rule (bare
   `{{ param }}`, no quotes).
6. **The derivations needed** — each tile's query as **intent + its resolved fields,
   filters, sorts, pivots, limit, and totals**, clustered into shared SQL cells. Flag
   Excel-style **calculations** (post-query formulas) and say how each is reproduced
   (SQL window function, companion query, or Python 🐍). Reuse the status legend
   (✅/🔸/🐍/⚠️) from [`omni-semantics.md`](omni-semantics.md).
7. **The tiles** — one line per tile: title (exact), chart type, x / y + aggregation,
   color/series, sort, number format, which derivation it reads. **Classic path:** also
   name the **Hex cell type** it becomes (EXPLORE variant, METRIC, `pivot-table`,
   markdown, Python 🐍) and mark any **ratio of aggregates** that must be pre-computed
   in SQL.
8. **Layout** — the dashboard's grid, row by row, with **each tile's width as a share of
   the row** (Omni's 24-column grid → Hex's 0–120 app grid, ×5, on the classic path;
   proportions on the generative path). Multiple Omni pages → Hex tabs. The Omni source-reference cells and raw SQL cells stay **out** of
   the app.
9. **Styling** — per-series colors as hex codes (from the vis config and the export's
   `colorPalettes`), number/date formats, KPI/single-value tiles, markdown tile content.
10. **Gaps** — Mustache-templated markdown tiles, custom Vega-Lite vis, maps, spreadsheet
    tiles / file uploads, access filters / user attributes, AI-generated tiles: name
    them (🐍/⚠️) **with the agreed substitute** so the agent doesn't silently invent one.

Keep it tight — intent, not prose. A dashboard's worth of brief is a page or two.

---

## The handoff

1. **Inject the brief** as a markdown cell (`hex cell create -t markdown -l "Migration brief"`).
   ⚠️ **Wrap the brief body in `{% raw %}` … `{% endraw %}`** — and the styling spec, and
   any injected Omni reference (export JSON, model YAML, generated SQL). Hex markdown
   cells Jinja-render `{{ }}`; Omni model YAML is full of `${view.field}` (harmless) but
   markdown tiles use **Mustache `{{ }}`** and the brief will quote Hex Jinja params —
   an unwrapped cell can ERROR the whole `hex project run`. See [`gotchas.md`](gotchas.md).
   When the **agent builds the SQL**, attach the data connection to the project (a
   one-line seed SQL cell via `hex cell create --data-connection-id …` does this).
2. **Start the thread with the path's prompt.** App form is controlled by **prompt
   wording alone** — there is no CLI flag:
   - **Classic** → prescriptive about native cell types, ends with *"Do NOT build a
     Generative app."* Template → [`build-classic-app.md`](build-classic-app.md).
   - **Generative** → the prompt **opens** with *"Build this as a GENERATIVE APP (App
     builder → Generative app), not a classic notebook app."* Template →
     [`build-generative-app.md`](build-generative-app.md).
   - Pre-built SQL: add *"the SQL cells already exist — use them as the data source,
     don't rewrite them."*
3. **⚠️ Surface the live URL to the customer immediately.** `hex thread create --json`
   returns a `url`. Give it to them **as the build starts** so they can watch the agent
   work and stop/redirect it if it drifts. Don't poll silently.
4. **Verify the form** after the build (`hex project export` → `genAppFiles` **empty**
   for classic, **non-empty** for generative) and re-prompt if it built the wrong one.
5. **Poll** `hex thread get <id>` until `Status: IDLE`; iterate with
   `hex thread continue <id> "<fix>"`.

## Verify + gate (always)

The build is not done until it's gated. The notebook agent is capable but still a black
box that can be confidently wrong — **verify, don't trust.**

- **Confirm what it built** — `hex project export`: right form for the chosen path, SQL
  cells present + (pre-built) unchanged, presentation bound to the right dataframes,
  params wired **upstream** of their consumers, SQL **consolidated**.
- **Run the SQL-fidelity gate** — ledger, independent re-derivation from the export +
  model, mistake-class checklist, and the **result-parity check against Omni's own query
  results** → [`sql-review.md`](sql-review.md).
- **Classic path only: run the cell-spec diff** on the viz cells →
  [`build-classic-app.md`](build-classic-app.md).
- **Verify the render with the visual-QA loop** →
  [`visual-qa-loop.md`](visual-qa-loop.md).
- **Fix divergences** — `hex thread continue <id> "<name the exact divergence>"`, or edit
  the cell directly when a surgical fix is faster.

## Cheat-sheet

- `hex thread create "<prompt>" --project <id> --json` → `url` (hand to customer) + `thread_id`.
- `hex thread get <id>` → `Status: RUNNING｜IDLE`; `hex thread messages <id>` → its reasoning.
- `hex thread continue <id> "<prompt>"` → iterate.
- Needs the headless-agent-threads feature enabled for the workspace. Uses Hex credits.
