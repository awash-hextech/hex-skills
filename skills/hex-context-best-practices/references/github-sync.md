# GitHub Sync — context as code (the default path)

Hex context (guides, workspace context, semantic projects) should live as **Markdown/YAML files in a
Git repo** and sync into Hex automatically via a GitHub Action. The repo is the source of truth;
synced resources are **read-only in Hex**, so no one can drift the live copy out from under version
control.

This is the path this skill defaults to. You author and edit files in the repo, open a PR to preview,
merge to publish. Fetch the live pages in `references/hex-docs.md` before giving UI steps — Hex's UI
changes. Authoritative doc: **Context Sync** (linked there).

---

## Who does what (read this first)

The work splits cleanly across two agents. Keep them in their lanes:

| | **This coding agent (Claude Code / Codex)** | **The Hex agent (Threads / Notebook)** |
| --- | --- | --- |
| Knows | git, repo layout, the config file, the Action, Markdown/YAML structure, the mental model | your actual warehouse — real tables, columns, endorsed assets, live query results |
| Does | scaffolds the repo, writes `hex_context.config.json`, sets up the Action, structures and edits files, opens PRs | **drafts data-grounded content** ("write me a guide for revenue using my workspace") |
| Can't | see your data — must not invent table/column names | do git, the config, or the Action |

**The handoff that makes this work:** when content needs to reference real tables or columns, don't
guess — have the **Hex agent draft it** (it can introspect the warehouse and run queries), then bring
that draft back into the repo, structure it, and sync it. See `hex-guides/guide-writing-guide.md` for
the prompt pattern. The coding agent owns the plumbing; the Hex agent owns the data grounding.

---

## Repo layout

A conventional layout (adapt to an existing repo — see "Editing an existing repo" below):

```
your-repo/
├── hex.md                       # workspace context (reserved filename — always-on, every prompt)
├── guides/
│   ├── revenue.md               # one guide per domain, retrieved by name+description
│   ├── product.md
│   └── ...
├── semantic/                    # optional — semantic project files
│   └── sales/
│       ├── model.yml
│       └── view.yml
├── hex_context.config.json      # tells the Action which files to sync
└── .github/workflows/
    └── hex-context.yml          # the sync Action
```

`hex.md` at the repo root is the **reserved path for workspace context**. Any other Markdown file is a
guide. You don't have to name it `hex.md` on disk — you can map any file to that slot with
`hexFilePath` (below).

---

## The config file — `hex_context.config.json`

Lives at the repo root. Tells the Action which files to upload and where they land in Hex.

```json
{
  "guides": [
    { "path": "hex.md", "hexFilePath": "hex.md" },
    { "pattern": "guides/*.md" },
    {
      "path": "docs/revenue-guide.md",
      "hexFilePath": "revenue.md"
    },
    {
      "pattern": "guides/**/*.md",
      "transform": { "stripFolders": true }
    }
  ],
  "semanticProjects": [
    { "id": "<semantic-project-uuid>", "path": "semantic/sales" }
  ]
}
```

**Guides** — two ways to point at files:
- `path` — a single file. Add `hexFilePath` if the path shown in Hex should differ from the repo path
  (e.g. map `docs/revenue-guide.md` → `revenue.md`, or map any file → the reserved `hex.md`).
- `pattern` — a glob. `guides/*.md` matches files directly in `guides/`; `guides/**/*.md` recurses.
  Add `"transform": { "stripFolders": true }` to drop folder paths from the name shown in Hex
  (`guides/sub/x.md` → `x.md`).

**Semantic projects** — each entry needs the `id` (the semantic project's UUID from your Hex
workspace) and the `path` to the directory holding its model/view files.

**Pruning is always on:** a resource removed from the config (or the repo) is **deleted from Hex** on
the next publish. The repo is the source of truth — deleting a file deletes the guide.

---

## The GitHub Action

Add `.github/workflows/hex-context.yml`:

