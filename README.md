# supaneon-sync

**Production-grade Supabase to Neon logical backup and disaster recovery automation.**

`supaneon-sync` is a security-first tool designed to automate logical PostgreSQL backups from a primary Supabase database to a standby Neon database. It ensures you have an always-ready, verifiable failover target without the complexity of managing servers or persistent storage.

---

## 🚀 Key Features

*   **Supabase Free-Tier Protection**: Prevents project pausing by keeping activity alive and data secured elsewhere.
*   **Immutable Backups**: Creates timestamped, copy-on-write Neon branches (`backup-YYYYMMDDTHHMMSSZ`) that are never modified.
*   **Zero-Disk Piping**: Streams data directly from `pg_dump` to `pg_restore` using pipes, avoiding intermediate files and reducing security risks.
*   **Verifiable Reliability**: Includes automated **restore testing** that validates backups by restoring them to a temporary branch and running integrity checks.
*   **Instant Failover**: Designed so you can switch your application's `DATABASE_URL` to Neon instantly in case of a Supabase outage.
*   **Stateless**: Runs as a CLI or GitHub Action; no long-running servers or daemons required.

## 🛠️ Architecture

The system follows a layered architecture to ensure reliability and security:

1.  **Backup**: Connects to Supabase, streams the schema and data using `pg_dump`, and pipes it directly to `pg_restore` on a fresh Neon branch.
2.  **Branching Strategy**:
    *   `main`: Stable standby, never touched by automated restores.
    *   `backup-...`: Read-only snapshots of your database at specific points in time.
    *   `restore-test-...`: Ephemeral branches used solely to verify backup integrity.
3.  **Security Transforms**: Automatically redacts connection strings from logs and enforces SSL on all connections.

## 📋 Prerequisites

*   Python 3.11+
*   PostgreSQL client tools (specifically `pg_dump` and `pg_restore`) installed on the system.
*   A **Supabase** project (Primary).
*   A **Neon** project (Standby/Backup target).

## 📦 Installation

To install the package locally:

```bash
git clone https://github.com/virachai/supaneon-sync.git
cd supaneon-sync
pip install -e .
```

To install development dependencies (for running tests or contributing):

```bash
pip install -e .[dev]
```

## ⚙️ Configuration

The tool relies entirely on environment variables for configuration. Create a `.env` file or set these in your CI/CD environment:

| Variable | Description | Required |
| :--- | :--- | :---: |
| `SUPABASE_DATABASE_URL` | Connection string for your Supabase database. **Must** include `sslmode=require`. | ✅ |
| `NEON_API_KEY` | Your Neon API Key for managing branches. | ✅ |
| `NEON_PROJECT_ID` | The ID of the Neon project to use as the destination. | Optional |
| `LOG_LEVEL` | Logging verbosity (default: `INFO`). | Optional |

> **Note**: `supaneon-sync` strictly enforces `sslmode=require` on all database connections.

## 💻 Usage

The `supaneon-sync` CLI provides three main commands:

### 1. Validate Configuration
Checks that all required tools (`pg_dump`, `pg_restore`) are present and environment variables are correctly set.

```bash
supaneon-sync validate-config
```

### 2. Run Backup
Creates a new Neon branch and pipes the database dump from Supabase to it.

```bash
supaneon-sync backup-run
```

### 3. Test Restore (Health Check)
Verifies the integrity of your latest backup. This command:
1.  Finds the most recent backup branch.
2.  Creates a temporary `restore-test` branch.
3.  Restores the data.
4.  Runs health checks (connectivity, schema validation).
5.  Deletes the test branch if successful (fails the workflow if not).

```bash
supaneon-sync restore-test
```

## 🤖 Automation (GitHub Actions)

This project is verified to run on GitHub Actions. Included workflows:

*   **`backup.yml`**: Runs daily at 02:00 UTC.
*   **`restore-test.yml`**: Runs daily at 03:30 UTC.

To enable these, simply add your `SUPABASE_DATABASE_URL` and `NEON_API_KEY` to your GitHub Repository Secrets.

## 🔒 Security

*   **No Secrets in Logs**: All sensitive environment variables and connection strings are automatically redacted from output logs.
*   **Least Privilege**: We recommend using dedicated database roles for backup and restore operations with only necessary permissions.
*   **Secure Transport**: Enforced TLS for all data in transit.

See [SECURITY.md](SECURITY.md) for more details.

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and the process for submitting pull requests.

## 📄 License

This project is licensed under the MIT License.
