# Author a Hex guide for the migrated data source

A migration should ship more than dashboards — it should hand the customer a **governed
semantic layer** so their team can self-serve trustworthy answers in Hex Threads / the
Notebook Agent. Mode already carries a *de facto* semantic layer in its **Definitions**
(reusable SQL snippets for canonical metrics) and in the recurring join/filter patterns
across a data source's queries. Mirror it as a **Hex guide**: a retrieved, per-domain
context asset the agent pulls in when a question matches.

Guides are authorable headlessly via the CLI, so this fits the pipeline.

## When to author (once per data source, not per report)

A Hex guide is **per domain / data source**, not per report. Many Mode reports share one
data source → author **one** guide and let every migrated report's questions retrieve it.
Author (or refresh) it the first time you migrate a report on a given data source; on
later reports, top it up rather than duplicating.

## What goes in it — and what stays out

Keep it tight (~150 lines / ~350 words). A guide describes **when/how** to use the data,
not **what each column is**. Pull the content straight from the Phase-1 parse (see
[`mode-semantics.md`](mode-semantics.md)):

| Guide section | Source in the Mode workspace |
|---|---|
| **Canonical Metrics** | Mode **Definitions** + repeated metric SQL across queries — each with its warehouse-SQL definition, source table, and the trap to avoid. Include only the *business* metrics (ratios, windowed measures, relative-date-bound measures), not every field. |
| **Join Patterns** | The join shapes that recur across the data source's queries — the required key per table pair, and what *not* to join on (fan-out risk). |
| **Source of Record** | The primary warehouse table(s) the data source sits on; which to prefer. |
| **Risk Areas** | Migration gotchas that affect correctness — the relative-date window, a `{% form %}` param's real scope, a definition that hides a join, dialect drift (if the warehouse changed), any renamed/deprecated fields. |
| **Example Questions** | 2–3 questions the migrated reports answer, in the user's own words (drives retrieval). |

**Keep OUT** (each has a better home — see the `hex-context-best-practices` skill):
field-by-field column meanings → **warehouse descriptions**; which tables are golden →
**endorsements**; the SQL of every individual chart → the project itself.

## Template

```markdown
---
name: <Data source subject> Metrics
description: How <subject> metrics (<metric a>, <metric b>, …) are defined and
  joined. Use for questions about <terms users actually type>. Migrated from
  Mode data source "<name>".
---

# Canonical Metrics
- **<Metric>** = `<warehouse SQL>` — from `<schema.table>`. <the trap, e.g.
  "count active only", "revenue is non-additive across the region join">.
  <If it came from a Mode Definition, note the definition name.>

# Join Patterns
- `<fact>` → `<dim>` on `<key>` (many-to-one). Never join on `<bad key>` (fans out).

# Source of Record
- Base table(s): `<schema.table>`. Prefer `<x>` over `<y>` for <reason>.

# Risk Areas
- <named gotcha> — why it bites + the correct behavior (e.g. "the `date_range`
  form param defaults to last 90 days, not all-time — reports assume the default").

# Example Questions
- "<a real question the reports answer>"
```

Use enforceable **Always / Never** language, and name each anti-pattern with its reason +
the correct behavior.

## Publish (headless)

```bash
hex guide preview path/to/<datasource>-guide.md    # → returns a preview URL + preview_id
hex guide publish <preview_id>                     # deploy to the workspace
```

Preview first (test the agent's behavior with the new guide), then publish. Guide files
can be version-controlled and re-published as the migration or the data source evolves.

## Compose with the other context assets (optional, higher fidelity)

The guide is the fast, headless win. For a fuller semantic layer — endorsements, warehouse
descriptions, or a YAML semantic model for must-be-exact metrics — use the
**`hex-context-best-practices`** skill. Mode Definitions map especially well to
semantic-model MEASUREs when a metric must be exact. Not required to ship the guide.
