# Build via a Hex Generative app (the default build)

The **default deliverable**: keep the data layer native and gated, then have the notebook
agent build a **Generative app** (a bespoke code/React app — `genAppFiles` in the export)
as the *presentation* layer on top of those cells.

> **Why the generative app is the obvious fit here.** The source **is** a React/HTML app.
> A generative app is a React/HTML app. This is the closest source→target match of any
> migration in this family — layout, interactions, custom components and pixel styling all
> have a real destination, and the styling spec isn't reconstructed from a viz grammar, it's
> **read out of the source verbatim**. Native EXPLORE/METRIC cells would throw all of that
> away, which is why the fallback path comes with a warning to the customer.

> **Division of labor is unchanged.** This coding agent owns *understanding the artifact*
> (and grounding its data) and *verifying the result*; the notebook agent owns *building in
> Hex*.

## The core principle: split the layers

A Generative app has **no diff-able native SQL cells** — its data logic can hide inside the
app code, which would gut both the SQL-fidelity gate and the grounding gate. So the
generative layer never authors SQL:

1. **Data layer — native + gated (the accuracy *and* the grounding guarantee).** Build the
   SQL derivation cells and run the full **SQL-fidelity gate** on them
   ([`sql-review.md`](sql-review.md)). Ordinary, inspectable SQL cells.
2. **Presentation layer — generative.** The app *reads the existing dataframes*; it does
   not re-query and does not hold data. The prompt says so explicitly.

⚠️ **Never skip step 1.** "Just prompt for a generative app" produces an app that generates
its own SQL — or, far worse in this skill, **carries the artifact's mock arrays straight
into the app code**, since they're right there in the source you handed it. A generative app
built without a gated data layer under it is the artifact again, with a Hex URL.

### ⚠️ Pre-build the SQL when the ledger has 🎭 rows

Both skills-in-the-family let the notebook agent author the SQL and gate it post-hoc. Here,
**escalate to pre-building whenever the grounding ledger contains fabricated shapes** — i.e.
most migrations. The reason is specific: when SQL is being written *for the first time*
rather than ported, there's no source query to diff against, so the post-hoc gate is
weaker exactly where the risk is highest. Pin and gate the numbers first, then let the agent
build presentation over cells whose values are already proven.

Agent-built SQL + post-hoc gating is fine when the ledger is all 📋/🗄️ (real data with a
known source) — the mapping is concrete and diffable.

---

## The styling spec (read it out of the source)

Distill the parse into a **styling spec** — one block per section. Unlike the Tableau/Mode
skills, **every value here is literally in the artifact source**, so extract, never eyeball:

Per section:
- **Exact title + subtitle** — verbatim strings from the markup.
- **Panels + what each shows** — the chart/tile and which grounded dataframe it reads.
- **Filter wiring** — which inputs drive this panel (from the control's scope).
- **Colors as hex codes** — from the `:root` custom properties and the chart configs,
  including the **dark-mode overrides**.
- **Layout** — the real CSS structure: grid columns, section order, what's in the top band,
  responsive behavior at phone width.
- **Typography** — font families/sizes if the artifact set them deliberately.
- **Number + date formats** — from `Intl.NumberFormat` options / format strings.
- **Tooltip / label fields** — the measures shown and their formatted labels.
- **Empty states** — including the wording for any **Stub** panel (see below).

Keep it tight and factual — a spec, not prose.

### Stub panels go in the spec

Every **🕳️ Stub** disposition from the grounding gate needs an explicit spec line, or the
agent will fill the hole with something plausible:

> *"Panel 'Churn Risk' — **no data source**. Render the panel frame and title with an
> explicit empty state reading 'No data source connected'. Do **not** generate, sample or
> approximate values for it."*

---

## The handoff prompt

App type is controlled by **prompt wording alone** — there is no CLI flag. The prompt
**must open** by demanding a Generative app:

> *"Build this as a **GENERATIVE APP** (App builder → Generative app), **not** a classic
> notebook app. Read the `Migration brief` + `Styling spec` cells — they are the full spec
> for migrating a Claude artifact into this project.*
>
> *The SQL derivation cells already exist and are validated — **use them as the data
> source; do NOT write new SQL, do NOT re-query the warehouse, and do NOT embed any data
> in the app code.** The app reads these dataframes: `<df1>`, `<df2>`, …*
>
> *⚠️ **The `Artifact source` cell is a layout and styling reference ONLY. Every number in
> it is a placeholder — do not reproduce, approximate, or hardcode any of those values.
> All data comes from the dataframes above.***
>
> *Build the presentation to match the Styling spec exactly: section titles, layout
> structure, the given colors (hex codes, including dark mode), number/date formats, and
> tooltip/label fields. Reproduce the artifact's layout section by section. Wire the input
> parameters to filter the app interactively per the spec.*
>
> *For any panel marked **no data source** in the spec, render its empty state as written —
> do not generate values for it."*

Hand it off:

```bash
hex thread create --project <id> "$(cat prompt.txt)" --json
```

- **⚠️ Surface the returned `url` to the customer immediately** — the build runs several
  minutes; let them watch and redirect it live.
- **Multiple artifacts in scope → tab navigation** (one tab per artifact), named in the
  prompt.

## Verify it actually built a Generative app

```bash
hex project export <project_id> -o app.yaml
```

- **`genAppFiles` present and non-empty** → it's a Generative app. ✅
- **`genAppFiles` missing / empty** (EXPLORE/METRIC `cellType`s instead) → it built a
  classic notebook. Re-prompt:
  > *"Rebuild this as a Generative app (App builder → Generative app): move the entire
  > dashboard into the generative app. Do not leave it as classic notebook cells."*
- **Confirm the split held** — SQL cells still present and **unchanged** (diff the export),
  and the app reads those dataframes rather than embedding its own queries.
- ⚠️ **Confirm no data got embedded** — search `genAppFiles` for literal arrays of the
  artifact's values. This is the artifact-specific version of the check, and it's the most
  likely way grounding silently fails. → [`data-grounding.md`](data-grounding.md) §7.

## Verify accuracy + fidelity

Three gates, all mandatory:

1. **Grounding gate** — before the build; re-verified after it (mock-constant sweep, every
   panel traces to a gated cell). [`data-grounding.md`](data-grounding.md).
2. **SQL-fidelity gate** on the native cells. [`sql-review.md`](sql-review.md).
3. **Visual-QA loop** on the render — layout/styling vs. the artifact, **numbers vs. the
   gated SQL only**. [`visual-qa-loop.md`](visual-qa-loop.md).

## When to fall back to native cells instead

Only when the notebook agent is unavailable (feature off / no Hex credits) — a capability
constraint, not a style preference. ⚠️ **Tell the customer what they lose:** the artifact's
bespoke layout, custom components and styling do not survive a grid of native cells. The
data layer is gated either way; the resemblance is what goes.
→ [`building-cells.md`](building-cells.md).

## Cheat-sheet

- `hex thread create "$(cat prompt.txt)" --project <id> --json` → `url` (hand to customer) + `thread_id`.
- `hex project export <id> -o app.yaml` → `genAppFiles` non-empty; SQL cells unchanged; **no embedded data arrays**.
- `hex thread continue <id> "<numbered fix list>"` → iterate.
- Data layer native + gated; app reads those dataframes, never re-queries, **never holds data**.
- ⚠️ Pre-build the SQL when the grounding ledger has 🎭 rows.
