---
name: context-architect
description: >
  Advise on and DRAFT Hex context assets. Use to decide what to build first, to write workspace
  context and guides, warehouse descriptions, endorsement plans, and semantic models, and to diagnose
  why an agent gave a wrong answer and prescribe the fix. Invoke on "write me a workspace guide",
  "my descriptions are weak", "Threads picked the wrong table", "should I build a semantic model".
---

# Context Architect

Build the context that makes Hex's agents trustworthy, and write the real files into the team's Git
repo, where they sync to Hex via the GitHub Action.

**Before UI steps, fetch the doc.** Hex's UI changes. When you give step-by-step instructions, read
the relevant page in `references/hex-docs.md` first so the steps are current.

**Ground in their setup.** Skim `references/intake.md`; ask only for what you need — the use case +
3–5 questions, the tables involved, any existing docs. Mine attached docs; most context already
exists as tribal knowledge.

**You can't see their warehouse — don't invent table or column names.** When an artifact needs to
reference real data and you don't have it, either get it from the user (or attached docs), or delegate
the drafting to the **Hex agent**, which can introspect the warehouse: have them run the prompt in
`hex-guides/guide-writing-guide.md` in a Thread, then bring the data-grounded draft back and you do
the repo/config/PR mechanics. You own the plumbing; Hex owns the data grounding.

**Assume a Git repo.** Context lives as files in a repo and syncs to Hex via the GitHub Action — that's
the default destination for everything you draft, not a copy-paste into the UI. See
`references/github-sync.md`.

Work the assets in leverage order. You rarely need all of them for one use case.

---

## 1. Endorse & exclude (do this first — highest leverage)

Most warehouses are mostly staging/test/raw. Set the "approved menu":
- **Exclude from AI** the bad tables/schemas — a hard guardrail, not a hint.
- **Endorse** (Approved/Trusted) the production tables you'd stake an answer on.
- **Enable Endorsed Mode** (Settings → AI & agents) — restricts Explorer users to endorsed assets
  only in Threads. On by default; keep it on for self-serve rollouts. Editors can still toggle
  between endorsed and all assets; Explorers cannot when this is enforced.

### Domain endorsement pattern
Group endorsements by domain (revenue, product, marketing, etc.) and write descriptions on every
endorsed asset that name the domain and the questions it serves. The descriptions are the routing
layer — the agent narrows to endorsed assets first, then reads descriptions to pick the right one.

**The workflow:**
1. Endorse all assets for a domain (tables, projects, semantic models).
2. On each endorsed asset, write a description that includes domain keywords users actually type —
   e.g. *"Use for revenue, ARR, MRR, and churn questions. Source of record for subscription value."*
3. Done. No further mapping needed.

**Anti-pattern — don't duplicate in workspace context.** Do not add a domain→table routing table to
the workspace context file. If your descriptions are good, the agent already knows which endorsed
asset to pick. A routing table in workspace context is a sign that descriptions are weak — fix the
descriptions instead.

Deliver: an endorse list + an exclude list grouped by domain, plus description drafts for each
endorsed asset (see Section 2 for description quality bar).

---

## 2. Warehouse descriptions (the "what")

Table/column descriptions answer *what this contains*. Start with the most-used endorsed tables and
the columns that get queried or joined often.

Test: *could a new-grad hire use this field correctly from the description alone?*

```
Bad:  "The ID of the customer"
Good: "Unique identifier for customers. Maps to customers.id in the CRM. NULL for guest checkouts."
```

A good description adds what it maps to, edge cases, and any join/filter preference.

---

## 3. Workspace context & guides (the "when / how")

Two related assets — don't conflate them:

- **Workspace context** — one markdown file sent with **every** prompt. Global truths only. Keep it
  under ~300 lines / 800 words so it doesn't crowd out descriptions and guides. Four sections that
  perform well: Business Context, Data Conventions & Structure, Recurring Mistakes, Analysis
  Preferences.
- **Workspace guides** — a **library** of files the agent retrieves only when relevant. One per
  domain, ~150 lines / 350 words. Each needs `name` + `description` frontmatter written *for
  retrieval* — include the words users actually type ("revenue, sales, GMV, AOV"). Sections: Canonical
  Metrics, Join Patterns, Schema Preferences, Risk Areas, Example Questions.

**Decision test:** applies to *every* question → context. Specific domain or question type → guide.

**Rules for both:**
- Enforceable language: "Always" / "Never", not "try to" or "prefer."
- Describe **when and how** to use data, not what it is (the *what* is warehouse descriptions).
- For each anti-pattern: name it, say *why* it's wrong, state the correct behavior.

**Keep these OUT of workspace context** (each has a better home): a full warehouse directory →
descriptions; golden tables → endorsements; tables to ban → exclude-from-AI; semantic model logic →
the model; metric formulas → guides or semantic models.

**Fast start:** when the content must reference real data, have the Hex agent draft it (the prompt in
`hex-guides/guide-writing-guide.md` — it can see the warehouse); otherwise hand existing docs to an
LLM and edit, or draft both here from what the user gives you.

Full structure and examples: `references/context-assets-deep-dive.md`.

---

## 4. Semantic models (rigid rules — build when needed)

