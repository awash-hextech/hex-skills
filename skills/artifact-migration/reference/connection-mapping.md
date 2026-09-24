# Data connection mapping

Resolve which **Hex data connection** the migrated app's cells should query.

> **This is not a lookup — it's a discovery conversation.** Tableau and Mode each name a
> source connection you can match on metadata. **An artifact names nothing.** There is no
> adapter, no host, no `db.schema.table` in the source to match against — usually there's
> no warehouse involved at all. So this step doesn't *resolve* a connection so much as
> *establish* one, and it follows directly from the grounding gate
> ([`data-grounding.md`](data-grounding.md)), which is where the tables get named.

## 1. Get the tables from the grounding ledger

The ledger's **Target table(s)** column is the input to this step. If it's empty, you're
not ready — go back and finish grounding. The ordering matters: *grounding names the
tables, and the tables imply the connection* — never the other way round, or you'll end up
fishing for tables inside whichever connection you picked first.

Occasionally the source does carry a hint worth checking:

- A **fetch URL** pointing at an internal API or a warehouse proxy.
- A **comment or a label** naming a table, a dashboard, or a system (`// from the FIN
  export`). ⚠️ A hint, never provenance — confirm with the customer and against the
  warehouse. → [`data-grounding.md`](data-grounding.md) §2.
- A **published data file** in the artifact (`data.json`, a bundled `.csv`) whose column
  names match a real table.

## 2. Match to a Hex connection

```bash
hex connection list --json
hex connection get <id> --json    # connectionDetails.<adapter>.{accountName, database, warehouse, role}
```

Match on whether the connection **reaches the tables the ledger names** — type + database
(+ schema). Confirm reachability with the run-status oracle rather than assuming: a wrong
role or schema gives `ERRORED`, not silence. → [`gotchas.md`](gotchas.md).

## 3. Decide

- **Exactly one** connection reaches the named tables → use it; state the assumption.
- **Zero or multiple** → **ask the customer.** This is a genuine human gate.
- ⚠️ **Never assume Snowflake.** Read the adapter off the connection and write that
  dialect's SQL.

Record `connection_id` in the manifest. There is no `same_warehouse` flag here — nothing is
being ported from another warehouse, so **every** query is authored fresh against this
connection's dialect. (That's also why the SQL gate leans harder on independent
re-derivation than on textual diffing — there's no source query text to diff against.)

## 4. When no connection reaches the data

Three outcomes, in order of preference:

1. **The data exists but isn't connected** → the customer adds a Hex connection. Normal
   setup; pause the migration until it's there.
2. **The data exists outside the warehouse** (a spreadsheet, a CSV, an API, artifact-DB
   rows) → land it: a Hex **file upload** for small static sets, a **Python cell** using
   **Hex secrets** for an API, or have the customer load it to the warehouse (the right
   answer for anything recurring). Artifact-DB rows always take this path →
   [`data-grounding.md`](data-grounding.md) §4.
3. **The data doesn't exist** → **Drop** or **Stub** the panel. Never fabricate it, and
   never let "we'll wire it up later" ship as numbers that look live.

> Unlike the BI migrations, outcome 3 is **common and expected** here — an artifact is
> often a design for a dashboard whose data was never sourced. Say so plainly; it's a
> useful finding, not a failure.
