# Omni → Hex Migration Skill

An **agent skill** that migrates Omni Analytics dashboards into Hex. This coding agent
reads each dashboard through the Omni API: the tile queries, every layer of the semantic
model, and **Omni's own generated SQL and result rows per tile**. It compiles the
semantic queries into the SQL they mean and writes a precise **migration brief**. Hex's
in-product notebook agent then builds the dashboard, as either a **classic app** (native
cells in an app layout) or a **generative app** (a code app), chosen per dashboard. This
agent verifies the result with:
- a **SQL-fidelity gate**, anchored on result parity against Omni
- a **cell-spec diff** (classic path only)
- a **visual-QA loop**

It follows the same structure as the `mode-migration`, `tableau-migration`, and
`looker-migration` skills in this repo and reuses their Hex-side assets.

- **How it works, for humans:** [`HOW-IT-WORKS.md`](HOW-IT-WORKS.md)
- **The playbook the agent follows:** [`SKILL.md`](SKILL.md)

## Classic or generative?

| | Classic app | Generative app |
|---|---|---|
| **Deliverable** | native cells + `appLayout` | `genAppFiles` code app |
| **Best for** | the typical Omni tile grid | markdown/HTML-heavy, custom-vis, or branded dashboards |
| **Editable by analysts** | ✅ | ⚠️ code |
| **Fidelity checking** | cell-spec diff **+** render diff | render diff |

Default to classic when unsure. Decide per dashboard, not per batch.

## Install

### Claude Code (plugin marketplace)

```
/plugin marketplace add hex-inc/hex-skills
/plugin install omni-migration@hex-skills
```

Both build paths (classic and generative) ship in this one skill.

### Any agent CLI (cross-tool, Agent Skills standard)

```
npx skills add hex-inc/hex-skills --skill omni-migration
```

### OpenAI Codex

Clone the repo and ask Codex to follow `skills/omni-migration/SKILL.md` (or see
[`AGENTS.md`](../../AGENTS.md) at the repo root).

Then invoke it via your agent (e.g. a `/omni-migration` command), or just ask to "migrate my Omni dashboards to Hex" — the `description` frontmatter triggers it.

## First-time setup
1. `cp credentials/omni.env.example credentials/omni.env` and fill in your Omni instance
   URL and an **Organization API key**. The file is gitignored.
2. Install the [Hex CLI](https://hex.tech/product/cli) and authenticate. Know which **Hex
   data connection** to target, and enable the **headless-agent-threads** feature.
3. `pip install -r requirements.txt && playwright install chromium`, then
   `python scripts/hex_shots.py --login` once.

## What's in here
| Path | What |
|------|------|
| `SKILL.md` | The playbook (the agent reads this) |
| `HOW-IT-WORKS.md` | Human-facing explainer |
| `reference/` | `omni-semantics.md` (understand the dashboard), `build-classic-app.md`, `build-generative-app.md`, `build-notebook-agent.md`, `building-cells.md`, `sql-review.md`, `visual-qa-loop.md`, `connection-mapping.md`, `datasource-guide.md`, `gotchas.md` |
| `templates/` | Native Hex cell configs for the classic path (shared with the Mode and Tableau skills) |
| `scripts/omni_fetch.py` | List dashboards by views; fetch queries, model YAML, Omni's generated SQL, results, PNG |
| `scripts/omni_shots.py` | Headless Omni dashboard screenshot (fallback reference image) |
| `scripts/hex_shots.py` | Headless screenshot of the built Hex app |
| `credentials/` | `omni.env.example` (copy to `omni.env`, gitignored) |

## Short version
0. `python scripts/omni_fetch.py --list` → triage by views; confirm a build path per dashboard.
1. Pilot 1–2 dashboards: `omni_fetch.py --dashboard <id> --results --png` → brief → build →
   gates → customer confirm → tune.
2. Batch the rest with the `migrations.json` manifest.
