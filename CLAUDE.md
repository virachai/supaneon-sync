# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

**supaneon-sync** is a production-grade, security-first database backup and disaster recovery system that automates logical PostgreSQL backups from Supabase (primary) to Neon (standby).

**Technology Stack:**
- Python 3.11+
- Typer CLI framework
- GitHub Actions (cron + manual triggers)
- pg_dump / pg_restore
- Neon branching (copy-on-write)

**Primary Objectives:**
- Prevent Supabase free-tier pause outages
- Maintain an always-ready standby database
- Enable instant failover by switching DATABASE_URL
- Provide verifiable backups through automated restore testing
- Operate entirely on free tiers

**Out of Scope:**
- Streaming replication
- Active-active databases
- Paid services
- Long-running infrastructure

## Common Commands

**System Dependencies:**
```bash
sudo apt-get install -y postgresql-client
```

**Development Setup:**
```bash
# Install with dev dependencies
pip install -e .[dev]

# Linting
ruff check .

# Formatting
black .                # Format code
black --check .        # Check formatting

# Testing
pytest -q

# Type checking
mypy
```

**CLI Commands:**
```bash
# Validate environment configuration
supaneon-sync validate-config

# Run backup and restore to Neon branch
supaneon-sync backup-run

# Run restore test using latest backup
supaneon-sync restore-test
```

## Architecture Overview

The codebase follows a layered architecture with clear separation of concerns:

### CLI Layer
- **[\_\_main\_\_.py](src/supaneon_sync/__main__.py)** - Typer CLI commands that route to orchestration modules

### Config Layer
- **[config.py](src/supaneon_sync/config.py)** - Environment validation with SSL enforcement
  - Validates required environment variables
  - Enforces `sslmode=require` on all PostgreSQL connections
  - Returns `Config` dataclass

### Service Layer
- **[neon.py](src/supaneon_sync/neon.py)** - Neon API client for branch management
  - `create_branch()`, `delete_branch()`, `list_branches()`
  - `latest_backup_branch()` - finds most recent backup
- **[backup.py](src/supaneon_sync/backup.py)** - Backup orchestration
  - Creates timestamped Neon branches
  - Pipes pg_dump directly to pg_restore (no intermediate files)
- **[restore.py](src/supaneon_sync/restore.py)** - Restore testing orchestration
  - Creates temporary test branches
  - Runs healthchecks
  - Cleans up on success, preserves on failure

### Validation Layer
- **[healthcheck.py](src/supaneon_sync/healthcheck.py)** - Smoke test suite
  - Database connectivity tests
  - Schema/table existence validation

### Utilities
- **[utils.py](src/supaneon_sync/utils.py)** - Safe logging with automatic credential redaction
- **[exceptions.py](src/supaneon_sync/exceptions.py)** - Custom exception hierarchy

### Key Architectural Decisions

**Process Piping:** Backup uses subprocess piping (`pg_dump | pg_restore`) to avoid disk I/O, reduce storage overhead, and improve security.

**Timestamped Branch Names:** Branches use UTC timestamps (`backup-YYYYMMDDTHHMMSSZ`) for deterministic ordering and metadata encoding.

**Never Restore to Main:** All restores go to new branches; Neon's `main` branch remains stable.

**Credential Redaction:** `utils.py` automatically redacts PostgreSQL connection strings from logs using regex replacement.

## Architectural Principles

This is a production system designed to protect real databases. Follow these principles:

- **Stateless execution** - No servers, no daemons, no persistent state
- **Immutable backups** - Once created, backup branches are never modified
- **Explicit over implicit** - Clear configuration, no magic behavior
- **Fail fast, fail safely** - Errors abort immediately with clear messages
- **Least privilege everywhere** - Use dedicated backup/restore database roles
- **Backups that cannot be restored are failures** - Restore testing is mandatory
- **Favor reliability and clarity over optimization** - Correctness > cleverness

## Security Requirements

This project follows a strict security-first model:

