# Build path B — a Hex generative app

One of the skill's two build paths (chosen per dashboard in SKILL.md step 4). Keep the
data layer native and gated, then have the notebook agent build a **Generative app** (a
code app — `genAppFiles` in the export) as the *presentation* layer on top of those
cells. Pairs with the **visual-QA loop** ([`visual-qa-loop.md`](visual-qa-loop.md)),
which is the only look-&-feel gate on this path.

> **When generative is the right call for Omni.** Most Omni dashboards are tile grids
> that the classic path reproduces well. Choose generative when the dashboard's value is
> in its **presentation**: heavy **markdown/HTML tiles with Mustache templating** and
> custom CSS, **custom Vega-Lite** visuals, an embedded/branded look (Omni themes, embed
> styling), a narrative "data story" layout, or a customer requirement for pixel
> fidelity over analyst-editability. The generative app is real code, so it can
> reproduce those far closer than a grid of EXPLORE cells.

> **The trade, state it up front:** analysts can't edit a generative app with clicks —
> it's code — and there's no mechanical cell-spec diff, so the render loop carries all
> of the look-&-feel verification.

## The core principle: split the layers

A Generative app has **no diff-able native SQL cells** — data logic can hide inside the
app code, which would gut the SQL-fidelity gate. So the generative layer never authors
SQL:

1. **Data layer — native + gated.** SQL cells reproducing the compiled Omni queries,
   through the full **SQL-fidelity gate** ([`sql-review.md`](sql-review.md)).
2. **Presentation layer — generative.** The app *reads the existing dataframes*; it does
   not re-query. The prompt says so explicitly.

⚠️ **Never skip step 1.** "Just prompt for a generative app" yields an app that writes
its own SQL inside code you can't cleanly diff — and for Omni that means its own guess
at the joins and fan-out handling. Gate the SQL, *then* generative-ize the presentation.

Ratios and Excel-style calculations *can* be computed in app code on this path, but keep
them in SQL anyway — that keeps every number on the dashboard inside the gate.

---

## The styling spec (drives the prompt AND the diff baseline)

One block per tile; it is what the agent builds from and what the visual-QA loop diffs
against. Extract values from the export, never eyeball them:

- **Exact title + subtitle** (verbatim).
- **Metrics + formulas** — the derivation each tile reads and the measure it shows.
- **Filter wiring** — which inputs drive this tile (and any cross-filtering).
- **Colors as hex codes** — from the tile vis config + the export's `colorPalettes`.
- **Tooltip / label fields**, **time ranges** (resolved), **number + date formats**.
- **Markdown tile content** — the text, the Mustache references resolved to the
  dataframe + column they read, and any custom CSS verbatim.
- **Layout** — the dashboard grid row-by-row with relative widths; theme colors/fonts if
  the dashboard uses a custom theme.

---

## The handoff prompt

The prompt **must open** by demanding a Generative app, or the agent defaults to a
classic notebook:

> *"Build this as a **GENERATIVE APP** (App builder → Generative app), **not** a classic
> notebook app. Read the `Migration brief` + `Styling spec` cells — they are the full spec
> for migrating an Omni dashboard into this project.*
>
> *The SQL cells already exist and are validated — **use them as the data source; do NOT
> write new SQL or re-query the warehouse.** The app reads these dataframes: `<df1>`,
> `<df2>`, …*
>
> *Build the presentation to match the Styling spec exactly: tile titles, metrics, filter
> wiring, the given colors (hex codes), label fields, time ranges, number/date formats,
> and the markdown tiles' content and styling. Reproduce the Omni dashboard's grid
> row-by-row. [If multiple dashboards:] use **tab navigation**, one tab per dashboard.*
>
> *Wire the input parameters to filter the app interactively per the spec."*

```bash
hex thread create --new-project "$(cat prompt.txt)" --json   # or --project <id> if cells exist there
```

**⚠️ Surface the returned `url` to the customer immediately.**

## Verify it actually built a Generative app

```bash
hex project export <project_id> -o app.yaml
```

- **`genAppFiles` present and non-empty** → Generative. ✅
- **Missing / empty** (EXPLORE/METRIC `cellType`s instead) → it built classic. Re-prompt:
  > *"Rebuild this as a Generative app (App builder → Generative app): move the entire
  > dashboard into the generative app. Do not leave it as classic notebook cells."*
- **Split held** — SQL cells present and **unchanged**; the app reads those dataframes
  rather than embedding its own queries. If it authored SQL, `continue` it to read the
  existing cells.

## Verify accuracy + fidelity (two gates)

1. **SQL-fidelity gate** (incl. the Omni result-parity check) — [`sql-review.md`](sql-review.md).
2. **Visual-QA loop on the render** — the rendered app is how you verify look & feel:
   headless screenshot → panel-by-panel diff vs. the Omni PNG → surgical fix batch →
   repeat → [`visual-qa-loop.md`](visual-qa-loop.md).

## Cheat-sheet

- `hex thread create "$(cat prompt.txt)" --project <id> --json` → `url` (hand to customer) + `thread_id`.
- `hex project export <id> -o app.yaml` → `genAppFiles` non-empty; SQL cells unchanged.
- `hex thread continue <id> "<numbered fix list>"` → iterate (form fix + visual-QA loop).
- Data layer native + gated; app reads those dataframes, never re-queries.