```yaml
name: Publish Hex context

on:
  push:
    branches: ["main", "master"]
  pull_request:

permissions:
  contents: read
  pull-requests: write

jobs:
  publish_hex_context:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v6
      - name: Upload context resources
        uses: hex-inc/action-context-toolkit@v2
        env:
          GITHUB_TOKEN: ${{ github.token }}
        with:
          token: ${{ secrets.HEX_API_TOKEN }}
          comment_on_pr: true
```

**How it behaves:**
- **On a pull request** → the Action *stages* the changes and comments on the PR with a summary of
  changed resources plus a **link to test them in a thread preview**. Nothing goes live.
- **On merge to `main`/`master`** → the Action *publishes*. Changes are live in Hex, read-only.

**Action inputs** (all optional except `token`):
- `token` *(required)* — your Hex workspace token. Store as the repo secret `HEX_API_TOKEN`; never inline it.
- `config_file` — defaults to `./hex_context.config.json`.
- `hex_url` — defaults to `https://app.hex.tech`. Single-tenant / EU / HIPAA customers set their own
  base URL (e.g. `eu.hex.tech`, `yourco.hex.tech`).
- `comment_on_pr` — set `true` to get the preview comment (needs `GITHUB_TOKEN` in `env` and the
  `pull-requests: write` permission, both shown above).

`@v2` installs and uses the Hex CLI under the hood — no separate install step.

---

## The API token (one-time setup)

A **Workspace Admin** creates the token:

1. Hex → **Settings → API keys** → new workspace token.
2. Grant scopes: **Guides: Read, Guides: Write**, and **Semantic layer sync** (the last only if you
   sync semantic projects). Pick a sensible expiration.
3. In the GitHub repo → **Settings → Secrets and variables → Actions → New repository secret**, named
   **`HEX_API_TOKEN`**, pasted value.

Direct the user to create and paste the token themselves — don't ask them to hand it to you.

---

## Test locally before wiring CI (optional)

If they have the Hex CLI, the same sync runs from a terminal — useful for a first dry run:

```bash
hex auth login --token-from-env HEX_API_TOKEN   # or: hex auth login (interactive)
hex context preview                             # stages changes, returns a test link
hex context publish                             # publishes the staged preview
```

`--config-path <path>` points at a non-default config location. This is the same engine the Action
uses; most teams let CI do it and only reach for the CLI to debug.

---

## Recommended workflow (author → preview → publish)

1. **Write or edit** the file(s) in the repo — `hex.md` for workspace context, `guides/<domain>.md`
   for a guide. When the content must reference real data, get the draft from the Hex agent first
   (see the who-does-what table).
2. **Update `hex_context.config.json`** if you added a new file the globs don't already cover.
3. **Open a PR.** The Action comments with a preview link — open it, ask the preview thread the
   use case's real questions, confirm the answers improved.
4. **Merge.** The Action publishes; the guide/context is live and read-only in Hex.
5. **Iterate.** Context compounds — next change is a one-line edit and another PR.

Recommend **branch protection on `main`** (require the PR + a review) so nothing publishes to the live
workspace without the preview being seen. That's the whole point of the preview step.

---

## Editing an existing repo

Teams often already have a repo (dbt project, analytics monorepo). Don't impose the layout above —
**fit into what exists**:

- Read the repo first. If guides already live somewhere, point the config at them with `path`/`pattern`
  rather than moving files.
- Use `hexFilePath` / `stripFolders` to keep repo paths and Hex names sane without reorganizing.
- To update an existing guide: **edit the file in place**, open a PR, let the preview confirm, merge.
  No new file, no config change needed if a glob already matches it.
- Adding the workspace-context file to a repo that has none: create `hex.md` at the root (or map an
  existing file to `hex.md` via `hexFilePath`).

---

## Manual fallback (no repo yet)

If someone has no repo and just wants to test a single guide right now: **Data → Context Studio →
Guides → New guide**, paste, save; workspace context goes in **Settings → AI & agents**. This is a
quick smoke test, not the destination — anything pasted this way should move into the repo so it's
version-controlled and preview-gated. Steer them to set up the repo + Action as soon as they're
iterating for real.
