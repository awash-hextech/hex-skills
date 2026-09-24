# Build via Hex's notebook agent — brief + handoff mechanics

The **shared mechanics** for the default build: how to write the **migration brief**,
inject it, hand the work to Hex's in-product notebook agent (`hex thread`), and iterate.
The default deliverable is a **Generative app** — the app-specific prompt, the
`genAppFiles` verification and the styling spec live in
[`build-generative-app.md`](build-generative-app.md). Use this doc once you've read the
artifact **and cleared the grounding gate**.

## Why the notebook agent is the better builder here

This coding agent is **blind to the things that make the build correct**:

- It **cannot see the warehouse** — not the live schema, column types, or the data.
- It **cannot see the customer's Hex context** — Context Studio descriptions, endorsed
  tables, semantic models, existing guides, prior projects.
- It **cannot see the rendered result** — every chart is built blind.

The **notebook agent has all three**. So the division of labor is:

> **This coding agent owns *understanding the artifact*, *grounding its data*, and
> *verifying the result*. The notebook agent owns *building it in Hex*.**

The cost is Hex credits.

## Two ways to author the SQL layer

The presentation is always a Generative app; these differ only in **who first authors the
native SQL cells underneath it** (both end gated the same way):

- **Pre-built SQL (the common path *here*).** You build + gate the SQL cells first, then
  the agent builds the app on top. ⚠️ **Default to this whenever the grounding ledger has
  🎭 rows** — when the SQL is being written for the first time there's no source query for
  a post-hoc diff to lean on, so pin the numbers *before* any app work. It costs a YAML
  round-trip (`hex cell create` can't mint INPUT or dataframe-SQL companion cells).
- **Agent-built SQL.** You write the brief; the agent builds the SQL cells, the parameters
  and the app; you gate **post-hoc**. Reserve this for ledgers that are all 📋/🗄️ — real
  data with a known source and a concrete table mapping to diff against.

> This is the **inverse** of the Tableau/Mode default, and deliberately so: those skills
> port an existing query, this one usually authors one.

---

## Writing the migration brief

The brief is a **markdown cell in the project** — persistent, re-readable by the agent
across `continue` turns, and visible to the customer. It carries everything the agent needs
and can't get from this skill (which it can't read). It is the skill's real deliverable:
**a faithful transcription of the artifact's design, on top of a grounded data layer.**

### Describe *intent*, not literal SQL — and ⚠️ never the mock values

Two rules, and the second is the one unique to this skill:

1. **Don't paste finished SQL for the agent to copy** (agent-built path). It can see the
   warehouse schema and the customer's context; you can't. Describe **what each derivation
   is meant to represent** and let it implement against the schema it sees.
   > Frame it in the brief: *"These are the data derivations this app needs and what each
   > is meant to represent. Use your judgment and the warehouse schema + workspace context
   > you can see to build them correctly."*

2. **⚠️ Never put the artifact's numbers in the brief as targets.** Given *"Q3 revenue
   should be $1.24M"* the agent will **make that true** — a `CASE` ladder, a `VALUES` list,
   a filter tuned until it matches. Carry **shape + intent + the table/column mapping**;
   carry **zero mock values**. Full anti-pattern →
   [`data-grounding.md`](data-grounding.md) §5.

### What the brief must contain

Enumerate everything — the agent builds only what you name, so a missed panel is a missed
chart.

1. **What the artifact is + who it's for** — one or two sentences of purpose.
2. **Data source** — the resolved connection, database/schema, tables and the **join**
   (keys + expected cardinality), stated as facts for the agent to confirm.
3. **⚠️ The grounding ledger, in full** — per data shape: its role on the page, the
   **target table + column mapping**, the grain, the population filters, and its
   **disposition** (Ground / Drop / Stub). **Say plainly that the artifact source cell's
   numbers are placeholders and must not be reproduced.** This section is the brief's
   center of gravity here — it replaces the "translate the source query" section the BI
   skills have.
4. **Shared filters / population** — every filter that applies across panels, as intent.
   Flag relative-date windows and off-by-one risk.
5. **Parameters + scope** — per control: type, default, domain/options, and **which panels
   it affects**. Note the Hex **auto-quoting** rule (bare `{{ param }}`, no quotes).
6. **The derivations needed** — each as **intent + which panels read it**, with the status
   legend (✅/🔸/🐍/⚠️) from [`artifact-semantics.md`](artifact-semantics.md).
