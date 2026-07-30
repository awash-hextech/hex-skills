---
name: hex-context-best-practices
description: >
  Use this skill whenever someone is authoring, auditing, or improving the context that makes Hex's
  AI agents (Threads, the Notebook Agent, the Modeling Agent) accurate — and managing that context as
  files in a Git repo that syncs to Hex. Triggers on: "context strategy", "context engineering", "set
  up Threads context", "workspace guide", "warehouse descriptions", "endorse tables", "semantic
  model", "my agent gave the wrong answer", "audit my Hex context", "improve agent accuracy", "how do
  I make Hex AI more accurate", "Hex Context Studio", "context suggestions". Always use this skill for
  any task about making Hex's agents trustworthy through better context — even if phrased casually
  like "help me get my data team using AI" or "why does Threads keep picking the wrong table". It
  drafts and edits the actual context assets (workspace context, guides, descriptions, semantic
  models) as repo files and opens a PR to sync them.
---

# Hex Context Authoring & Audit

Help a data team **author and audit the context** that makes Hex's agents give trustworthy answers.
Context lives as files in a **Git repo** and syncs to Hex via a GitHub Action; this skill drafts and
edits those files and opens a PR.

The single most important idea: **agents are only as good as the context you give them, and context
compounds.** It doesn't need to be perfect on day one. Start with what exists, scope to one use case,
improve every loop.

**How context reaches Hex — the loop this skill drives:**

```
author/edit files in the repo  →  open a PR  →  user merges  →  GitHub Action syncs to Hex
```

`hex.md` at the repo root is the **workspace context** (always-on, every prompt). **Every other `.md`
is a guide** (retrieved when relevant). Synced files are read-only in Hex — the repo is the source of
truth. This skill never publishes via the CLI or by pasting into the UI; it produces file changes and
a PR, and the user's merge + the Action do the rest. Full mechanism: `references/github-sync.md`.

---

## Step 0 — Where are they starting? (do this first)

