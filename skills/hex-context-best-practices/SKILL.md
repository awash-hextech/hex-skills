---
name: hex-context-best-practices
description: >
  Use this skill whenever someone is setting up, improving, or planning a rollout of agentic
  analytics in Hex — especially Threads, the Notebook Agent, or the Modeling Agent. Triggers on:
  "context strategy", "context engineering", "set up Threads", "workspace guide", "warehouse
  descriptions", "endorse tables", "semantic model", "my agent gave the wrong answer", "roll out
  self-service analytics", "how do I make Hex AI more accurate", "Hex Context Studio". Always use
  this skill for any task about making Hex's agents trustworthy or scaling them to business users —
  even if the request is phrased casually like "help me get my data team using AI" or "why does
  Threads keep picking the wrong table". This skill both advises on strategy AND drafts the actual
  context assets (workspace guides, descriptions, semantic models) and rollout plans.
---

# Hex Context Strategy

Help a data team build a **context strategy** for Hex's agents and roll it out so business users can
self-serve trustworthy answers. This skill does two jobs: (1) advise on and **draft** the four
context assets, and (2) produce a **phased rollout plan** tailored to the team's situation.

The single most important idea: **agents are only as good as the context you give them, and context
compounds.** It does not need to be perfect on day one. Start with what exists, scope to one use
case, and improve every loop.

---

## How to use this skill

This skill has two specialists. Figure out which the person needs and route accordingly. They will
often need both, usually in this order: build context first, then plan the rollout.

| If the person wants to… | Use |
| --- | --- |
| Decide what context to build, write workspace guides / descriptions / semantic models, or fix a wrong agent answer | **`agents/context-architect.md`** |
| Plan how to introduce Threads to their team and scale it in phases | **`agents/rollout-planner.md`** |

**Spawning the specialist:**
- In Claude Code or Codex with subagent support, invoke the matching file in `agents/` as a subagent.
- In Claude.ai or any environment without subagents, just **read the matching `agents/` file inline**
  and follow it. The files are written to work either way.

**Before doing detailed work, gather context about their setup.** Both specialists lean on
`references/intake.md` — a short questionnaire the person can answer (or attach docs to) so the
output fits their actual warehouse, team, and use case. Don't interrogate; ask for what you need,
infer the rest, and note assumptions.

---

**Keep steps current.** Hex's UI changes. Before giving step-by-step instructions, fetch the relevant
page from `references/hex-docs.md` so the steps are accurate.

## The mental model (read this before either specialist)

Hex's agents reference **four categories of context**. Each has one job. The skill of keeping each
category focused on its job is **context engineering**. The categories sit on a spectrum from loose
**guidance** to rigid **governance**:

1. **Endorsed & excluded statuses** — *your warehouse guardrails.* Mark schemas/tables/semantic
   models as Approved/Trusted, or "Exclude from AI" for staging, test, and deprecated data. This is
   the **fastest, highest-leverage** action — it defines the "approved menu" the agent can pull from.
   Pair with **Endorsed Mode** (Settings → AI & agents): when enabled (the default), Explorer users
   are restricted to endorsed assets only in Threads — no toggle, no escape hatch. Recommended for
   self-serve rollouts where you want to guarantee business users only touch vetted data.
2. **Warehouse descriptions** — *the foundational context.* Table and column descriptions. Answers
   "what does this column contain." Fundamental hygiene.
3. **Workspace context & guides** — *teaching the agent your business.* **Workspace context** is one
   file sent with every prompt (global truths); **guides** are a retrieved library, one per domain.
   Both describe *when/how* to use data, not *what* it is. Anything that doesn't fit the other three.
4. **Semantic models** — *the rigid rules.* YAML that codifies how tables join, how measures are
   calculated, what dimensions exist. For metrics that must be 100% correct every time.

**Advanced sources (optional, later-stage):** on Team/Enterprise, two more sources extend the four —
**reference repositories** (connect GitHub/GitLab so the agent reasons over your code: metric logic,
table structures, event logging) and **External Apps / MCP** (let the agent use Notion, Linear, or
custom MCP tools). Surface these only when the person asks about code repos or MCP, already has repos
connected to their AI tooling, or has matured past the basics. They're governed the same way as the
core four — by a clear description. See `references/advanced-context.md`.

**The routing rule that keeps categories clean** (state this whenever someone is unsure where a
piece of context belongs):
- Endorsing specific tables/schemas → endorse them in Hex. Banning bad tables → **exclude from AI**
  (not the workspace context — text bans are unreliable).
- Defining what a column contains → warehouse description (not the workspace context).
- Logic for joining two tables → semantic model if you have one, else warehouse descriptions on the
  joined columns.
- Applies to every question → workspace context. Specific domain/question type → a guide.
- Metric formulas → a guide or semantic model (not the always-on context).

**Where ownership tends to land:** warehouse descriptions and semantic models live closer to the
warehouse (analytics engineering); endorsements and workspace guides live closer to Hex's UI
(analysts/admins). There's no hard rule.

**Observability closes the loop.** Context can't improve without visibility. Hex's **Context Studio**
shows usage/adoption, lets you manage assets, surfaces trending questions and agent responses, and —
via **Suggestions** — auto-generates concrete context fixes from conversation patterns and feedback.
To find what to improve, ask Hex itself (the agent knows your warehouse and context); see
`references/ask-hex.md` for in-product, MCP, and CLI ways to do that. Improvement is never "done" —
frequent at first, tapering over time.

**Prioritization (the 30-minute start):** endorse a few golden tables and exclude junk → add
descriptions to the most-queried endorsed tables/columns → write a workspace guide with 5–10 rules →
add semantic models to codify key metrics. Always scope to a real business use case. Don't boil the
ocean.

---

## Working principles for any output

- **Positive guidance beats prohibitions.** "Always join on `customer_id` in the customer schema"
  works better than "don't use the wrong key."
- **Scope to one use case** = a broad subject with 3–5 concrete business questions. That keeps the
  work measurable and prevents context that's too broad to give signal.
- **Show, don't just tell.** When drafting assets, produce the actual text/YAML the person can paste
  into Hex, not a description of it.
- **Map the accuracy bar per question.** Some answers can be "good enough"; others must be dead-on.
  Tailor effort accordingly.
- **Tribal knowledge → context.** Most early wins come from writing down what the team already knows.

---

## Reference files

- `agents/context-architect.md` — advise on + draft the four context assets; diagnose and fix wrong answers.
- `agents/rollout-planner.md` — produce a phased, customized rollout plan.
- `references/intake.md` — the questionnaire for customizing output to the person's setup.
- `references/context-assets-deep-dive.md` — detailed patterns and full examples (workspace guide,
  semantic model YAML, the fix framework). Read when the architect needs depth.
- `references/advanced-context.md` — reference repositories (code) and External Apps / MCP. Read when
  the person asks about repos or MCP, or already has code connected to their AI tooling.
- `references/hex-docs.md` — canonical Hex doc links. Fetch the relevant page before giving UI steps.
- `references/automation.md` — CLI + REST API map for context work from the terminal. Read when
  someone wants to automate endorsements, publish guides, run the suggestion loop, or have a coding
  agent (Claude Code, Codex, Cursor) apply context changes via `hex` or `curl`/scripts.
- `references/ask-hex.md` — tiered ways (in-product / MCP / CLI) to get Hex's own signal on what
  context to improve, including the `hex suggestion list` CLI loop.
