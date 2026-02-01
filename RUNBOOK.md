# Operational Runbook: supaneon-sync

This document outlines the operational procedures for managing the `supaneon-sync` disaster recovery system. It is intended for DevOps engineers and on-call staff responding to incidents or performing maintenance.

---

## 🛡️ Database Roles Setup

To follow the principle of least privilege, create dedicated roles for backup and restore operations instead of using the superuser.

### 1. Create `backup_user` (Primary Database)
Run this on your **Supabase** (Primary) database. This role allows reading schema and data for backups.

```sql
-- 1. Create the user
CREATE ROLE backup_user WITH LOGIN PASSWORD 'your_secure_password';

-- 2. Grant connect privileges
GRANT CONNECT ON DATABASE postgres TO backup_user;

-- 3. Grant usage on schemas (often just public, or add others like auth)
GRANT USAGE ON SCHEMA public TO backup_user;

-- 4. Grant read-only access to all tables and sequences
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_user;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO backup_user;

-- 5. Ensure future tables are also readable
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO backup_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON SEQUENCES TO backup_user;
```

> **Note:** If you have multiple schemas, repeat steps 3-5 for each schema.

### 2. Create `restore_user` (Recovery Database)
Run this on your **Neon** (Standby) database if you plan to use a restricted user for testing restores.
*Note: `pg_restore` often requires essentially superuser privileges to restore roles, extensions, and accurate ownership. For full fidelity, you may need to use the `neondb_owner` role provided by Neon.*

If you wish to use a restricted role for data-only restores:

```sql
-- 1. Create the user
CREATE ROLE restore_user WITH LOGIN PASSWORD 'your_secure_password';
-- Ideally, make it a member of the owner role if possible, or grant CREATE
GRANT CONNECT ON DATABASE neondb TO restore_user;
GRANT CREATE ON SCHEMA public TO restore_user;
```

---

## 🚨 Disaster Recovery (Failover)

**Scenario:** Supabase (Primary) is down or inaccessible, and you need to switch traffic to Neon (Standby).

### 1. Identify the Latest Healthy Backup
Check the status of the latest GitHub Actions run or query the Neon API.
Since backups are timestamped branches, find the most recent one.

**Via CLI (Local):**
```bash
# This command automatically finds the latest branch starting with 'backup-'
supaneon-sync config  # Check env first
python -m supaneon_sync.neon_client list-branches --filter "backup-"
```

**Via Neon Console:**
1. Log in to the [Neon Console](https://console.neon.tech).
2. Go to **Branches**.
3. Look for the most recent branch named `backup-YYYYMMDDTHHMMSSZ`.

### 2. Verify Operation (Optional but Recommended)
Before switching traffic, ensure the branch works.
1. Connect via a SQL client using the branch's connection string.
2. Run a quick query: `SELECT count(*) FROM crucial_table;`

### 3. Switch Application Traffic
Update your application's environment variable to point to the Neon branch.

*   **Old `DATABASE_URL`**: `postgresql://user:pass@supabase-host:5432/postgres?sslmode=require`
*   **New `DATABASE_URL`**: `postgresql://user:pass@neon-host:5432/neondb?sslmode=require`

> **Note:** Use the "Pooled Connection" string from Neon for high-connection workloads (serverless apps).

### 4. Post-Failover
*   The application is now running against the read-write Neon branch.
*   **Warning:** Data written to this branch is *diverging* from the (down) Supabase instance.
*   **Recovery:** When Supabase returns, you will need to migrate data *back* or choose to stay on Neon permanently.

---

## 🛠️ Manual Operations

### Triggering an Immediate Backup
If you suspect an issue or are about to make risky changes, trigger a backup manually.

**Via GitHub Actions:**
1. Go to **Actions** -> **Backup Database**.
2. Click **Run workflow** -> **Run workflow**.

**Via CLI:**
```bash
export SUPABASE_DATABASE_URL="..."
export NEON_API_KEY="..."
supaneon-sync backup-run
```

### Manual Restore Test
To verify the system's integrity without waiting for the scheduled job:

**Via GitHub Actions:**
1. Go to **Actions** -> **Restore Test**.
2. Click **Run workflow**.

**Via CLI:**
```bash
supaneon-sync restore-test
```

---

## 🔧 Troubleshooting

### "Backup Failed" Notification
**Symptoms:** GitHub Action `backup.yml` fails.
**Common Causes:**
1.  **Supabase Connection Issues:**
    *   Check `SUPABASE_DATABASE_URL`. Ensure the project isn't paused.
    *   Verify `sslmode=require` is present.
2.  **Neon API Limits:**
    *   Free tier project limit reached? (Max branches?).
    *   Check if `NEON_API_KEY` is valid.
3.  **Schema Mismatch:**
    *   `pg_dump` version mismatch (rare if using standard images).

**Resolution:**
*   Check the Action logs for specific error messages.
*   Run `validate-config` locally to check credentials.

### "Restore Test Failed" Notification
**Symptoms:** `restore-test.yml` fails.
**Gravity:** **HIGH**. This means your backups might be corrupt.
**Investigation:**
1.  **Do not delete the failed branch.** The system attempts to clean up, but check if `debug-restore-*` branches exist.
2.  Inspect the logs to see if it was a *connectivity* error (transient) or *data* error (corruption).
3.  Try running a manual restore test.

---

## 🔐 Maintenance

### Rotating Credentials
1.  **Supabase Password Change:**
    *   Update `SUPABASE_DATABASE_URL` in GitHub Secrets immediately.
    *   The next backup will fail if this is not done.
2.  **Neon API Key Rotation:**
    *   Generate new key in Neon Console.
    *   Update `NEON_API_KEY` in GitHub Secrets.
    *   Revoke old key.

3.  **Neon DB Password:**
    *   This is required for `pg_restore` and is passed via `NEON_DB_PASSWORD` in GitHub Secrets.
    *   If you rotate the `neondb_owner` password or the user you are using (`NEON_DB_USER` env, defaults to `neondb_owner`), update the secret immediately.

### Cleaning Up Old Branches
Currently, the system does not auto-delete old backup branches (to prevent accidental data loss).
**Periodic Task:**
1.  Review old `backup-YYYY...` branches in Neon.
2.  Delete branches older than X days if no longer needed.
   ```bash
   # (Future automated script placeholder)
   ```

---

## 📞 Escalation
*   **Supabase Status:** [status.supabase.com](https://status.supabase.com/)
*   **Neon Status:** [status.neon.tech](https://status.neon.tech/)
