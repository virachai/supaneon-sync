# supaneon-sync

**Production-grade Supabase to Neon logical backup and disaster recovery automation.**

`supaneon-sync` is a security-first tool designed to automate logical backups from a primary Supabase (PostgreSQL) database to a standby Neon (PostgreSQL) database. Schemas are replicated into timestamped Neon schemas, ensuring you have an always-ready, verifiable failover target.

---

## 🚀 Key Features

*   **Supabase to Neon Sync**: Automatically dumps Supabase database and restores to timestamped Neon schemas.
*   **Immutable Backups**: Creates timestamped schemas (`backup_YYYYMMDDTHHMMSSZ`) that are never modified.
*   **Verifiable Reliability**: Includes automated **restore testing** that validates backups by running integrity checks.
*   **Schema Transformation**: Automatically remaps Supabase roles and schemas to work in Neon.
*   **Stateless**: Runs as a CLI or GitHub Action; no long-running servers or daemons required.

## 🛠️ Architecture

The system follows a layered architecture to ensure reliability and security:

1.  **Backup**: Uses Supabase CLI to dump the database, transforms SQL to remap schemas and roles, then restores into a timestamped Neon schema.
2.  **Schema Strategy**:
    *   `public`: Default Neon schema for application use.
    *   `backup_YYYYMMDDTHHMMSSZ`: Timestamped backup schemas, rotated to keep the 6 most recent.
3.  **Security Transforms**: Automatically redacts connection strings from logs and enforces SSL on both source and destination connections.

## 📋 Prerequisites

*   Python 3.11+
*   **Supabase CLI** installed and configured
*   A **Supabase** project (Primary).
*   A **Neon** project (Standby/Backup target).

## 📦 Installation

To install the package locally:

```bash
git clone https://github.com/virachai/supaneon-sync.git
cd supaneon-sync
pip install -e .
```

To install development dependencies:

```bash
pip install -e .[dev]
```

## ⚙️ Configuration

The tool relies entirely on environment variables:

| Variable | Description | Required |
| :--- | :--- | :---: |
| `SUPABASE_DATABASE_URL` | Connection string for your Supabase database. Must include `sslmode=require`. | ✅ |
| `NEON_DATABASE_URL` | Connection string for your Neon database. Must include `sslmode=require`. | ✅ |
| `NEON_API_KEY` | Your Neon API Key for managing branches (optional). | ❌ |
| `NEON_PROJECT_ID` | The ID of the Neon project to use as the destination (optional). | ❌ |

## 💻 Usage

The `supaneon-sync` CLI:

### 1. Validate Configuration
Checks that environment variables are correctly set.

```bash
supaneon-sync validate-config
```

### 2. Run Backup
Dumps Supabase database and restores it into a timestamped Neon schema.

```bash
supaneon-sync backup-run
```

### 3. Test Restore (Health Check)
Verifies the integrity of your latest backup.

```bash
supaneon-sync restore-test
```

## 🤖 Automation (GitHub Actions)

*   **`backup.yml`**: Runs daily at 02:00 UTC.
*   **`restore-test.yml`**: Runs daily at 03:30 UTC.

To enable these, add your `SUPABASE_DATABASE_URL`, `NEON_DATABASE_URL`, etc., to your GitHub Repository Secrets.

## 📄 License

This project is licensed under the MIT License.
