# Hex Context Best Practices

An Agent Skill that helps data teams build and roll out a **context strategy** for Hex's AI agents
(Threads, the Notebook Agent, and the Modeling Agent). It advises on and **drafts** the context
assets, plans a phased rollout, and diagnoses why an agent gave a wrong answer.

It works across Claude Code, Claude.ai, OpenAI Codex, and other agents that read Markdown skills.

## What's inside

```
hex-context-best-practices/
├── SKILL.md                          # orchestrator — start here
├── agents/
│   ├── context-architect.md          # draft the context assets; fix wrong answers
│   └── rollout-planner.md            # phased Threads rollout + tracker offer
├── references/
│   ├── github-sync.md                # repo layout, config, the GitHub Action — the default path
│   ├── intake.md                     # questionnaire to customize to a setup
│   ├── context-assets-deep-dive.md   # workspace context/guides + semantic YAML examples
│   ├── advanced-context.md           # reference repositories + External Apps / MCP
│   ├── ask-hex.md                    # in-product / MCP / CLI ways to get Hex's improvement signal
│   └── hex-docs.md                   # canonical Hex doc links (fetch before UI steps)
└── hex-guides/
    └── guide-writing-guide.md        # add to Hex — has the Hex agent draft data-grounded context
```

## The model: context as code

Guides and workspace context live as Markdown files in a **Git repo** and sync into Hex through the
[`hex-inc/action-context-toolkit`](https://github.com/hex-inc/action-context-toolkit) GitHub Action.
The repo is the source of truth; open a PR to preview changes in a live thread, merge to publish, and
synced resources are read-only in Hex. The skill sets this up and then authors/edits files against it.

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
/plugin install hex-context-best-practices@hex-skills
```

Then just ask, e.g. *"help me build a context strategy for our revenue KPIs in Hex."*

### Any agent CLI (cross-tool, Agent Skills standard)

```
npx skills add hex-inc/hex-skills
```

### OpenAI Codex

Clone the repo and ask Codex to follow `skills/hex-context-best-practices/SKILL.md` (or see
[`AGENTS.md`](../../AGENTS.md) at the repo root).

### Claude.ai (no code)

Download `hex-context-best-practices.skill` from the
[latest release](https://github.com/hex-inc/hex-skills/releases) and upload it in
Settings → Capabilities → Skills (paid plans).

### Manual (Claude Code personal skill)

```
git clone https://github.com/hex-inc/hex-skills
cp -r hex-skills/skills/hex-context-best-practices ~/.claude/skills/
```

## How it works

1. The agent reads `SKILL.md`, learns the mental model (four context assets on a guidance→governance
   spectrum, plus advanced sources), and routes to a specialist.
2. It gathers a little context via `references/intake.md` (or mines docs you attach).
3. **Context Architect** writes the assets as repo files (`hex.md`, `guides/<domain>.md`, semantic
   YAML) + a test plan, scoped to one use case — delegating data-grounded drafting to the Hex agent.
4. It wires up `hex_context.config.json` and the GitHub Action so a PR previews and a merge publishes
   (`references/github-sync.md`).
5. **Rollout Planner** produces a phased plan and can turn it into a spreadsheet or Notion tracker.
6. You iterate — context compounds, and each new use case is another PR.

## Credit

Distilled from Hex's *Data Leader's Playbook for AI Analytics* and Hex's published best-practice docs.
Hex and the named features are products of Hex Technologies; this is an independent aid for using them.
