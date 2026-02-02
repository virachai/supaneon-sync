# Operational Runbook: supaneon-sync

This document outlines the operational procedures for managing the `supaneon-sync` disaster recovery system. It is intended for DevOps engineers and on-call staff responding to incidents or performing maintenance.

---

## 🛡️ Database Roles Setup

To follow the principle of least privilege, create dedicated roles for backup and restore operations instead of using the superuser.

### 1. Supabase Access (Primary)
Ensure the `SUPABASE_DATABASE_URL` provides a user with at least `read` privileges on all tables in the target database. This is used by the Supabase CLI to dump the database.

### 2. Create `restore_user` (Recovery Database)
Run this on your **Neon** (Standby) database if you plan to use a restricted user for testing restores.

```sql
-- 1. Create the user
CREATE ROLE restore_user WITH LOGIN PASSWORD 'your_secure_password';
-- Ideally, make it a member of the owner role if possible, or grant CREATE
GRANT CONNECT ON DATABASE neondb TO restore_user;
GRANT CREATE ON SCHEMA public TO restore_user;
```

---

## 🚨 Disaster Recovery (Failover)

**Scenario:** Supabase (Primary) is down or inaccessible, and you need to query the backup in Neon (Standby).

### 1. Identify the Latest Healthy Backup
Since backups are timestamped schemas, find the most recent one.

**Via CLI (Local):**
```bash
# This command automatically finds the latest schema starting with 'backup_'
supaneon-sync config  # Check env first
# Connect to Neon and query schemas
```

**Via Neon Console or SQL Client:**
1. Connect to your Neon database.
2. Run: `SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'backup_%' ORDER BY schema_name DESC LIMIT 1;`
3. Look for the most recent schema named `backup_YYYYMMDDTHHMMSSZ`.

### 2. Verify Operation (Optional but Recommended)
Before switching traffic, ensure the backup schema works.
1. Connect via a SQL client using Neon's connection string.
2. Run a query: `SELECT * FROM backup_YYYYMMDDTHHMMSSZ.your_table LIMIT 1;`
3. The backup contains full table structures from Supabase.

### 3. Application Access
Update your application's logic or environment variable to point to the Neon backup schema. Since both Supabase and Neon are PostgreSQL, your existing queries should work with minimal changes (just update the schema prefix).

---

## 🛠️ Manual Operations

### Triggering an Immediate Backup
If you suspect an issue or are about to make risky changes, trigger a backup manually.

**Via GitHub Actions:**
1. Go to **Actions** -> **Backup**.
2. Click **Run workflow**.

**Via CLI:**
```bash
export SUPABASE_DATABASE_URL="..."
export NEON_DATABASE_URL="..."
supaneon-sync backup-run
```

### Manual Restore Test
To verify the system's integrity:

**Via CLI:**
```bash
supaneon-sync restore-test
```

---

## 🔧 Troubleshooting

### "Backup Failed" Notification
**Common Causes:**
1.  **Supabase Connection Issues:**
    *   Check `SUPABASE_DATABASE_URL`. Ensure the database is accessible.
    *   Verify Supabase CLI is installed and configured.
2.  **Neon Connection Issues:**
    *   Check `NEON_DATABASE_URL` and ensure SSL mode is set correctly.
3.  **Authentication:**
    *   Check if `SUPABASE_DATABASE_URL` and `NEON_DATABASE_URL` credentials are valid.
4.  **Schema Limits:**
    *   Check if Neon has schema or storage limits reached.

### "Restore Test Failed" Notification
**Investigation:**
1.  Inspect the logs to see if it was a *connectivity* error or a schema verification failure.
2.  Check if the backup schema exists and contains the expected tables.
3.  Verify that schema transformations (role remapping, extensions) completed successfully.

---

## 🔐 Maintenance

### Rotating Credentials
1.  **Supabase Password Change:**
    *   Update `SUPABASE_DATABASE_URL` in GitHub Secrets immediately.
2.  **Neon Password Change:**
    *   Update `NEON_DATABASE_URL` in GitHub Secrets immediately.
3.  **Neon API Key Rotation (if used):**
    *   Generate a new key in the Neon Console and update `NEON_API_KEY` in GitHub Secrets.

---

## 📞 Escalation
*   **Supabase Status:** [status.supabase.com](https://status.supabase.com/)
*   **Neon Status:** [status.neon.tech](https://status.neon.tech/)
