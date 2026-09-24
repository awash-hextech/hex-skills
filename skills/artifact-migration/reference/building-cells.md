# Hand-build native cells (FALLBACK path only)

> ⚠️ **This is the fallback, not the default.** Use it **only** when the notebook agent is
> unavailable — the headless-agent-threads feature is off, or there are no Hex credits.
> That's a capability constraint, not a style preference.
> → [`build-generative-app.md`](build-generative-app.md) is the default build.

> ⚠️ **Tell the customer what they lose.** More than in any sibling skill: the source here
> *is* a React app, so the generative path reproduces it closely. A grid of native
> EXPLORE/METRIC cells **will not resemble the artifact** — bespoke layout, custom
> components, and most styling do not survive. The data is gated either way; the
> resemblance is what goes. Say this before building, not at QA.

**The grounding gate still applies, unchanged.** Nothing in this path relaxes it — every
number still traces to a real warehouse column, and Drop/Stub dispositions still hold.
→ [`data-grounding.md`](data-grounding.md).

## The path

1. **Ground the data and gate the SQL first** — same as the default path. Build the SQL
   derivation cells, validate with the oracle, run the full
   [`sql-review.md`](sql-review.md) gate. Charts come after gated SQL, never before.
2. **Author the parameter + companion cells in YAML.** `hex cell create` makes only
   code/sql/markdown, so INPUT (parameter) cells and connection-less dataframe-SQL
   companions (`dataFrameCell: true`, `dataConnectionId: null` — a KPI or ratio reading a
   shared dataframe) need a YAML round-trip.
   ⚠️ Input cells must be **upstream** of every cell that reads them, in the notebook and
   in `cells[]`. → [`gotchas.md`](gotchas.md).
3. **Clone-and-override from `templates/`.** Start from the closest template and override
   only what differs — don't author a cell config from scratch.

   | Template | Use for |
   |---|---|
   | `metric.json` | a KPI / big-number tile (fed a 1-row SQL cell) |
   | `explore_bar.json` | categorical comparison |
   | `explore_line.json` | a time series |
   | `explore_area.json` | stacked/filled time series |
   | `explore_scatter.json` | two-measure relationship |
   | `explore_pie.json` | part-to-whole (sparingly) |
   | `explore_pivot.json` | a table / crosstab |
   | `explore_faceted.json` | small multiples |
   | `_filter_snippet.json` | a filter block to paste into an EXPLORE config |

   Per chart, set from the styling spec: `cellLabel` + `config.title` (the artifact's exact
   string), `dataframe`, the `spec.fields` encodings, `colorMappings` (**the artifact's hex
   codes**), sort, and `displayFormat` (currency/percent/decimals, date `truncUnit`).
4. **Validate the YAML before importing.** Check against the Hex JSON schema —
   `https://static.hex.site/hex-file-schema.json` (the RedHat YAML VS Code extension gives
   inline validation). A malformed cell config imports "successfully" and renders blank.
5. **Register the data connection** under `sharedAssets.dataConnections` — a project
   assembled purely in YAML doesn't get it automatically, and every SQL cell then
   references a connection the project lacks (run ERRORs, no useful detail).
6. **Import, run, then build the app layout.** `hex project import f.yaml` → `hex project
   run` (async; poll) → export again and edit `appLayout` from the fresh export's cellIds.
   Mirror the artifact's CSS structure onto the 0–120 grid; leave chart heights `null`.
   ⚠️ Keep the artifact-source reference cell and the raw SQL cells **out** of the layout.
   → [`gotchas.md`](gotchas.md) "App layout".

## Mapping artifact panels → native cells

| Artifact panel | Native cell |
|---|---|
| KPI / big number | `METRIC` over a 1-row SQL cell |
| Bar / column chart | `EXPLORE` (bar) |
| Line / area chart | `EXPLORE` (line/area), base axis `dataType: DATE` + `truncUnit` |
| Scatter | `EXPLORE` (scatter) |
| Donut / pie | `EXPLORE` (pie) |
| Table / data grid | `EXPLORE` (pivot/table) |
| Select / slider / date picker | `INPUT` cell (upstream) |
| Tabs | `appLayout.tabs[]` |
| Static copy | Markdown cell |
| Image from the asset store | Markdown cell via **file upload** (never a hotlinked artifact URL) |
| Bespoke D3 / inline-SVG visual | ⚠️ No native equivalent — Python cell (best effort) or a named gap |
| **Stub panel** (no data source) | A Markdown cell stating "No data source connected" — **never** a chart with sample values |

## QA on this path

- **The SQL gate runs as usual**, including the **mock-constant sweep**
  ([`sql-review.md`](sql-review.md) §5) — native cells are just as capable of carrying a
  hardcoded artifact value.
- **There's a gate this path gains:** native chart specs live in the exported YAML, so
  chart type, encodings, colors and formats can be **diffed mechanically** against the
  styling spec before anything renders. Do that — it's free and it's exact.
- **The visual gate is human.** This agent can't render native cells, so hand the customer
  the project link + the artifact side-by-side.
  ⚠️ Brief them the same way as the default path: *layout will differ (that's this path's
  cost), and the numbers are supposed to differ (those are now real)*.
  → [`visual-qa-loop.md`](visual-qa-loop.md).