### Secrets & Credentials
- **No secrets in code or logs** - All credentials via environment variables only
- **Enforce TLS** - All database URLs must include `sslmode=require` (validated in [config.py:28](src/supaneon_sync/config.py#L28))
- **Least privilege** - Use dedicated backup/restore roles with minimal privileges

### Logging Requirements
- **Never log connection strings** - Redacted automatically by [utils.py](src/supaneon_sync/utils.py)
- **Never log SQL statements** - Only high-level steps and outcomes
- **Never log PII or row-level data** - Only metadata and status

### Data Handling
- **Pipe pg_dump → pg_restore** - Avoid persistent dump files when possible
- **Delete temp files immediately** - If temporary files are used
- **Exclude sensitive tables** - Configure excluded tables in backup workflow

## Neon Branch Strategy

Neon branching ensures safety and rollback capability:

### Rules
- **Never restore directly to `main`** - Always create a new branch first
- **Create timestamped branches** - Format: `backup-YYYYMMDDTHHMMSSZ` (UTC)
- **Branch creation before restore** - Always create branch, then restore
- **Old branch cleanup** - Optional retention policy (not yet implemented)

### Branch Purposes
- `main` - Stable standby, never modified by automated restores
- `backup-YYYYMMDDTHHMMSSZ` - Immutable backup snapshots
- `restore-test-*` - Temporary validation branches (deleted on success)

## Restore Testing

Automated restore testing is **mandatory**. Backups that cannot be restored are considered failures.

### Workflow
1. Find latest backup branch via [neon.py](src/supaneon_sync/neon.py)
2. Create temporary Neon test branch
3. Restore backup contents into test branch
4. Run smoke tests via [healthcheck.py](src/supaneon_sync/healthcheck.py):
   - Database connectivity
   - Schema existence
   - Table presence
   - Basic row counts
5. **On success:** Delete test branch
6. **On failure:** Preserve branch for inspection, fail the workflow

### Smoke Test Requirements
- Fast (seconds, not minutes)
- Deterministic (same input → same output)
- Non-destructive (read-only operations)

## Failover Model

Failover is designed to be instantaneous with no code changes:

- **Promotion mechanism:** Change `DATABASE_URL` environment variable only
- **No code changes required** - Application must be PostgreSQL-compatible
- **RPO (Recovery Point Objective):** Time of last successful backup
- **RTO (Recovery Time Objective):** Seconds (just URL swap)

## Environment Variables

Required environment variables:

```bash
# Supabase database URL (MUST include sslmode=require)
SUPABASE_DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"

# Neon API key
NEON_API_KEY="your-neon-api-key"

# Required: Target specific Neon project
NEON_PROJECT_ID="your-project-id"
```

## Code Quality Standards

When contributing to this codebase:

### Code Style
- Pythonic, readable, modular code
- Type hints where appropriate (dataclasses, function signatures)
- Explicit error handling with custom exceptions
- Idempotent behavior (safe to re-run)
- Deterministic execution (no random behavior)

### PRs and Commits
- Small, focused PRs (single concern per PR)
- Conventional Commits: `feat:`, `fix:`, `chore:`
- Include tests when fixing bugs
- Update [README.md](README.md) for behavior changes
- Update [SECURITY.md](SECURITY.md) for security-related changes

### Testing Requirements
- Failed restore = failed workflow
- Failed restore = failed workflow
- Pre-commit hooks enforce black + ruff
- CI runs: ruff check, black check, pytest
- **Agent Rule:** After any code change, run `/check-all-passed` to verify quality.

## GitHub Actions Workflows

The system runs via scheduled GitHub Actions:

- **[backup.yml](.github/workflows/backup.yml)** - Daily at 02:00 UTC (`0 2 * * *`)
  - Runs `python -m supaneon_sync.backup`
- **[restore-test.yml](.github/workflows/restore-test.yml)** - Daily at 03:30 UTC (`30 3 * * *`)
  - Runs `python -m supaneon_sync.restore`
- **[ci.yml](.github/workflows/ci.yml)** - On push to main and PRs
  - Linting, formatting, tests

All workflows support manual trigger via `workflow_dispatch`.
