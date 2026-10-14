# Data connection mapping

Resolve which **Hex data connection** a migrated dashboard's SQL cells should query, and
decide up front: **is it the same warehouse Omni queried, or a different one?** That
answer decides whether the compiled SQL can be checked by **exact result parity**
against Omni ([`sql-review.md`](sql-review.md) §4) and whether you owe a dialect pass.
There's no automatic link from Omni — match on metadata, not names or hosts.

## 1. Get the Omni connection's physical details

In Omni, every **model** sits on exactly one **connection**, and every dashboard query
names its `modelId`. So the chain is *dashboard → query `modelId` → model → connection*.

- `scripts/omni_fetch.py` saves the document record (its `connectionId`), each tile's
  `modelId` (`queries.json`), the export's `workbookModel.connection_id`, and the full
  connection list (`connections.json` — dialect, database, default schema per
  connection). Join them on the connection id.
- The **model YAML** names the physical tables: each view's `schema` + `table_name`
  (or a `sql` derived-table definition). That's the best signal for which database and
  schema the tiles read — no hidden proxy like a Tableau published datasource.

Pull: dialect (Snowflake, BigQuery, Databricks, Redshift, Postgres, …), host/account,
database, default schema, and any role/warehouse.

## 2. Match to a Hex connection

`hex connection list --json` → `hex connection get <id> --json` →
`connectionDetails.<adapter>.{accountName, database, warehouse, role}`. **Match on
`type` + `database` (+ `schema`).**

## 3. Do NOT match on host

The account URL usually differs even for the same data (different account, region, or
snapshot). Same database name ≠ same data — parity is not guaranteed until the
result-parity check says so.

## 4. Decide — and record same-warehouse-or-not

- **Exactly one** Hex connection matches type + database → use it; state the assumption.
- **Zero or several** → **ask the customer.** This is the one genuine human gate on
  connections. Batch the question across the whole wave.
- Record in the manifest:
  - **`same_warehouse: true`** — same dialect and database. The compiled SQL runs in
    Omni's dialect, and **result parity against Omni should tie exactly**.
  - **`same_warehouse: false`** — dialect change (e.g. Omni on BigQuery → Hex on
    Snowflake). Compile to the target dialect, and expect parity to need explanation.

## 5. Names

Same warehouse → the `schema.table_name` in each view is already correct; use it.
Changed warehouse → remap identifiers + quoting/case-folding. Validate reachability with
the run-status oracle (wrong role/schema → `ERRORED`, not silent).

## 6. Non-warehouse data — ask the customer

Omni **spreadsheet tiles** and **file uploads** (CSV uploads attached to a dashboard —
the export's `fileUploads`) have no warehouse rows behind them. Ask the customer for the
source (or where it now lives), load it in Hex as a file or a table, or record it as a
gap. Never fabricate the data. The raw upload in the export is a fallback source **only**
with the customer's OK — it's a point-in-time copy.
