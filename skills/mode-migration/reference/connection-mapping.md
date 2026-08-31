# Data connection mapping

Resolve which **Hex data connection** a migrated report's cells should query, and
decide the **critical up-front question: is it the same warehouse Mode queried, or a
different one?** That answer changes how much SQL work you owe (near-verbatim port vs.
dialect translation — see [`mode-semantics.md`](mode-semantics.md)). There's no
automatic link from Mode — match on metadata, not names or hosts. Do this per report
(step 1 of the porting loop).

## 1. Get the Mode data source's physical details

Every Mode query names a **data source** (a warehouse connection configured in the Mode
workspace). From the report export:

- `scripts/mode_fetch.py` records each query's `data_source_id` and the report's data
  sources. The Mode data-source object carries `adapter` (the warehouse type —
  `snowflake`, `redshift`, `bigquery`, `databricks`, `postgres`, …), `name`, and
  connection metadata (`database`, `host`, `account`, depending on adapter).
- The **query SQL itself** is the best signal for **table names** — they're written out
  as `db.schema.table` (or the adapter's convention) right in the query text, unlike a
  Tableau published datasource that hides them behind a proxy.

Pull: `adapter` (warehouse type), host/account, database, schema, warehouse/role.

## 2. Match to a Hex connection

`hex connection list --json` → `hex connection get <id> --json` →
`connectionDetails.<adapter>.{accountName, database, warehouse, role}`. **Match on
`type` + `database` (+ `schema`).**

## 3. Do NOT match on host

The account URL usually differs even for the same data:
```
Mode:  <account-a>.snowflakecomputing.com  /  SALES_DB . PUBLIC
Hex:   <account-b>.<region>.aws            /  sales_db
       ^ different host,  same database.  (and possibly a different SNAPSHOT — data parity is NOT guaranteed)
```

## 4. Decide — and record same-warehouse-or-not

- **Exactly one** Hex connection matches type+database → use it; state the assumption.
- **Zero or multiple** → **ask the customer** which Hex connection to target. This is the
  one genuine human gate on connections — data may live in a different account/snapshot.
- **Record `same_warehouse` in the manifest:**
  - **Same warehouse type** (Mode Snowflake → Hex Snowflake, same DB) → `same_warehouse:
    true`. The SQL **ports near-verbatim** — only Liquid → Hex params needs changing. This
    is the common, cheap case.
  - **Different warehouse type** (Mode Redshift → Hex Snowflake, etc.) → `same_warehouse:
    false`. You additionally owe a **dialect translation pass** on every query (see
    [`mode-semantics.md`](mode-semantics.md) "Dialect step"). Flag it — it's real work and
    a real fidelity risk.

## 5. Translate names 1:1 (same warehouse) or per dialect (changed warehouse)

Same warehouse → the `db.schema.table` in the Mode query is already correct; lift it.
Changed warehouse → remap identifiers + quoting/case-folding to the target dialect.
Validate reachability with the run-status oracle (wrong role/schema → `ERRORED`, not
silent).

## 6. Non-warehouse data sources — ask the customer

Not every Mode query hits a warehouse. Mode supports **uploaded CSVs**, **Google
Sheets**, and its own helper/sample datasets. If a report's data source is one of these,
the rows **aren't in a warehouse Hex can reach** — treat it like Tableau's external-file
rule: **ask the customer for the source file (or where the data now lives)** and load it
in Hex (a file upload or a Python cell), or note it as a gap. Never fabricate the data.

> Naming Hex connections to match Mode data sources makes step 2 trivial, but it's a
> **bonus**, not a requirement.
