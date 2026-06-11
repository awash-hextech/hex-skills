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
│   ├── intake.md                     # questionnaire to customize to a setup
│   ├── context-assets-deep-dive.md   # workspace context/guides + semantic YAML examples
│   ├── advanced-context.md           # reference repositories + External Apps / MCP
│   ├── ask-hex.md                    # in-product / MCP / CLI ways to get Hex's improvement signal
│   ├── automation.md                 # CLI + API map; endorse via curl/script from coding agents
│   └── hex-docs.md                   # canonical Hex doc links (fetch before UI steps)
└── hex-guides/
    └── guide-writing-guide.md        # install into Hex — teaches the agent to help write guides
```

## Install

### Use inside Hex (no CLI needed)

If you're working in Hex and want the agent to help you write workspace context and guides without
leaving the product, install the **guide-writing guide** into your workspace once:

1. Copy the contents of [`hex-guides/guide-writing-guide.md`](hex-guides/guide-writing-guide.md).
2. In Hex: **Data → Context Studio → Guides → New guide**. Paste and save.

That's it. From then on, whenever anyone asks the Hex agent *"help me write a guide"* or *"how do
I add context for revenue"*, it retrieves this guide and walks them through it — all from inside
Hex, using the Notebook Agent against your actual warehouse.

This is the recommended next step after you've set up your initial context strategy.

---

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
3. **Context Architect** drafts paste-ready assets and a test plan, scoped to one use case.
4. **Rollout Planner** produces a phased plan and can turn it into a spreadsheet or Notion tracker.
5. You iterate — context compounds, and each new use case gets faster.

## Credit

Distilled from Hex's *Data Leader's Playbook for AI Analytics* and Hex's published best-practice docs.
Hex and the named features are products of Hex Technologies; this is an independent aid for using them.
