# Hex Context Management

An Agent Skill for **doing context management well in Hex** — building and maintaining the context
that makes Hex's AI agents (Threads, the Notebook Agent, and the Modeling Agent) accurate. It drafts
and edits the context assets as files in a Git repo, opens a PR, and diagnoses why an agent gave a
wrong answer.

It works across Claude Code, Claude.ai, OpenAI Codex, and other agents that read Markdown skills.

## What's inside

```
context-management/
├── SKILL.md                          # orchestrator — start here (Step 0 routes to a mode)
├── agents/
│   └── context-architect.md          # the authoring & audit engine; fix wrong answers
├── references/
│   ├── github-sync.md                # create the repo, config, the GitHub Action — how context ships
│   ├── ask-hex.md                    # improvement loop: pull Suggestions via CLI → coherent PRs
│   ├── intake.md                     # questionnaire to customize to a setup
│   ├── context-assets-deep-dive.md   # workspace context/guides + semantic YAML + semantic-first examples
│   ├── advanced-context.md           # reference repositories + External Apps / MCP
│   └── hex-docs.md                   # canonical Hex doc links (fetch before UI steps)
└── hex-guides/
    └── guide-writing-guide.md        # add to Hex — has the Hex agent draft data-grounded context
```

## The model: context as code

Guides and workspace context live as Markdown files in a **Git repo** and sync into Hex through the
[`hex-inc/action-context-toolkit`](https://github.com/hex-inc/action-context-toolkit) GitHub Action.
`hex.md` is the workspace context; every other `.md` is a guide. The loop is **edit files → open a PR
→ merge → the Action syncs to Hex**; synced resources are read-only in Hex, so the repo is the source
of truth. **Publishing is always GitHub** — the skill produces file changes and a PR, never publishing
via CLI or the UI.

Once context is live, Hex generates **Suggestions** from real usage. The skill uses the Hex **CLI** to
*pull* those suggestions and to *ask the Hex agent to draft* data-grounded content — then organizes
them into coherent PRs by domain. (The CLI is for signal and drafting; it never publishes.) Warehouse
descriptions and endorsements are applied in Hex directly, not synced from the repo.

Two agents split the work:
- **A coding agent with this skill** owns the plumbing — repo layout, `hex_context.config.json`, the
  Action, git/PR flow, Markdown structure. It can't see your warehouse.
- **The Hex agent** (Threads/Notebook) can see your warehouse, so it drafts data-grounded content
  ("write me a guide for revenue using my workspace"). Its drafts flow back into the repo.

Setup lives in [`references/github-sync.md`](references/github-sync.md).

## Install

### Claude Code (plugin marketplace)

```
/plugin marketplace add hex-inc/hex-skills
/plugin install context-management@hex-skills
```

Then just ask, e.g. *"help me build a context strategy for our revenue KPIs in Hex."*

### Any agent CLI (cross-tool, Agent Skills standard)

```
npx skills add hex-inc/hex-skills
```

### OpenAI Codex

Clone the repo and ask Codex to follow `skills/context-management/SKILL.md` (or see
[`AGENTS.md`](../../AGENTS.md) at the repo root).

### Claude.ai (no code)

Download `context-management.skill` from the
[latest release](https://github.com/hex-inc/hex-skills/releases) and upload it in
Settings → Capabilities → Skills (paid plans).

### Manual (Claude Code personal skill)

```
git clone https://github.com/hex-inc/hex-skills
cp -r hex-skills/skills/context-management ~/.claude/skills/
```

## How it works

1. The agent reads `SKILL.md`, learns the four-context-asset mental model, and runs **Step 0** to place
   you: **Mode A — bootstrap (0→1)** if you have little/no context, or **Mode B — audit & author-helper**
   if you already have a pipeline.
2. It gathers a little context via `references/intake.md` (or mines docs you attach).
3. **Context Architect** writes/edits the assets as repo files (`hex.md`, `guides/<domain>.md`, semantic
   YAML) + a test plan, scoped to one use case — delegating data-grounded drafting to the Hex agent. In
   Mode B it starts from Context Studio Suggestions (`references/ask-hex.md`).
4. It wires up (or fits into) `hex_context.config.json` and the GitHub Action, then opens a PR
   (`references/github-sync.md`). You merge; the Action syncs.
5. You iterate — context compounds, and each new use case or fix is another PR.

Heavily invested in semantic models? Answer yes to the semantic-first intake question and the whole
approach shifts to model-first routing (a `hex.md` policy + slim, model-routing guides) — see
`agents/context-architect.md` §4.

## Credit

Distilled from Hex's *Data Leader's Playbook for AI Analytics* and Hex's published best-practice docs.
Hex and the named features are products of Hex Technologies; this is an independent aid for using them.
