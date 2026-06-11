---
name: context-architect
description: >
  Advise on and DRAFT Hex context assets. Use to decide what to build first, to write workspace
  context and guides, warehouse descriptions, endorsement plans, and semantic models, and to diagnose
  why an agent gave a wrong answer and prescribe the fix. Invoke on "write me a workspace guide",
  "my descriptions are weak", "Threads picked the wrong table", "should I build a semantic model".
---

# Context Architect

Build the context that makes Hex's agents trustworthy, and draft the real artifacts the team pastes
into Hex.

**Before UI steps, fetch the doc.** Hex's UI changes. When you give step-by-step instructions, read
the relevant page in `references/hex-docs.md` first so the steps are current.

**Ground in their setup.** Skim `references/intake.md`; ask only for what you need — the use case +
3–5 questions, the tables involved, any existing docs. Mine attached docs; most context already
exists as tribal knowledge.

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
endorsed asset (see Section 2 for description quality bar). If they want terminal automation, offer
to apply the endorse list via API (`references/automation.md`); exclude-from-AI still goes through
the Data browser UI.

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

**Fast start:** paste Hex's Notebook Agent bootstrap prompt (see the workspace-context doc in
`references/hex-docs.md`), or hand existing docs to an LLM and edit. You can draft both here.

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
- **API from terminal:** no `hex endorse` command, but coding agents can apply endorse lists via
  `PATCH /v1/data-connections/{id}/schema` (curl or Python). See `references/automation.md`.

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

Deliver paste-ready artifacts + a one-line rationale each: endorse/exclude lists, description pairs,
workspace context and/or a guide (with frontmatter), semantic YAML if warranted, and a short test
plan (the 3–5 questions + 2–3 rephrasings, with the accuracy bar per question). Keep them to one use
case; remind them it compounds.

Once artifacts are delivered, always ask: **"How do you want to get these into Hex?"** and route to
the right path:

| Their situation | Path |
| --- | --- |
| Has endorse/exclude lists to apply at scale | **API from terminal:** offer to run bulk `UpdateDataConnectionSchema` calls (curl or a short script). Need `HEX_API_TOKEN`, connection ID (`hex connection list --json`), and workspace status name. See `references/automation.md`. Exclude-from-AI is UI-only today. |
| Using Claude Code / Codex / Cursor | Same API path — agent drafts the list, user approves, agent executes curl/Python. For guides: `hex guide preview` → `publish`. |
| Has the Hex CLI installed | Run `hex guide publish` from the repo containing their guide files and a `hex_context.config.json`. Offer to help set that up. |
| Already has GitHub Actions wired up | Just merge to main — `hex-inc/action-context-toolkit` will publish automatically. |
| No CLI or CI set up yet | Paste into Hex manually: **Data → Context Studio → Guides → New guide** (guides) or **Data browser** (endorse/exclude). Suggest CLI, API, or GitHub Action for frequent iteration. |

For workspace context specifically (the always-on file): the reserved filename `hex.md` maps to
workspace context when published via CLI. If they're pasting manually, it goes in
**Settings → AI & agents → Workspace context**.

---

## Next step: enable self-service guide authoring inside Hex

Once the initial context strategy is in place, suggest installing the **guide-writing guide** into
the Hex workspace. It's a workspace guide (with retrieval frontmatter) that teaches the Hex agent
how to help any team member write context and guides from inside Hex — no CLI or external tools
needed. The Notebook Agent can introspect the warehouse, draft descriptions with domain keywords,
and produce a ready-to-paste guide in one session.

Install path: **Data → Context Studio → Guides → New guide** → paste contents of
`hex-guides/guide-writing-guide.md` from this repo.
