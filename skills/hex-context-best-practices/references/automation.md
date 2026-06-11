# Automating context management (CLI, API, and coding agents)

Hex context work can happen from the terminal in **two ways**:

1. **`hex` CLI** — native subcommands for guides and suggestions (and projects/cells if you have the
   general Hex skill).
2. **REST API via the terminal** — `curl`, a short Python script, or your coding agent running
   `requests`. There is **no** `hex endorse` command, but Claude Code, Codex, or Cursor can still
   apply endorse lists for you by calling the API.

When someone wants to "manage context from the terminal" or "have Claude Code endorse tables," read
this file and **offer to run the API calls** (after confirming token + connection IDs).

Fetch live details from `references/hex-docs.md` before giving setup steps.

---

## Quick map: context asset → how to automate

| Context asset | UI | `hex` CLI | REST API (curl / script) | MCP |
| --- | --- | --- | --- | --- |
| **Endorse** tables/schemas/DBs | Data browser, Context Studio | ❌ | ✅ `UpdateDataConnectionSchema` | ❌ |
| **Exclude from AI** | Data browser toggle | ❌ | ⚠️ UI today; not on endorsements API page | ❌ |
| **Endorse** projects | Context Studio | ❌ | ✅ `UpdateProject` | ❌ |
| **Endorse** semantic models | Context Studio | ❌ | ✅ `UpdateSemanticProject` | ❌ |
| **Workspace context & guides** | Context Studio Workbench | ✅ `hex guide preview` / `publish` | ✅ Guides draft/publish endpoints | ❌ |
| **Suggestions** (triage loop) | Context Studio | ✅ `hex suggestion list/get/update` | ❌ (CLI in docs) | ❌ |
| **Descriptions** | Data browser, dbt sync | ❌ | ❌ (not in public API ref) | ❌ |
| **Ask agent / Threads** | Threads | ❌ | Threads list/get | ✅ `create_thread`, etc. |

**Roles:** endorsements and publishing guides require **Admin or Manager**. Team/Enterprise plans.

**Exclude from AI** steers the agent away from tables in normal discovery; it is not a security
boundary (users can still @mention excluded tables). For access control, use warehouse permissions.

---

## Authentication (shared by CLI and API)

### Hex CLI

```bash
hex auth login                    # browser OAuth; stores credentials in keyring
hex auth status                 # verify login + active profile

# CI / scripting
export HEX_API_TOKEN='hxtw_...'  # or personal hxtp_...
hex auth login --token-from-env HEX_API_TOKEN
```

Custom domains (EU, single-tenant): `hex auth login -H https://eu.hex.tech`

### REST API

- **Base URL:** `https://app.hex.tech/api/v1` (replace host for custom domains).
- **Header:** `Authorization: Bearer <token>`
- **Tokens:** personal (`hxtp_…`, Editor+) or workspace (`hxtw_…`, Admin). Create under
  Settings → API keys. Workspace tokens for data connections need **write** scope on Data
  connections. Guides need **Guides read and write** scope.
- **Never commit tokens.** Use env vars (`HEX_API_TOKEN`) or your secret manager.

The API executes as the token owner — same permissions as that user in the UI.

---

## Endorse tables and schemas via API (from the terminal)

