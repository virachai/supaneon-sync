# supaneon-sync

**Production-grade MongoDB to Neon logical backup and disaster recovery automation.**

`supaneon-sync` is a security-first tool designed to automate logical backups from a primary MongoDB database to a standby Neon (PostgreSQL) database. Collections are stored as JSONB tables, ensuring you have an always-ready, verifiable failover target.

---

## 🚀 Key Features

*   **MongoDB to Postgres Sync**: Automatically migrates MongoDB collections to PostgreSQL JSONB tables.
*   **Immutable Backups**: Creates timestamped, copy-on-write Neon branches (`backup-YYYYMMDDTHHMMSSZ`) that are never modified.
*   **Verifiable Reliability**: Includes automated **restore testing** that validates backups by restoring them to a temporary branch and running integrity checks.
*   **Cross-DB Compatibility**: Stores flexible MongoDB documents in PostgreSQL's powerful JSONB format.
*   **Stateless**: Runs as a CLI or GitHub Action; no long-running servers or daemons required.

## 🛠️ Architecture

The system follows a layered architecture to ensure reliability and security:

1.  **Backup**: Connects to MongoDB, fetches all collections from the specified database, and stores them as JSONB in a fresh Neon branch.
2.  **Branching Strategy**:
    *   `main`: Stable standby, never touched by automated restores.
    *   `backup-...`: Read-only snapshots of your database at specific points in time.
    *   `restore-test-...`: Ephemeral branches used solely to verify backup integrity.
3.  **Security Transforms**: Automatically redacts connection strings from logs and enforces SSL on destination connections.

## 📋 Prerequisites

*   Python 3.11+
*   A **MongoDB** cluster (Primary).
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
| `MONGODB_SRV_URL` | Connection string for your MongoDB database. | ✅ |
| `NEON_API_KEY` | Your Neon API Key for managing branches. | ✅ |
| `NEON_PROJECT_ID` | The ID of the Neon project to use as the destination. | ✅ |
| `NEON_DATABASE_URL` | Connection string for your Neon database. Must include `sslmode=require`. | ✅ |

## 💻 Usage

The `supaneon-sync` CLI:

### 1. Validate Configuration
Checks that environment variables are correctly set.

```bash
supaneon-sync validate-config
```

### 2. Run Backup
Fetches MongoDB collections and stores them in a new Neon branch.

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

To enable these, add your `MONGODB_SRV_URL`, `NEON_API_KEY`, etc., to your GitHub Repository Secrets.

## 📄 License

This project is licensed under the MIT License.
