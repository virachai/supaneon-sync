# Operational Runbook: supaneon-sync

This document outlines the operational procedures for managing the `supaneon-sync` disaster recovery system. It is intended for DevOps engineers and on-call staff responding to incidents or performing maintenance.

---

## 🛡️ Database Roles Setup

To follow the principle of least privilege, create dedicated roles for backup and restore operations instead of using the superuser.

### 1. MongoDB Access (Primary)
Ensure the `MONGODB_SRV_URL` provides a user with at least `read` privileges on all collections in the target database.

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

**Scenario:** MongoDB (Primary) is down or inaccessible, and you need to query the backup in Neon (Standby).

### 1. Identify the Latest Healthy Backup
Since backups are timestamped branches, find the most recent one.

**Via CLI (Local):**
```bash
# This command automatically finds the latest branch starting with 'backup-'
supaneon-sync config  # Check env first
python -m supaneon_sync.neon list-branches
```

**Via Neon Console:**
1. Log in to the [Neon Console](https://console.neon.tech).
2. Go to **Branches**.
3. Look for the most recent branch named `backup-YYYYMMDDTHHMMSSZ`.

### 2. Verify Operation (Optional but Recommended)
Before switching traffic, ensure the branch works.
1. Connect via a SQL client using the branch's connection string.
2. Run a query: `SELECT * FROM "your_collection" LIMIT 1;`
3. Note that the data is stored in the `data` column as `JSONB`.

### 3. Application Access
Update your application's logic or environment variable to point to the Neon branch. Since the data is in Postgres, you will need to use a Postgres driver and queries that access the JSONB data.

---

## 🛠️ Manual Operations

### Triggering an Immediate Backup
If you suspect an issue or are about to make risky changes, trigger a backup manually.

**Via GitHub Actions:**
1. Go to **Actions** -> **Backup**.
2. Click **Run workflow**.

**Via CLI:**
```bash
export MONGODB_SRV_URL="..."
export NEON_API_KEY="..."
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
1.  **MongoDB Connection Issues:**
    *   Check `MONGODB_SRV_URL`. Ensure the cluster is accessible.
2.  **Neon API Limits:**
    *   Free tier project limit reached? (Max branches?).
3.  **Authentication:**
    *   Check if `NEON_API_KEY` or `MONGODB_SRV_URL` credentials are valid.

### "Restore Test Failed" Notification
**Investigation:**
1.  Inspect the logs to see if it was a *connectivity* error or a schema verification failure.
2.  Check for the presence of the `data` column in the created tables.

---

## 🔐 Maintenance

### Rotating Credentials
1.  **MongoDB Password Change:**
    *   Update `MONGODB_SRV_URL` in GitHub Secrets immediately.
2.  **Neon API Key Rotation:**
    *   Generate a new key in the Neon Console and update `NEON_API_KEY` in GitHub Secrets.

---

## 📞 Escalation
*   **MongoDB Status:** [status.mongodb.com](https://status.mongodb.com/)
*   **Neon Status:** [status.neon.tech](https://status.neon.tech/)
