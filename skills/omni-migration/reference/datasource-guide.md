# Carry the Omni semantic model into Hex (guide, optionally a semantic model)

An Omni migration has something Mode and Tableau migrations rarely do: **an explicit,
governed semantic model** (views, dimensions, measures, topics, relationships, all in
YAML). Dashboards are only half the asset. If you port the tiles and drop the model, the
customer loses the definitions their whole team self-served on. So ship the model's
meaning into Hex too, so Threads and the notebook agent answer questions the way Omni
did.

Two levels — do the first on every migration, the second when metrics must be exact:

1. **A Hex guide per topic / domain (always).** Fast, headless, retrieved by the agent
   when a question matches.
2. **A Hex semantic model (optional, higher fidelity).** For must-be-exact metrics, port
   the measures as semantic-model MEASUREs — see the `hex-context-best-practices` skill.
   If the customer already maintains dbt MetricFlow, Omni's own
   `omni-to-dbt-metricflow` skill (exploreomni/omni-agent-skills) can move view and
   relationship logic into MetricFlow YAML as a bridge.

## When to author (once per topic, not per dashboard)

A guide is **per domain**. Omni's natural unit is the **topic** (a base view + its
joins, the thing users pick to start a query). Many dashboards share a topic → author
**one** guide per topic the migrated dashboards use; top it up on later dashboards.

## What goes in it — and what stays out

Keep it tight (~150 lines / ~350 words). A guide says **when/how** to use the data, not
what each column is. Pull it from the model YAML you already parsed
([`omni-semantics.md`](omni-semantics.md)):

| Guide section | Source in the Omni model |
|---|---|
| **Canonical Metrics** | The topic's **measures** the dashboards use — each with its compiled warehouse SQL (`${}` references resolved), source table, and the trap to avoid. Business metrics only (ratios, filtered measures, distinct counts), not every field. |
| **Join Patterns** | The topic's **relationships** — join keys, `relationship_type`, and which joins fan out (one-to-many) and how to aggregate safely across them. |
| **Source of Record** | The views' `table_name` / schema; which base view to start from. |
| **Always-on filters** | The topic's `always_where` / default filters — the population every question should assume unless told otherwise. |
| **Risk Areas** | Fan-out on one-to-many joins, the query timezone, week start day, relative-date semantics, any access filter the model enforced. |
| **Example Questions** | 2–3 questions the migrated dashboards answer, in the users' own words. If the model has AI context (`ai_context`, sample queries), reuse it here. |

**Keep OUT:** field-by-field descriptions → **warehouse descriptions**; which tables are
golden → **endorsements**; the SQL of every tile → the project itself.

## Template

```markdown
---
name: <Topic> Metrics
description: How <topic> metrics (<metric a>, <metric b>, …) are defined and joined.
  Use for questions about <terms users actually type>. Migrated from Omni topic
  "<topic>" (model "<model>").
---

# Canonical Metrics
- **<Metric>** = `<compiled warehouse SQL>` — from `<schema.table>`. <the trap, e.g.
  "count distinct users, not rows", "excludes test accounts via the topic filter">.

# Join Patterns
- `<base view>` → `<view>` on `<key>` (many-to-one). `<view>` → `<view>` is
  one-to-many: aggregate before joining, never SUM across it.

# Always-on filters
- Every question assumes `<always_where condition>` unless the user says otherwise.

# Source of Record
- Base table: `<schema.table>`.

# Risk Areas
- <named gotcha> — why it bites + the correct behavior.

# Example Questions
- "<a real question the dashboards answer>"
```

Use enforceable **Always / Never** language, and name each anti-pattern with its reason.

## Publish (headless)

```bash
hex guide preview path/to/<topic>-guide.md    # → preview URL + preview_id
hex guide publish <preview_id>                # deploy to the workspace
```

Preview first (test the agent with the new guide), then publish. Keep guide files under
version control and re-publish as the model evolves.