Highest investment, strongest governance. YAML defining measures, dimensions, relations. Both Threads
and the Notebook Agent prefer them over raw tables — endorse the models too.

Build one when answers must be exact and the lighter assets aren't enough, when a metric needs one
definition everywhere (revenue, churn, active users), or when the DB is complex with recurring joins.

Build via the Modeling Agent (Modeling Workbench): from an existing project, from named tables, by
porting LookML/`.pbi`, or by syncing Cube / dbt MetricFlow / Snowflake Semantic Views. Don't treat a
model as a data-cleaning shortcut — say so honestly.

YAML anatomy and examples: `references/context-assets-deep-dive.md`.

---

## 5. Advanced sources (Team/Enterprise — only when relevant)

- **Reference repositories** — connect GitHub/GitLab so the agent reasons over code (metric logic,
  table structures, event logging). Suggest when logic "lives in the code." The repo *description*
  drives it; point to the repo from workspace context, mapped to a metric/domain.
- **External Apps / MCP** — let the agent use Notion, Linear, or custom MCP tools. Beta. Suggest when
  needed context lives outside the warehouse. Note: each call needs in-conversation approval, and
  External Apps don't work from CLI/API/headless sessions.

Setup, roles, constraints: `references/advanced-context.md`.

---

## Find the gaps: ask Hex what to improve

Don't guess what to fix — Hex knows your warehouse and context, and you don't. Route to the highest
tier the person can reach (full ladder in `references/ask-hex.md`):
- **Anyone:** ask the Hex agent in a Thread *"what context would help you answer this better?"*, and
  read **Context Studio → Suggestions** (Hex's auto-generated improvement recommendations).
- **MCP installed:** use the Hex MCP server to ask the Hex agent from their own tool (Claude/Cursor/
  Codex/etc.). It can't pull Suggestions or observability — only ask the agent and search projects.
- **CLI / coding agents:** `hex suggestion list` pulls Hex's recommendations into the terminal; the
  agent reads them, drafts fixes here, applies them, then marks them done — a closed loop.

## Diagnose a wrong answer → fix

Every off answer is a context gap. Match the failure to the fix. Quick tactic: ask the agent itself
*"that's wrong, you should have used table_x — what would help you pick it?"*

| Failure | Fix |
| --- | --- |
| **Wrong table** | Endorse the right one; **exclude** the wrong one (don't try to ban it in text); sharpen the right table's description. |
| **Bad join** | Describe the join columns; add a context/guide rule: "always join on `customer_id` in the customer schema." |
| **Wrong field / aggregation** | Sharpen the column description; add a rule: "calculate ARR by summing `arr_final` in `fct_revenue`." |
| **Missed filter** | Sharpen the column description; add a rule: "always filter customer status on `cust_status_new`." |
| **"Can't find that data"** | The columns lack descriptions — add them. |

**Pick the lever by symptom:** trying to *ban* a table is governance → use **exclude-from-AI**, not
the workspace context (banning by text is unreliable). Choosing *among good options* → context/guide.
Needs perfect accuracy → semantic model.

---

## Output

Deliver artifacts + a one-line rationale each: endorse/exclude lists, description pairs, workspace
context and/or a guide (with frontmatter), semantic YAML if warranted, and a short test plan (the 3–5
questions + 2–3 rephrasings, with the accuracy bar per question). Keep them to one use case; remind
them it compounds.

**Deliver everything as repo files, not paste-ready blobs.** The destination is a Git repo that syncs
to Hex via the GitHub Action — the repo is the source of truth and synced resources are read-only in
Hex. Write the actual files:
- Workspace context → **`hex.md`** at the repo root (the reserved path).
- Each guide → **`guides/<domain>.md`**.
- Semantic project files → a directory referenced from `hex_context.config.json`.

Then wire and ship them:
1. **Update `hex_context.config.json`** so the new files are covered (a `guides/*.md` glob usually
   already is). Full schema + the Action YAML + token setup: `references/github-sync.md`.
2. **Open a PR.** The Action posts a preview link — re-ask the use case's real questions against it.
3. **Merge** to publish.

If they have an existing repo, fit into its layout (read it first, point the config at where guides
already live) rather than imposing a new structure — see the "Editing an existing repo" section of
`references/github-sync.md`. To update an existing guide, edit the file in place and open a PR.

**Editing vs. creating:** for a fix to an existing guide, prefer editing the file already in the repo
over adding a new one — no config change needed if a glob already matches it.

**Manual fallback (only if they have no repo yet):** paste into **Data → Context Studio → Guides →
New guide** (workspace context → **Settings → AI & agents**) to smoke-test, then move it into a repo
so it's version-controlled and preview-gated. Don't make this the default.

---

## Next step: enable data-grounded self-service authoring

Once the initial context strategy is in place, add the **guide-writing guide**
(`hex-guides/guide-writing-guide.md`) to the workspace so any team member can get the Hex agent to
draft data-grounded context — the Hex agent can introspect the warehouse and verify column names,
which a coding agent can't. Its output flows back into the repo and syncs like everything else.

Install it the same way as any other guide: **commit it to the repo** (e.g. `guides/guide-writing.md`)
so the Action publishes it. It's already covered by a `guides/*.md` glob. (Pasting it into
Context Studio works too, but committing keeps it version-controlled with the rest.)
