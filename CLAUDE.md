# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## System Overview

**supaneon-sync** is a production-grade, security-first database backup and disaster recovery system that automates logical backups from Supabase (primary) to Neon (standby).

**Technology Stack:**
- Python 3.11+
- Typer CLI framework
- GitHub Actions (cron + manual triggers)
- Supabase CLI for pg_dump
- Neon PostgreSQL (timestamped schemas)

**Primary Objectives:**
- Prevent Supabase data loss
- Maintain an always-ready standby database in Neon with timestamped schemas
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

# Run backup from Supabase to Neon schema
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
  - Validates required environment variables (`SUPABASE_DATABASE_URL`, `NEON_DATABASE_URL`)
  - Enforces `sslmode=require` on both Supabase and Neon connections
  - Returns `Config` dataclass

### Service Layer
- **[neon.py](src/supaneon_sync/neon.py)** - Neon API client for branch management
  - `create_branch()`, `delete_branch()`, `list_branches()`
- **[backup.py](src/supaneon_sync/backup.py)** - Backup orchestration
  - Dumps Supabase database using `supabase db dump` CLI
  - Transforms SQL to remap schemas and roles
  - Restores into timestamped Neon schemas
- **[restore.py](src/supaneon_sync/restore.py)** - Restore testing orchestration
  - Creates temporary test branches
  - Runs healthchecks on JSONB tables

### Validation Layer
- **[healthcheck.py](src/supaneon_sync/healthcheck.py)** - Smoke test suite
  - Database connectivity tests
  - Schema and table existence validation

## Architectural Principles

- **Stateless execution** - No servers, no daemons, no persistent state
- **Immutable backups** - Once created, backup branches are never modified
- **Explicit over implicit** - Clear configuration, no magic behavior
- **Fail fast, fail safely** - Errors abort immediately with clear messages
- **Backups that cannot be restored are failures** - Restore testing is mandatory

## Security Requirements

- **No secrets in code or logs** - All credentials via environment variables only
- **Enforce TLS on all connections** - Both `SUPABASE_DATABASE_URL` and `NEON_DATABASE_URL` must include `sslmode=require`
- **Credential Redaction** - `utils.py` automatically redacts sensitive URLs from logs

## Environment Variables

Required environment variables:

```bash
# Supabase database URL (MUST include sslmode=require)
SUPABASE_DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"

# Neon database URL (MUST include sslmode=require)
NEON_DATABASE_URL="postgresql://user:pass@host/db?sslmode=require"

# Optional: Neon API key and project ID for branch management
NEON_API_KEY="your-neon-api-key"
NEON_PROJECT_ID="your-project-id"
```
