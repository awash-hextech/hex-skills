# Ask Hex what to improve

The best signal for what context to fix next comes from Hex itself, because the Hex agent knows the
warehouse and existing context — this skill doesn't. Point the person to the highest tier they can
reach. Each tier is independent; use what they have.

## Tier 1 — In-product (anyone with agent access)

- **Ask the Hex agent directly.** In a Thread, after a shaky answer, ask: *"What context would help you
  answer this correctly — a description, a guide, an endorsement?"* It can reason about its own gaps
  against your actual warehouse and context.
- **Read Suggestions.** Context Studio → **Suggestions** is Hex's AI-recommended context improvements,
  generated from patterns across conversations, agent warnings, and user feedback. Each proposes a
  concrete fix — create/update a guide, update workspace rules, improve a description, or endorse a
  resource — that you accept or reject. This is the fastest "what should I do better" answer.
  *(Admin/Manager only; Team/Enterprise.)*
- **Skim observability** for trending questions and where the agent struggles, to prioritize by volume.

## Tier 2 — Via the Hex MCP server (if they've installed it)

If the person uses Claude, Cursor, ChatGPT, Codex, Glean, or another MCP client, suggest connecting
the **Hex MCP server** (`https://app.hex.tech/mcp`; Team/Enterprise, Explorer+). It lets their AI
assistant **ask the Hex agent without leaving their tool** — it can `search_projects`, `create_thread`,
`get_thread`, and `continue_thread`.

Use it to ask the Hex agent the same gap-finding questions as Tier 1 from inside their workflow. **It
cannot pull Suggestions or observability data** — those stay in Context Studio (Tier 1) or the CLI
(Tier 3). Don't imply otherwise.

## Tier 3 — Via the terminal (CLI + API) — the clever loop

This is the payoff for CLI and coding-agent users.

**`hex` CLI** can **pull Hex's Suggestions straight into the terminal**, so a coding agent (Claude
Code, Codex) can read them and act:

**REST API** (curl / Python from the same terminal) can bulk-apply endorsements — there is no
`hex endorse` subcommand, but agents can call `PATCH /v1/data-connections/{id}/schema` after you
approve an endorse list. Full map: `references/automation.md`.

```bash
hex suggestion list --json          # Hex's own context-improvement recommendations
hex suggestion get <suggestion_id>  # details + evidence for one
hex suggestion update <id> --status COMPLETED   # or DISMISSED, with --dismiss-reason
```

The closed loop to pitch:
1. `hex suggestion list --json` — pull what Hex thinks you should fix.
2. For each, this skill (context-architect) drafts the fix — a guide, description, or endorsement.
3. Apply it: publish in Hex, or for GitHub-synced guides commit the change; then
   `hex suggestion update <id> --status COMPLETED`.

So instead of *you* hunting for gaps, Hex names them and your agent fixes them. *(Suggestions via CLI
are Admin/Manager, Team/Enterprise.)* Tip: `hex install agent-skill --claude` adds Hex's own bundled
Claude skill for driving the CLI.

### Let the agent drive the loop

The suggestion triage loop above is something your coding agent can run for you — not just assist
with. Two patterns depending on what tool you're in:

**Interactive triage session (Claude Code — `/loop`):**
Use `/loop` to keep re-running the suggestion triage in a single session. The agent pulls new
suggestions, drafts fixes, waits for your review, applies them, and repeats. Good for a focused
context maintenance pass where you want to stay in the loop.

```
/loop check for new hex suggestions, draft fixes for any open ones, and apply them after my approval
```

**Recurring automated maintenance (Claude Code — `/schedule`):**
Use `/schedule` to set up a remote agent that runs on a cron schedule — no session required. It
wakes up, runs `hex suggestion list`, drafts fixes as a PR or applies them directly, and goes back
to sleep. Good for teams that want context maintenance to happen in the background.

```
/schedule every Monday morning, run hex suggestion list, draft fixes for open suggestions, and open a PR
```

**Codex — Thread Automations:**
Codex doesn't have `/loop` or `/schedule` yet, but has **Thread Automations** — heartbeat-style
recurring wake-ups attached to the current thread. Set a minute-based interval for an active triage
loop, or a daily/weekly schedule for maintenance check-ins. Find it in the Codex thread menu.

Note: `/loop` and `/schedule` are Claude Code-specific. Thread Automations are Codex-specific. Both
do the same job — keep the suggestion loop running without you manually re-triggering it.

---

**How to choose what to suggest:** lead with Tier 1 (everyone has it). Add Tier 2 only if they mention
an MCP client or already have Hex connected. Bring up Tier 3 when they mention the CLI, coding agents,
or managing context as code — that's where the loop gets genuinely automated. Fetch the live pages in
`references/hex-docs.md` before giving setup steps.
