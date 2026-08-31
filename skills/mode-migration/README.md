# Mode → Hex Migration Skill (generative-app build)

A durable, portable **agent skill** that migrates Mode (Mode Analytics / ThoughtSpot Mode) reports into Hex by **delegating the build to Hex's in-product notebook agent**. This coding agent pulls the report via the Mode API and reads its **queries (SQL), Liquid templating, chart defs, and Python/R notebook** as the source of truth; it writes a precise **migration brief** + **styling spec**; Hex's notebook agent — which can see the live warehouse schema and the customer's workspace context — builds a **generative app** on a natively-gated SQL data layer; then this agent verifies with a **SQL-fidelity gate** (on the SQL) and a **visual-QA loop** (on the render). It's modeled on the sibling `tableau-migration` skill and shares its spine and Hex-side assets.

## The headline difference from the Tableau skill: Mode is SQL-native

A Mode query's text **is** the warehouse SQL that ran — there's no VizQL/LOD/table-calc layer to reverse-engineer. So the durable work re-centers on the layers Mode wraps around that SQL:

- **Liquid templating** — `{% form %}` parameters, `{{ @param }}` refs, `{% if %}`/`{% case %}` branching, and `{{ @definition }}` includes → Hex input cells + Jinja. (⚠️ Hex auto-quotes string params — the **inverse** of Mode, a classic silent-zero-rows trap.)
- **Query / dataset dependencies** — definitions inlined as CTEs; cross-report dataset refs rebuilt upstream.
- **Python/R notebook cells** — `datasets['Query Name']` → a Hex Python cell reading the upstream SQL dataframe.
- **The presentation layer** — Report Builder layout or a bespoke **HTML/Liquid report page** → the generative app (which reproduces bespoke HTML/CSS far closer than native cells).

When Hex points at the **same warehouse** Mode queried (the common case), the SQL ports **near-verbatim**. When the customer **also switches warehouses**, a real dialect-translation pass is owed — the skill makes that a tracked decision (`same_warehouse` in the manifest).

**The deliverable is a generative app** — a bespoke code app that reproduces Mode's layout and pixel styling, while the numbers stay in inspectable, gated SQL cells underneath (the app reads those dataframes; it never re-queries). The render is verified by a headless screenshot-diff loop against the original Mode report. **Hand-building native cells is a fallback only** — used when the notebook agent isn't available (feature off / no Hex credits).

**The full playbook lives in [`SKILL.md`](SKILL.md).** That's the canonical doc the agent reads.

## First-time setup
1. `cp credentials/mode.env.example credentials/mode.env` and fill in your Mode **workspace slug**, **API token**, and **secret**. (Gitignored — never commit it.)
2. Install the [Hex CLI](https://hex.tech/product/cli) and authenticate.
3. Know which **Hex data connection** the migrated cells should query (and whether it's the same warehouse Mode used), and ensure the **headless-agent-threads feature** is enabled (the default build uses `hex thread`).
4. For the visual-QA loop: `pip install playwright && playwright install chromium`, then one-time headed logins — `python scripts/hex_shots.py --login` **and** `python scripts/mode_shots.py --login`.

## What's in here
| Path | What |
|------|------|
| `SKILL.md` | The playbook — workflow spine (the agent reads this to run a migration) |
| `reference/` | On-demand detail: `connection-mapping.md`, `mode-semantics.md` (understand the report — Liquid/definitions/notebook/dialect), `build-generative-app.md` (**the default build** — Generative app), `build-notebook-agent.md` (brief + handoff mechanics), `visual-qa-loop.md` (render gate), `sql-review.md` (SQL-fidelity gate), `building-cells.md` (**fallback only** — hand-build native cells), `datasource-guide.md`, `gotchas.md` |
| `templates/` | Clone-and-override native Hex cell configs for the **fallback** hand-build (METRIC, EXPLORE variants). *Reused verbatim from the Tableau skill — Hex-side target format, source-agnostic.* |
| `scripts/mode_fetch.py` | Fetch reports (JSON + query SQL + chart defs + notebook) from the Mode API |
| `scripts/mode_shots.py` | Headless Playwright screenshot of a Mode report for visual QA |
| `scripts/hex_shots.py` | Headless Playwright screenshot of the built Hex app (visual-QA loop) |
| `credentials/` | `mode.env.example` (copy → `mode.env`, gitignored) |
| `mode_exports/`, `working/` | Local downloads + scratch (gitignored) |

## How to use it (short version)
0. **Prioritize & organize** the customer's reports into one folder — migrate what's used, drop the dead weight.
1. **Pilot 1–2 reports** end-to-end: pull → brief + styling spec → gate the SQL → notebook-agent builds the **generative app** → SQL-fidelity gate + visual-QA loop against the Mode originals, tune.
2. **Batch the rest** with the folder loop + `migrations.json` manifest.

See [`SKILL.md`](SKILL.md) for each step in full.
