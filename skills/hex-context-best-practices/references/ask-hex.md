# The improvement loop — suggestions → coherent PRs

Once context is live and people are asking questions in Threads, Hex generates **Suggestions** —
concrete recommendations to improve your context. This is the engine of **Mode B**: pull the
suggestions, organize them into coherent PRs, ship the fixes through GitHub.

**Division of tools (important):**
- **The CLI is for *signal and drafting*, never publishing.** Use it to *pull* suggestions and to
  *ask the Hex agent* (which can see the warehouse) to draft data-grounded content.
- **GitHub is for publishing.** Every actual change to a guide, workspace context, or semantic model
  ships as a repo edit → PR → merge → the Action syncs. See `references/github-sync.md`.

---

## Get the signal

**Context Studio → Suggestions (in-product).** Hex's AI-recommended improvements, generated from
conversation patterns, agent warnings, and user feedback. Each proposes a concrete fix — create/update
a guide, sharpen a description, endorse a resource, adjust workspace context. *(Admin/Manager;
Team/Enterprise.)*

**Pull them with the CLI** so a coding agent can read and act on them:

```bash
hex suggestion list --json          # all open suggestions
hex suggestion get <suggestion_id>  # details + the proposed change for one
```

**Ask the Hex agent directly** when you want it to reason about its own gaps or draft something
grounded in real data — it sees the warehouse; this coding agent doesn't. **Run these yourself — don't
hand the user commands to copy.** `create` returns a `thread_id`; poll `hex thread get <id>` until it's
done (it takes a minute or two), then use the response:

```bash
hex thread create "Review my revenue guide against the warehouse. What context would make you answer
completed-order questions from the semantic model instead of raw SQL? Return markdown I can paste."
hex thread get <thread_id>                    # poll until the response is ready
hex thread continue <thread_id> "Now draft the updated guide."
```

(Same idea works interactively in a Thread, or via the Hex MCP server if they use an MCP client —
MCP can `create_thread`/`continue_thread` but **cannot** pull Suggestions; those are CLI/in-product only.)

### First: is `hex.md` in the repo?

Check before auditing anything else. If the repo has guides but no `hex.md`, the workspace context is
probably UI-authored and uncommitted — the most common half-migrated state. Guides usually lean on its
rules (semantic-first policy, SQL guardrails), so flag it and bring `hex.md` under version control first.

### No Suggestions yet? Audit the repo

Empty is normal for a new/low-traffic workspace. Don't wait — **ask for the repo URL and read the
files.** For a synced workspace the repo files *are* the live guides (source of truth, read-only in
Hex). Review `hex.md` + `guides/` against the four-asset rules and draft improvements.

There's no way to list live guides (no CLI verb; the API lists only *draft* guides via
`getListDraftGuides`), so the repo is how you see what exists. Blind spot: a guide authored in the Hex
UI and never committed shows only in Context Studio.

---

## The loop: organize suggestions into coherent PRs

1. **Pull** open suggestions (`hex suggestion list`).
2. **Group them by domain/theme**, not one-off — e.g. all revenue-guide fixes together, all
   product-metric fixes together. Propose the grouping; let the user adjust.
3. **Draft each change.** Edit the guide / `hex.md` / semantic file in the repo. When the change must
   reference real tables or columns, delegate the drafting to the Hex agent (`hex thread` above, or a
   Thread) and bring its output into the file.
4. **Route by target — this is where not everything is a repo PR:**

   | Suggestion targets… | Where it goes |
   |---|---|
   | Guide, workspace context (`hex.md`), semantic model | **context repo → PR → Action** |
   | Warehouse description or endorsement | **Apply in Hex directly** (Context Studio / warehouse). These are *not* synced by the context repo — tell the user, don't try to put them in a PR. |

5. **Open one PR per domain/theme** with the repo-bound changes. User reviews the preview, merges; the
   Action syncs.
6. **Close the loop:** after merge, mark the handled suggestions done:

```bash
hex suggestion update <suggestion_id> --status completed
hex suggestion update <suggestion_id> --status dismissed --dismiss-reason "not relevant"
```

So instead of *you* hunting for gaps, Hex names them, this skill organizes them into reviewable PRs,
and the ones that belong in Hex (descriptions, endorsements) are called out to handle there.

---

**Running it on a cadence (optional, don't over-prescribe):** this loop can be re-run whenever
suggestions pile up, or scheduled to run periodically and open a PR for review — but let the team run
it however fits their workflow. Fetch the live pages in `references/hex-docs.md` before giving UI steps.
