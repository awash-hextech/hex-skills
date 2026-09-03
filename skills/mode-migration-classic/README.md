# Mode → Hex Migration Skill (classic-app build)

A durable, portable **agent skill** that migrates Mode (Mode Analytics / ThoughtSpot Mode) reports into Hex as a **classic app** — native notebook cells (SQL, input parameters, EXPLORE/METRIC/pivot charts, markdown, Python) assembled in an **app layout** — by **delegating the build to Hex's in-product notebook agent**. This coding agent pulls the report via the Mode API and reads its **queries (SQL), Liquid templating, chart defs, and Python/R notebook** as the source of truth; it writes a precise **migration brief** + **styling spec**; Hex's notebook agent — which can see the live warehouse schema and the customer's workspace context — builds the native cells + layout on a **gated SQL data layer**; then this agent verifies with a **SQL-fidelity gate** (on the SQL), a **cell-spec diff** (on the exported chart specs), and a **visual-QA loop** (on the render).

It is a fork of the sibling **`mode-migration`** skill, which is identical except that it delivers a **generative app**. See [Which skill to use](#which-skill-to-use).

## The headline difference from the Tableau skill: Mode is SQL-native

A Mode query's text **is** the warehouse SQL that ran — there's no VizQL/LOD/table-calc layer to reverse-engineer. So the durable work re-centers on the layers Mode wraps around that SQL:

- **Liquid templating** — `{% form %}` parameters, `{{ @param }}` refs, `{% if %}`/`{% case %}` branching, and `{{ @definition }}` includes → Hex input cells + Jinja. (⚠️ Hex auto-quotes string params — the **inverse** of Mode, a classic silent-zero-rows trap.)
- **Query / dataset dependencies** — definitions inlined as CTEs; cross-report dataset refs rebuilt upstream.
- **Python/R notebook cells** — `datasets['Query Name']` → a Hex Python cell reading the upstream SQL dataframe.
- **The presentation layer** — Report Builder rows → native cells in an `appLayout` (a close structural fit); a bespoke **HTML/Liquid report page** → native approximation + declared gaps.

When Hex points at the **same warehouse** Mode queried (the common case), the SQL ports **near-verbatim**. When the customer **also switches warehouses**, a real dialect-translation pass is owed — the skill makes that a tracked decision (`same_warehouse` in the manifest).

## The deliverable

**A classic Hex app.** Every chart is a real Hex cell with an editable spec, the numbers live in inspectable, gated SQL cells the charts read (never re-query), filters are INPUT cells, and the whole dashboard is **maintainable by the customer's analysts with no code**. Because the specs are in the exported YAML, fidelity is checked **mechanically** — chart type, encodings, hex colors, number/date formats, `seriesId` linkage, layout grid — and then confirmed by a headless screenshot-diff loop against the original Mode report.

**The trade-off, stated up front:** native cells **cannot** reproduce a bespoke HTML/Liquid Mode report page (custom CSS, D3/JS embeds), and a native chart can't compute a **ratio of aggregates** (that gets pre-computed in SQL). Those become native approximations with **declared gaps**, agreed with the customer during triage.

**Hand-building is a fallback only** — used when the notebook agent isn't available (feature off / no Hex credits). The artifact is the same; only the builder changes.

**The full playbook lives in [`SKILL.md`](SKILL.md).** That's the canonical doc the agent reads.

## Which skill to use

| | `mode-migration-classic` (this one) | `mode-migration` (sibling) |
|---|---|---|
| **Deliverable** | native cells + app layout | generative app (`genAppFiles`) |
| **Maintainable by analysts** | ✅ every chart is an editable cell | ⚠️ it's app code |
| **Fidelity to a bespoke HTML/CSS report page** | ⚠️ structure + content, not pixels | ✅ closest available |
| **Fidelity checking** | cell-spec diff **+** render diff | render diff only |
| **Chart ceiling** | what EXPLORE/METRIC express (ratios pre-computed in SQL; no maps → Python) | arbitrary, it's code |

Rule of thumb: **Report Builder reports → this skill. Hand-built HTML report pages where pixel fidelity outranks maintainability → the generative sibling.** Decide per report, not per batch. The Mode-side parsing, the brief, and the SQL gate are identical in both.

## Install

### Claude Code (plugin marketplace)

```
/plugin marketplace add hex-inc/hex-skills
/plugin install mode-migration-classic@hex-skills
```

Install `mode-migration` alongside it if you also want the generative build — the two
cross-reference each other for routing.

### Any agent CLI (cross-tool, Agent Skills standard)

```
npx skills add hex-inc/hex-skills --skill mode-migration-classic
```

### OpenAI Codex

Clone the repo and ask Codex to follow `skills/mode-migration-classic/SKILL.md` (or see
[`AGENTS.md`](../../AGENTS.md) at the repo root).

Then invoke it via your agent (e.g. a `/mode-migration-classic` command), or just ask to "migrate my Mode reports to Hex as a classic app" — the `description` frontmatter triggers it.

## First-time setup
1. `cp credentials/mode.env.example credentials/mode.env` and fill in your Mode **workspace slug**, **API token**, and **secret**. (Gitignored — never commit it.)
2. Install the [Hex CLI](https://hex.tech/product/cli) and authenticate.
3. Know which **Hex data connection** the migrated cells should query (and whether it's the same warehouse Mode used), and ensure the **headless-agent-threads feature** is enabled (the default build uses `hex thread`).
4. For the visual-QA loop: `pip install playwright && playwright install chromium`, then one-time headed logins — `python scripts/hex_shots.py --login` **and** `python scripts/mode_shots.py --login`.
5. For the YAML round-trips (INPUT cells, dataframe-SQL companions, `appLayout` edits, any hand-build): install the [RedHat YAML VS Code extension](https://marketplace.visualstudio.com/items?itemName=redhat.vscode-yaml) so `*.hex.yaml` files validate live.

## What's in here
| Path | What |
|------|------|
| `SKILL.md` | The playbook — workflow spine (the agent reads this to run a migration) |
| `reference/` | On-demand detail: `connection-mapping.md`, `mode-semantics.md` (understand the report — Liquid/definitions/notebook/dialect), `build-classic-app.md` (**the default build** — known ceilings, styling spec, prescriptive prompt, form verification, cell-spec diff), `building-cells.md` (**native-cell capability map** + hand-build fallback), `build-notebook-agent.md` (brief + handoff mechanics), `visual-qa-loop.md` (render gate), `sql-review.md` (SQL-fidelity gate), `datasource-guide.md`, `gotchas.md` (parsing rules, CLI quirks, **app layout**) |
| `templates/` | Clone-and-override native Hex cell configs (METRIC, EXPLORE variants) — the **target format of this build**, and the source material for the hand-build fallback. *Reused verbatim from the Tableau skill — Hex-side target format, source-agnostic.* |
| `scripts/mode_fetch.py` | Fetch reports (JSON + query SQL + chart defs + notebook) from the Mode API |
| `scripts/mode_shots.py` | Headless Playwright screenshot of a Mode report for visual QA |
| `scripts/hex_shots.py` | Headless Playwright screenshot of the built Hex app (visual-QA loop) |
| `credentials/` | `mode.env.example` (copy → `mode.env`, gitignored) |
| `mode_exports/`, `working/` | Local downloads + scratch (gitignored) |

## How to use it (short version)
0. **Prioritize & organize** the customer's reports into one folder — migrate what's used, drop the dead weight, and **route any pixel-critical HTML report** to the generative sibling.
1. **Pilot 1–2 reports** end-to-end: pull → brief + styling spec (tile → cell type) → gate the SQL → notebook-agent builds the **classic app** → SQL-fidelity gate + cell-spec diff + visual-QA loop against the Mode originals, tune.
2. **Batch the rest** with the folder loop + `migrations.json` manifest.

See [`SKILL.md`](SKILL.md) for each step in full.
