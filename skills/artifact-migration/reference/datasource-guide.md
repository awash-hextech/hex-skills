# Author a Hex guide for the grounded data source

A migration should ship more than a dashboard — it should hand the customer a **governed
semantic layer** so their team can self-serve trustworthy answers in Hex Threads / the
notebook agent. Guides are authorable headlessly via the CLI, so this fits the pipeline.

> **Where the content comes from here.** Tableau gives you a published datasource; Mode
> gives you Definitions. An artifact gives you **neither** — but it gives you something the
> BI sources don't: the **grounding ledger you just built**, which is a freshly-negotiated,
> customer-confirmed mapping from business concepts to real warehouse columns. That's
> exactly a semantic layer's raw material, and writing it down is how the grounding work
> stops being a one-off.

## When to author (once per data source, not per artifact)

A guide is **per domain / data source**. Several migrated artifacts usually land on one
data source → author **one** guide and let every migrated app's questions retrieve it.
Author (or refresh) it the first time you migrate onto a given data source; later artifacts
top it up rather than duplicating.

## What goes in it — and what stays out

Keep it tight (~150 lines / ~350 words). A guide describes **when/how** to use the data,
not **what each column is**.

| Guide section | Source in the migration |
|---|---|
| **Canonical Metrics** | Each **Ground** row's metric: its warehouse-SQL definition, source table, and the trap to avoid. Only *business* metrics (ratios, windowed measures, relative-date-bound measures), not every field. |
| **Join Patterns** | The join shapes the derivations needed — the required key per table pair, and what *not* to join on (fan-out risk). |
| **Source of Record** | The warehouse table(s) the grounding settled on; which to prefer when there were candidates. |
| **Risk Areas** | ⚠️ **The highest-value section in this skill** — see below. |
| **Example Questions** | 2–3 questions the migrated app answers, in the user's own words (drives retrieval). |

**Keep OUT** (each has a better home): field-by-field column meanings → **warehouse
descriptions**; which tables are golden → **endorsements**; the SQL of every individual
panel → the project itself.

### ⚠️ Risk Areas — record what grounding exposed

The grounding gate surfaces things nobody had written down. This is where they go:

- **Metrics the artifact showed that don't exist in the warehouse** (the ⚠️ **Drop** rows).
  Name them: *"`health_score` appeared in the source design but has no definition or source
  — don't invent one."* Without this, the next person re-invents it.
- **Concepts whose definition had to be negotiated** — the metric everyone assumed was
  obvious until this migration asked. Record the definition that was agreed and who agreed
  it.
- **Grain mismatches** — where the business asks daily and the table only supports monthly.
- **Stubbed panels** — what's waiting on a source, so it isn't mistaken for broken.
- The usual correctness traps: relative-date windows, a param's real scope, ratio-of-
  aggregates, `COUNT` vs `COUNTD`, date columns stored as strings upstream.

## Template

```markdown
---
name: <Subject> Metrics
description: How <subject> metrics (<metric a>, <metric b>, …) are defined and
  joined. Use for questions about <terms users actually type>. Established while
  migrating the "<artifact title>" Claude artifact into Hex.
---

# Canonical Metrics
- **<Metric>** = `<warehouse SQL>` — from `<schema.table>`. <the trap, e.g. "count
  distinct accounts, not rows", "revenue is non-additive across the region join">.

# Join Patterns
- `<table_a>` → `<table_b>` on `<key>` (many-to-one). Never join on `<x>` — fans out.

# Source of Record
- `<schema.table>` is authoritative for <subject>. Prefer it over `<alt>` because <reason>.

# Risk Areas
- **<Concept> has no source.** It appeared in the migrated design; there is no warehouse
  definition. Do not improvise one.
- **<Metric> definition** was agreed as `<definition>` during migration (<who/when>).
- **<Grain note>** — the table supports <grain>; requests for <finer grain> can't be met.
- <relative-date window / param scope / ratio-of-aggregates trap>

# Example Questions
- "<question a user would actually type>"
- "<another>"
```

## Publish

```bash
hex guide preview <guide>.md      # → preview_id
hex guide publish <preview_id>
```

Markdown only. Refresh the guide as later artifacts add metrics to the same data source
rather than publishing a second guide for the same domain.