Before drafting anything, figure out the person's context maturity with a couple of quick questions
(don't interrogate — infer from what they say):

- Do you already have Hex context set up — a `hex.md`, guides, endorsed tables?
- Is it already in a **Git repo that syncs to Hex** (the Action), or authored in the Hex UI, or not
  really anywhere yet?
- Are Context Studio **Suggestions** piling up, or is Threads giving wrong answers you can point to?

Their answer routes to one of two modes. Both use the same authoring engine
(`agents/context-architect.md`) and the same asset mental model below.

### Mode A — Bootstrap (0 → 1)
*They have little or no context, or nothing version-controlled yet.*

1. **Endorse & exclude first (in Hex) — highest-leverage, do before drafting.** Have the user endorse
   a few golden tables for the use case and exclude the schemas/databases/junk tables the agent
   shouldn't touch. This is a **Hex UI action** (Context Studio / data browser) — not a repo file, not
   the CLI. It defines the approved menu the agent pulls from; the guides then reference endorsed tables.
2. **Stand up the context repo** (if they don't have one): `hex.md` for workspace context, a
   `guides/` folder, `hex_context.config.json`, and the sync Action. Setup: `references/github-sync.md`.
3. **Draft the first assets** — workspace context + one domain guide — scoped to a single use case.
   When content must reference real tables/columns, have the **Hex agent draft it** (it can see the
   warehouse; this coding agent can't) using the prompt in `hex-guides/guide-writing-guide.md`.
4. **Open the PR.** They review the preview, merge, and the Action syncs.

### Mode B — Improve from Suggestions (existing pipeline)
*They already have context live; Hex is now generating Suggestions from real usage.*

This is the ongoing improvement loop (full detail in `references/ask-hex.md`):

0. **Check the repo has `hex.md` first.** If workspace context isn't in the repo, it's likely
   UI-authored and uncommitted — flag it and bring it under version control before anything else.
   Guides usually depend on its rules (a semantic-first policy, SQL guardrails), so a missing `hex.md`
   is the most common half-migrated state.
1. **Pull the signal.** `hex suggestion list` (or Context Studio). **None yet?** Normal — ask for the
   repo URL and audit the files instead (there's no way to list live guides; the repo is source of
   truth). The CLI pulls signal and drives the Hex agent to draft — it never publishes.
2. **Organize into coherent PRs, grouped by domain/theme** — e.g. all revenue-guide fixes in one PR.
   Draft each change with `agents/context-architect.md`, delegating data-grounded drafting to the Hex
   agent (`hex thread`, or a Thread) since it can see the warehouse.
3. **Route by target:** guide / workspace context (`hex.md`) / semantic model → repo files in the PR;
   **warehouse descriptions and endorsements → apply in Hex directly** (they're not synced by the
   context repo — say so, don't force them into a PR).
4. **User merges → the Action syncs.** Then mark the handled suggestions done (`hex suggestion update`).

**Publishing is always GitHub.** The skill produces file changes and opens a PR; the user's merge and
the Action deploy. The CLI never publishes guides. (No repo yet? Paste one guide into Context Studio to
smoke-test, then move it into the repo.)

**Keep steps current.** Hex's UI changes. Before giving step-by-step UI instructions, fetch the
relevant page from `references/hex-docs.md`.

**Gather a little setup context.** `references/intake.md` is a short questionnaire (or attach docs) so
output fits their actual warehouse and use case. Ask for what you need, infer the rest, note assumptions.

---

## The mental model (the four context assets)

Hex's agents reference **four categories of context**. Each has one job. Keeping each category focused
on its job is **context engineering**. They sit on a spectrum from loose **guidance** to rigid
**governance**:

1. **Endorsed & excluded statuses** — *your warehouse guardrails.* Mark schemas/tables/semantic
   models as Approved/Trusted, or "Exclude from AI" for staging, test, and deprecated data. The
   **fastest, highest-leverage** action — it defines the "approved menu" the agent pulls from. Pair
   with **Endorsed Mode** (Settings → AI & agents): when enabled (the default), Explorer users are
   restricted to endorsed assets only in Threads. Recommended for self-serve.
2. **Warehouse descriptions** — *the foundational context.* Table and column descriptions. Answers
   "what does this column contain." Fundamental hygiene.
3. **Workspace context & guides** — *teaching the agent your business.* **Workspace context** (`hex.md`)
   is one file sent with every prompt (global truths); **guides** are a retrieved library, one per
   domain. Both describe *when/how* to use data, not *what* it is. Anything that doesn't fit the
   other three.
4. **Semantic models** — *the rigid rules.* YAML that codifies how tables join, how measures are
   calculated, what dimensions exist. For metrics that must be 100% correct every time.

**Which of these live in the repo:** **workspace context (`hex.md`), guides, and semantic models sync
from the repo** via the Action — author and edit them as files. **Endorsements and warehouse
descriptions are applied in Hex** (Context Studio / the warehouse), not synced from the context repo.
So when a fix targets a description or endorsement, do it in Hex; only the first three become PRs.

**Advanced sources (optional, later-stage):** on Team/Enterprise, two more extend the four —
**reference repositories** (connect GitHub/GitLab so the agent reasons over your code) and **External
Apps / MCP** (Notion, Linear, or custom MCP tools). Surface only when the person asks about code repos
or MCP or has matured past the basics. Governed the same way — by a clear description. See
`references/advanced-context.md`.

**The routing rule that keeps categories clean** (state this whenever someone is unsure where a piece
of context belongs):
- Endorsing specific tables/schemas → endorse them in Hex. Banning bad tables → **exclude from AI**
  (not the workspace context — text bans are unreliable).
- Defining what a column contains → warehouse description (not the workspace context).
- Logic for joining two tables → semantic model if you have one, else warehouse descriptions on the
  joined columns.
- Applies to every question → workspace context (`hex.md`). Specific domain/question type → a guide.
- Metric formulas → a guide or semantic model (not the always-on context).

**Where ownership tends to land:** warehouse descriptions and semantic models live closer to the
warehouse (analytics engineering); endorsements and guides live closer to Hex's UI (analysts/admins).
No hard rule.

**Prioritization (the 30-minute start):** endorse a few golden tables and exclude junk → add
descriptions to the most-queried endorsed tables/columns → write a workspace guide with 5–10 rules →
add semantic models to codify key metrics. Always scope to a real business use case. Don't boil the ocean.

---

## Working principles for any output

- **Positive guidance beats prohibitions.** "Always join on `customer_id` in the customer schema"
  works better than "don't use the wrong key."
- **Scope to one use case** = a broad subject with 3–5 concrete business questions. Keeps the work
  measurable and prevents context that's too broad to give signal.
- **Show, don't just tell.** Produce the actual files (`hex.md`, `guides/<domain>.md`, semantic YAML)
  in the repo, not a description of them.
- **Two agents, two lanes.** This coding agent owns the plumbing (repo layout, `hex_context.config.json`,
  the Action, git/PR flow, Markdown structure) but can't see the warehouse. The **Hex agent**
  (Threads/Notebook) can — so when content must reference real tables or columns, have Hex draft it,
  then bring the draft into the repo. Never invent table/column names you can't verify.
- **Run the CLI yourself.** When you delegate to the Hex agent, *you* run `hex thread create` and poll
  `hex thread get` for the result — don't hand the user commands to copy/paste.
- **Map the accuracy bar per question.** Some answers can be "good enough"; others must be dead-on.
- **Tribal knowledge → context.** Most early wins come from writing down what the team already knows.

---

## Reference files

- `agents/context-architect.md` — the authoring & audit engine: decide what to build, draft/edit the
  four assets, and diagnose + fix wrong answers.
- `references/github-sync.md` — **how context reaches Hex.** Create the repo, `hex.md` + guides layout,
  `hex_context.config.json`, the GitHub Action, token setup, and the PR → merge → sync loop.
- `references/ask-hex.md` — the Mode B improvement loop: pull Suggestions via the CLI, organize them
  into coherent PRs by domain, route by target, mark done. The CLI pulls signal and drives the Hex
  agent to draft — it never publishes.
- `references/intake.md` — the questionnaire for customizing output to the person's setup.
- `references/context-assets-deep-dive.md` — detailed patterns and full examples (workspace context,
  guide, semantic model YAML, the fix framework). Read when you need depth.
- `references/advanced-context.md` — reference repositories (code) and External Apps / MCP.
- `references/hex-docs.md` — canonical Hex doc links. Fetch the relevant page before giving UI steps.
- `hex-guides/guide-writing-guide.md` — a guide you add to the workspace so the Hex agent can draft
  data-grounded context that flows into the repo.