Hex documents bulk endorsement via API on the
[Endorsements](https://learn.hex.tech/docs/agent-management/context-management/endorsements-in-context-studio)
page. Endpoints:

| Endpoint | Path | Objects |
| --- | --- | --- |
| `UpdateDataConnectionSchema` | `PATCH /v1/data-connections/{dataConnectionId}/schema` | DATABASE, SCHEMA, TABLE |
| `UpdateProject` | `PATCH /v1/projects/{projectId}` | Projects |
| `UpdateSemanticProject` | `PATCH /v1/semantic-projects/{semanticProjectId}` | Semantic datasets/views |

Batch updates are atomic — if one row fails validation, nothing is applied.

### 1. Get your data connection ID

**CLI:**

```bash
hex connection list --json | jq '.values[] | {name, id}'
```

**API:**

```bash
curl -s -H "Authorization: Bearer $HEX_API_TOKEN" \
  "https://app.hex.tech/api/v1/data-connections" | jq '.values[] | {name, id}'
```

### 2. Endorse tables (curl)

`status` is the **status name** configured in your workspace (e.g. `Endorsed`, `Approved`,
`Trusted`). Check Context Studio → Endorsements or your workspace status settings. Pass `null` to
clear a status.

```bash
CONNECTION_ID="497f6eca-6276-4993-bfeb-53cbbbba6f08"

curl -s -X PATCH \
  -H "Authorization: Bearer $HEX_API_TOKEN" \
  -H "Content-Type: application/json" \
  "https://app.hex.tech/api/v1/data-connections/${CONNECTION_ID}/schema" \
  -d '{
    "updates": [
      {"type": "SCHEMA", "name": "analytics", "status": "Endorsed"},
      {"type": "TABLE", "name": "analytics.dim_customers", "status": "Endorsed"},
      {"type": "TABLE", "name": "analytics.stg_orders", "status": null}
    ]
  }'
```

**Naming:** `DATABASE` uses the simple name; `SCHEMA` and `TABLE` use qualified names
(e.g. `schema.table` or `database.schema.table` depending on your warehouse — match what you see
in the Data browser).

### 3. Endorse a project

```bash
PROJECT_ID="5a8591dd-4039-49df-9202-96385ba3eff8"

curl -s -X PATCH \
  -H "Authorization: Bearer $HEX_API_TOKEN" \
  -H "Content-Type: application/json" \
  "https://app.hex.tech/api/v1/projects/${PROJECT_ID}" \
  -d '{"status": "Endorsed"}'
```

### 4. Bulk endorse from a list (Python — good for coding agents)

After the context-architect drafts an endorse list, a coding agent can turn it into API calls:

```python
import os
import requests

BASE = os.environ.get("HEX_API_BASE", "https://app.hex.tech/api/v1")
TOKEN = os.environ["HEX_API_TOKEN"]
CONNECTION_ID = os.environ["HEX_CONNECTION_ID"]
STATUS = os.environ.get("HEX_ENDORSE_STATUS", "Endorsed")

# From architect output: qualified table names
TABLES_TO_ENDORSE = [
    "analytics.dim_customers",
    "analytics.fct_orders",
]

updates = [{"type": "TABLE", "name": t, "status": STATUS} for t in TABLES_TO_ENDORSE]

resp = requests.patch(
    f"{BASE}/data-connections/{CONNECTION_ID}/schema",
    headers={"Authorization": f"Bearer {TOKEN}"},
    json={"updates": updates},
    timeout=60,
)
print(resp.status_code, resp.text)
```

**Coding-agent workflow:** draft endorse list → user approves → agent runs script or curl → verify in
Context Studio.

---

## Guides and workspace context (`hex` CLI)

See the [Guides doc](https://learn.hex.tech/docs/agent-management/context-management/guides).

**Prereqs:** `hex_context.config.json` in your guides repo; reserved path `hex.md` = workspace
context.

```bash
hex guide preview --json
# → previewLink, previewId

PREVIEW=$(hex guide preview --json)
PREVIEW_ID=$(echo "$PREVIEW" | jq -r '.previewId')
hex guide publish "$PREVIEW_ID"
```

**GitHub:** `hex-inc/action-context-toolkit` publishes on merge to main.

---

## Suggestions loop (`hex` CLI)

See `references/ask-hex.md` for the full triage loop.

```bash
hex suggestion list --json
hex suggestion get <suggestion_id>
hex suggestion update <id> --status COMPLETED   # or DISMISSED
```

Pair with guide publish or API endorsements depending on the suggested fix.

---

## What coding agents can do for you

| Task | Agent approach |
| --- | --- |
| Bulk endorse golden tables | Draft list → `PATCH .../schema` via curl/Python |
| Publish a guide | `hex guide preview` → review link → `hex guide publish` |
| Triage context gaps | `hex suggestion list` → draft fixes → apply → mark COMPLETED |
| Discover connection IDs | `hex connection list --json` or `GET /data-connections` |
| Exclude staging tables | Data browser UI today; do not promise API unless verified |

Install Hex's bundled CLI skill for project/cell work: `hex install agent-skill --claude`

**MCP limitation:** the Hex MCP server (`search_projects`, Threads tools) cannot endorse or publish
guides — use CLI or API for that.

---

## Docs to fetch before UI or API steps

Listed in `references/hex-docs.md`. Key links:

- [CLI](https://learn.hex.tech/docs/api-integrations/cli)
- [Public API overview](https://learn.hex.tech/docs/api-integrations/api/overview)
- [API reference](https://learn.hex.tech/docs/api-integrations/api/reference)
- [Endorsements (+ API)](https://learn.hex.tech/docs/agent-management/context-management/endorsements-in-context-studio)
- [Guides (+ CLI publish)](https://learn.hex.tech/docs/agent-management/context-management/guides)
- [Suggestions (+ CLI)](https://learn.hex.tech/docs/agent-management/suggestions)
