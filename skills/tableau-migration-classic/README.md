# Tableau → Hex Migration Skill (classic-app build)

A durable, portable **agent skill** that migrates Tableau dashboards into Hex as a **classic app** — native notebook cells (SQL, input parameters, EXPLORE/METRIC/pivot charts, markdown, Python) assembled in an **app layout** — by **delegating the build to Hex's in-product notebook agent**. This coding agent parses the workbook XML and writes a precise **migration brief** + **styling spec**; Hex's notebook agent — which can see the live warehouse schema and the customer's workspace context — builds the native cells + layout on a **gated SQL data layer**; then this agent verifies with a **SQL-fidelity gate** (on the SQL), a **cell-spec diff** (on the exported chart specs), and a **visual-QA loop** (on the render). It's a standard Agent Skill, so it works with any terminal coding agent (Codex, Cursor, Claude Code, …).

It is a fork of the sibling **`tableau-migration`** skill, which is identical except that it delivers a **generative app**. See [Which skill to use](#which-skill-to-use).

## The deliverable

**A classic Hex app.** Every chart is a real Hex cell with an editable spec, the numbers live in inspectable, gated SQL cells the charts read (never re-query), filters are INPUT cells, and the whole dashboard is **maintainable by the customer's analysts with no code**. Because the specs are in the exported YAML, fidelity is checked **mechanically** — chart type, encodings, hex colors, number/date formats, date-axis types, `seriesId` linkage, layout grid — and then confirmed by a headless screenshot-diff loop against the original Tableau PNG.

**The trade-off, stated up front:** native cells **cannot** reproduce Tableau's pixel chrome, and a native chart **cannot compute a table calc, a running total, a percent-of-total, an LOD ratio, or any ratio of aggregates** — those get **pre-computed as SQL columns** during the parse. Maps, detail/LOD text tooltips, and web-page embeds become named gaps with agreed substitutes, settled with the customer during triage.

**Hand-building is a fallback only** — used when the notebook agent isn't available (feature off / no Hex credits). The artifact is the same; only the builder changes.

**Why delegate the build:** this coding agent is blind to the warehouse schema, the data, and the rendered result; the notebook agent sees all three. So for building *in Hex* it's the better-equipped agent. This coding agent's durable job is **understanding the Tableau source** (reading the XML, translating calcs/LOD/table-calcs/filters/params into the brief) and **verifying the result** (the three gates).

**The full playbook lives in [`SKILL.md`](SKILL.md).** That's the canonical doc the agent reads.

## Which skill to use

| | `tableau-migration-classic` (this one) | `tableau-migration` (sibling) |
|---|---|---|
| **Deliverable** | native cells + app layout | generative app (`genAppFiles`) |
| **Maintainable by analysts** | ✅ every chart is an editable cell | ⚠️ it's app code |
| **Fidelity to bespoke pixel styling** | ⚠️ structure + content, not pixels | ✅ closest available |
| **Fidelity checking** | cell-spec diff **+** render diff | render diff only |
| **Chart ceiling** | what EXPLORE/METRIC express (table calcs + ratios pre-computed in SQL; no maps → Python) | arbitrary, it's code |

Rule of thumb: **dashboards the team wants to own and edit → this skill. Pixel-critical dashboards where fidelity outranks maintainability → the generative sibling.** Decide per dashboard, not per batch. The Tableau-side parsing, the brief, and the SQL gate are identical in both.

## First-time setup
1. `cp credentials/tableau.env.example credentials/tableau.env` and fill in your Tableau **pod URL**, **site**, and **Personal Access Token**. (Gitignored — never commit it.)
2. Install the [Hex CLI](https://hex.tech/product/cli) and authenticate.
3. Know which **Hex data connection** the migrated cells should query, and ensure the **headless-agent-threads feature** is enabled (the default build uses `hex thread`).
4. Visual-QA gate: `pip install playwright && playwright install chromium`, then a one-time headed Hex login (`python scripts/hex_shots.py --login`).
5. For the YAML round-trips (INPUT cells, dataframe-SQL companions, `appLayout` edits, any hand-build): install the [RedHat YAML VS Code extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) so `*.hex.yaml` files validate live.

## What's in here
| Path | What |
|------|------|
| `SKILL.md` | The playbook — workflow spine (the agent reads this to run a migration) |
| `reference/` | On-demand detail: `connection-mapping.md`, `tableau-semantics.md` (understand the workbook), `build-classic-app.md` (**the default build** — known ceilings, styling spec, prescriptive prompt, form verification, cell-spec diff), `building-cells.md` (**native-cell capability map** + hand-build fallback), `build-notebook-agent.md` (brief + handoff mechanics), `visual-qa-loop.md` (render gate), `sql-review.md` (SQL-fidelity gate), `datasource-guide.md`, `gotchas.md` (parsing rules, CLI quirks, **app layout**) |
| `tableau-zoo/` | The "Tableau Zoo" — regression fixtures (`.twb` inputs + parity ground truth + Hex goldens) |
| `templates/` | Clone-and-override native Hex cell configs (METRIC, EXPLORE variants) — the **target format of this build**, and the source material for the hand-build fallback |
| `scripts/tableau_fetch.py` | Fetch `.twb`/`.twbx` from Tableau Cloud/Server |
| `scripts/tableau_shots.py` | Export PNGs of a workbook's dashboard + worksheets for visual QA |
| `scripts/hex_shots.py` | Headless Playwright screenshot of the built Hex app (visual-QA loop) |
| `credentials/` | `tableau.env.example` (copy → `tableau.env`, gitignored) |
| `tableau_exports/`, `working/` | Local downloads + scratch (gitignored) |

## How to use it (short version)
0. **Prioritize & organize** the customer's dashboards into one folder — migrate what's used, drop the dead weight, and **route any pixel-critical dashboard** to the generative sibling.
1. **Pilot 1–2 dashboards** end-to-end: parse → brief + styling spec (tile → cell type; table calcs/ratios → SQL columns) → gate the SQL → notebook-agent builds the **classic app** → SQL-fidelity gate + cell-spec diff + visual-QA loop against the Tableau originals, tune.
2. **Batch the rest** with the folder loop + `migrations.json` manifest.

See [`SKILL.md`](SKILL.md) for each step in full.
