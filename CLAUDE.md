# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

**supaneon-sync** is a production-grade, security-first database backup and disaster recovery system that automates logical backups from MongoDB (primary) to Neon (standby).

**Technology Stack:**
- Python 3.11+
- Typer CLI framework
- GitHub Actions (cron + manual triggers)
- MongoDB / pymongo
- Neon branching (copy-on-write)

**Primary Objectives:**
- Prevent MongoDB data loss
- Maintain an always-ready standby database in Postgres (JSONB)
- Enable verifiable backups through automated restore testing
- Operate entirely on free tiers

## Common Commands

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
mypy src
```

**CLI Commands:**
```bash
# Validate environment configuration
supaneon-sync validate-config

# Run backup from MongoDB to Neon branch
supaneon-sync backup-run

# Run restore test using latest backup
supaneon-sync restore-test
```

## Architecture Overview

The codebase follows a layered architecture with clear separation of concerns:

### CLI Layer
- **[__main__.py](src/supaneon_sync/__main__.py)** - Typer CLI commands that route to orchestration modules

### Config Layer
- **[config.py](src/supaneon_sync/config.py)** - Environment validation
  - Validates required environment variables (`MONGODB_SRV_URL`, `NEON_DATABASE_URL`)
  - Enforces `sslmode=require` on Neon connections
  - Returns `Config` dataclass

### Service Layer
- **[neon.py](src/supaneon_sync/neon.py)** - Neon API client for branch management
  - `create_branch()`, `delete_branch()`, `list_branches()`
- **[backup.py](src/supaneon_sync/backup.py)** - Backup orchestration
  - Fetches collections from MongoDB
  - Stores them as JSONB tables in PostgreSQL timestamped branches
- **[restore.py](src/supaneon_sync/restore.py)** - Restore testing orchestration
  - Creates temporary test branches
  - Runs healthchecks on JSONB tables

### Validation Layer
- **[healthcheck.py](src/supaneon_sync/healthcheck.py)** - Smoke test suite
  - Database connectivity tests
  - JSONB table/column existence validation

## Architectural Principles

- **Stateless execution** - No servers, no daemons, no persistent state
- **Immutable backups** - Once created, backup branches are never modified
- **Explicit over implicit** - Clear configuration, no magic behavior
- **Fail fast, fail safely** - Errors abort immediately with clear messages
- **Backups that cannot be restored are failures** - Restore testing is mandatory

## Security Requirements

- **No secrets in code or logs** - All credentials via environment variables only
- **Enforce TLS on destination** - `NEON_DATABASE_URL` must include `sslmode=require`
- **Credential Redaction** - `utils.py` automatically redacts sensitive URLs from logs

## Environment Variables

Required environment variables:

```bash
# MongoDB connection URL
MONGODB_SRV_URL="mongodb+srv://user:pass@host/db"

# Neon API key and project ID
NEON_API_KEY="your-neon-api-key"
NEON_PROJECT_ID="your-project-id"

# Neon database URL (MUST include sslmode=require)
NEON_DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"
```