7. **Derived logic that must live in SQL** — the client-side JS that changes numbers
   (aggregates, window functions, ratios as `SUM(a)/SUM(b)`).
   → [`artifact-semantics.md`](artifact-semantics.md) §6.
8. **The panels** — one line each: title (exact), chart type, x / y + aggregation,
   color/series, sort, number format, and which derivation it reads. (Big numbers → a
   1-row derivation.)
9. **Layout** — the artifact's section-by-section structure.
10. **Styling** — the `:root` hex codes (light **and** dark), fonts, number/date formats.
11. **Gaps** — capabilities with no Hex equivalent (ask-Claude in-page, viewer identity,
    file uploads), bespoke D3/SVG visuals, and every **Drop** and **Stub**, so the agent
    doesn't silently approximate them.

Keep it tight — intent, not prose. An artifact's worth of brief is a page or two.

---

## The handoff

1. **Inject the brief** as a markdown cell
   (`hex cell create -t markdown -l "Migration brief"`), plus the **styling spec** and the
   **artifact source** as separate reference cells.
   - ⚠️ **Wrap every injected body in `{% raw %}` … `{% endraw %}`.** Hex markdown cells
     Jinja-render `{{ }}`, and artifact source is saturated with JSX/template braces
     (`{{ }}`, `${...}`) — an unwrapped cell ERRORs the whole `hex project run` even though
     every SQL cell is fine. → [`gotchas.md`](gotchas.md).
   - ⚠️ **Label the artifact-source cell explicitly**: *"Reference only — layout and
     styling. Every number here is a placeholder; do NOT reproduce these values."*
   - Large artifacts may exceed one cell — split by section, or inject a trimmed source
     (structure + styling + chart configs, minus vendored libraries).
   - When the **agent builds the SQL**, attach the data connection to the project (a
     one-line seed SQL cell via `hex cell create --data-connection-id …` does this). When
     you **pre-built the SQL**, the gated cells are already there.
2. **Start the thread with the generative-app prompt.** It **must open** with *"Build this
   as a GENERATIVE APP (App builder → Generative app), not a classic notebook"* and must
   repeat the placeholder warning. Full template →
   [`build-generative-app.md`](build-generative-app.md). (Pre-built SQL: add *"the SQL
   cells already exist — use them as the data source, don't rewrite them."*)
3. **⚠️ Surface the live URL to the customer immediately.** `hex thread create --json`
   returns a `url`. Give it to them **as the build starts** so they can watch the agent
   work and stop/redirect it if it drifts. Don't poll silently.
4. **Prompt framing decides the output *form* — there's no CLI flag.** Always **verify the
   form** after the build (`hex project export` → `genAppFiles` non-empty) and re-prompt if
   it built classic.
5. **Poll** `hex thread get <id>` until `Status: IDLE`; iterate with
   `hex thread continue <id> "<fix>"`.

## Verify + gate (always)

The build is not done until it's gated. The notebook agent is capable but still a black box
that can be confidently wrong — **verify, don't trust.**

- **Confirm what it built** — `hex project export`: `genAppFiles` non-empty, SQL cells
  present + (pre-built) unchanged, the app reads the right dataframes, params wired, and
  **no data arrays embedded in the app code**.
- **Run the grounding verification** — mock-constant sweep + every panel traces to a gated
  cell. → [`data-grounding.md`](data-grounding.md) §7.
- **Run the SQL-fidelity gate** — read every SQL cell's values
  (`hex cell run <id> --with-output`), diff against the grounding ledger + your independent
  re-derivation, run the checklist and probes. → [`sql-review.md`](sql-review.md).
- **Fix divergences** — `hex thread continue <id> "<name the exact divergence>"`, or edit
  the cell directly when a surgical fix is faster.
- **Verify the render with the visual-QA loop** → [`visual-qa-loop.md`](visual-qa-loop.md).

## Cheat-sheet

- `hex thread create "<prompt>" --project <id> --json` → `url` (hand to customer) + `thread_id`.
- `hex thread get <id>` → `Status: RUNNING｜IDLE`; `hex thread messages <id>` → its reasoning.
- `hex thread continue <id> "<prompt>"` → iterate.
- ⚠️ Brief carries shape + mapping, **never mock values**; source cell labeled "placeholders".
- ⚠️ Pre-built SQL is the default here, not the exception.
- Needs the headless-agent-threads feature enabled. Uses Hex credits.
