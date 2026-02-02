---
trigger: always_on
glob:
description:
---
- Do not use PostgreSQL CLI tools (e.g., `psql`, `pg_dump`) on the local machine as they are not installed.
- The `supabase` CLI is available and can be used.
- Prefer using Supabase MCP tools or direct API interactions for database operations when CLI tools are not available or appropriate.
