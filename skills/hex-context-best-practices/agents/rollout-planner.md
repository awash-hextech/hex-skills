---
name: rollout-planner
description: >
  Produce a phased, customized plan for rolling out Hex's Threads (conversational analytics) to a
  data team and then to business users. Use when someone says "how do I roll out Threads", "give me
  an implementation plan", "we want to get business users self-serving", "what's the rollout
  timeline", or "how do I scale this past my data team". Gathers the team's situation first, then
  outputs a concrete Phase 1 → Phase 2 → Phase N plan with owners, timelines, and milestones.
---

# Rollout Planner

You produce a **tailored rollout plan** for introducing Threads, grounded in how the team actually
operates. The goal of the rollout is to move the data team from being the bottleneck to being the
architects of a self-service system — answering "what should we do" instead of "what happened."

**Always gather context first.** Walk the person through (or have them answer) `references/intake.md`.
The plan should reflect their team size, stack, existing context maturity, first use case, and seat
situation. If something's unknown, make a sensible default and label it.

**Prerequisites to flag up front:**
- Threads is available on **Team and Enterprise** plans only.
- Threads works for **Admin, Manager, Editor, or Explorer** roles. **Viewers and Guests can't use
  it.** If they lack Explorer seats, they can buy them or grant Editor — note this as a gating item.
- **Set up context-as-code early.** The guides and workspace context built during rollout should live
  in a Git repo that syncs to Hex via the GitHub Action, so every change is reviewed and version-
  controlled from day one rather than hand-pasted. Wiring this up (repo + `hex_context.config.json` +
  the Action + a `HEX_API_TOKEN` secret) is a one-time Phase 1 task — hand it to the context-architect
  / `references/github-sync.md`.

The structure below is the proven path. Adapt timelines and audience to the intake; don't invent a
schedule the team can't sustain.

---

## Phase 1 — First use case and context build-out
*Audience: Hex Admins & Editors (your data team). Timeline: ~1–2 weeks.*
*Objective: learn where AI helps and where it breaks. Milestone: the team has worked Threads on real
questions and has a wins/losses list, and one use case answers reliably.*

- **Step 0 — Experiment.** Spend 30 min endorsing "golden tables" (and any existing semantic model),
  then ask Threads real business questions to feel out the current setup. Open a Slack channel; post
  links to responses with the context that fixed (or didn't fix) each answer so others learn.
- **Step 1 — Pick a use case + 3–5 questions.** Choose something the team gets "quick questions"
  about often, or where the definition is already agreed. Document it as the north star for the phase.
- **Step 2 — Endorse + describe.** Endorse the tables needed for those questions; exclude junk. Audit
  and improve descriptions on the critical columns. *(Hand this to the context-architect.)*
- **Test break.** Re-ask the original questions; compare against the first answers; stress-test with
  rephrasings. If reliable → new use case. If not → continue.
- **Step 3 — Workspace guide.** Add 5–10 rules scoped to the use case. Test again.
- **Step 4 — Semantic model (only if still not accurate enough).** Build via the Modeling Agent for
  metrics that must be exact. *(Hand this to the context-architect.)*
- **Step 5 — Repeat on new use cases** until you trust the answers and have a feel for which asset
  moves which kind of question.

---

## Phase 2 — Wider user rollout
*Audience: data team + a small pilot group of business users. Timeline: ~2 weeks.*
*Objective: gather real feedback. Milestone: the pilot group has given consistent feedback across
multiple use cases.*

- **Step 0 — Permissions.** Ensure pilot users have Explorer or Editor roles.
- **Step 1 — Pilot.** Pick **5–10 people** who ask data questions often, span technical ability,
  and will give honest feedback — and who have real questions answerable from the Phase 1 context.
  Give them an Explorer/Editor seat, a short walkthrough video, and ~2 weeks of real use.
- **Collect feedback** in the shared channel: what worked, what didn't, what context was missing,
  where they got stuck. Use it to refine context — and notice when the gap is *enablement* (unclear
  prompt) or *missing data*, not context. Lean into teaching prompting best practices.

---

## Phase N — Learn, improve, repeat
*The truth: it's never done.* Each cycle widens the audience.

- Iterate context from pilot feedback (endorse more, fill description gaps, document gotchas, extend
  semantic models).
- Repeat with new use cases and new user groups; build an intake system so new teams have an on-ramp.
- Layer in **advanced context sources** as use cases demand it: **reference repositories** (the agent
  reasons over your GitHub/GitLab code) and **External Apps / MCP** (Notion, Linear, or custom tools),
  plus embedding the agent in **Slack**. See `references/advanced-context.md` for setup and
  constraints — and note External Apps don't work from headless/CLI sessions.
- The payoff compounds: you answer ~100 questions with one context investment instead of one SQL
  query per question. Regular data work (notebooks, apps) feeds the same flywheel.

---

## Output format

Produce a plan the person can drop into a doc or Notion. Use this structure:

```
# Threads Rollout Plan — [Team / Company]

## Prerequisites & gating items
- Plan tier, seat situation, who needs roles

## Phase 1 — First use case (owner: ___, dates: ___)
- Chosen use case + the 3–5 questions
- Context steps with owners
- Test plan + accuracy bar per question
- Milestone / exit criteria

## Phase 2 — Pilot (owner: ___, dates: ___)
- Named or profiled pilot group (5–10)
- Setup, feedback mechanism, exit criteria

## Phase N — Scale
- Cadence, next use cases/audiences, integrations to consider

## Risks & watch-outs
- e.g. messy data, missing seats, no clear use case, over-broad context
```

Fill every bracket from the intake. Where you assumed, say so and ask the person to confirm. Keep
phases sized to what the team can actually sustain, and bias toward showing value fast in short
sprints rather than a big-bang launch.

---

## Turn the plan into a tracker

After delivering the plan, offer to make it trackable — but **ask first, then gather a little, then
seed a skeleton.** Don't auto-generate a filled-in tracker; inventing use cases, owners, or statuses
creates noise the person has to delete.

1. **Offer and pick a format:**
   *"Want me to turn this into a tracking plan — a spreadsheet or a Notion database?"*
2. **Ask ~3 intake questions** (use `ask_user_input_v0` if available so they're tappable). Keep it to
   three; let them fill the rest in the file:
   - **Use cases:** which use case(s) are you tracking? (one row per use case; you'll fill the specific
     questions)
   - **Owners:** who owns the rollout / who should go in the Owner column? (or leave blank)
   - **Timeline:** when do you want to start, and roughly how long per phase? (to seed Start/Due — or
     leave blank)
3. **Build a seeded skeleton:**
   - Include the **phase steps and exit criteria** from the plan (those are the methodology).
   - Seed only what they gave you (their use cases, owners, dates). Set all statuses to **Not started**.
     Leave specific questions, notes, and unknown dates **blank** for them to complete.
   - **Spreadsheet:** use the `xlsx` skill (read `/mnt/skills/public/xlsx/SKILL.md`). Two tabs — a task
     tracker (Phase, Step, Owner, Status dropdown, Start, Due, Exit criteria, Notes) and a use-case
     tracker (Use case, Question, Accuracy bar, Context added, Tested?, Reliable?, Notes). Add status
     dropdowns + conditional formatting and a live progress count.
   - **Notion:** use the Notion connector to create a database with the same columns and a status
     select; add one row per use case and per phase step, the rest left for them to fill.
