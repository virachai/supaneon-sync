# Project Status: supaneon-sync

**Current Version:** `v1.0.0`
**Date:** 2026-02-02

## 📝 Overview
`supaneon-sync` is a robust automation tool for syncing Supabase (PostgreSQL) databases to Neon (PostgreSQL) for disaster recovery and secondary querying. It uses logical backups (`pg_dump`/`pg_restore`) to create immutable, timestamped snapshots.

## ✅ Current Implementation Status

### Core Features
- [x] **Automated Logical Backup**: Successfully dumps Supabase `public` schema.
- [x] **Timestamped Restore**: Restores into Neon using unique schema names (`backup_YYYYMMDDTHHMMSSZ`).
- [x] **Backup Rotation**: Automatically maintains only the most recent **6 backups** to optimize storage.
- [x] **Dependency Management**: Automatically ensures `uuid-ossp` extension is present in Neon.
- [x] **Role Redaction**: Environment variables are used for URLs, preventing credential leaks in logs.

### Infrastructure & CI/CD
- [x] **GitHub Actions**: Daily backup workflow (`02:00 UTC`) and restore testing.
- [x] **PostgreSQL 17**: CI/CD pipeline upgraded to use PostgreSQL 17 client for maximum compatibility.
- [x] **Validation**: Built-in CLI commands for configuration validation and restore testing.

### Code Quality
- [x] **Linting**: 100% compliant with Ruff.
- [x] **Formatting**: Standardized using Black.
- [x] **Types**: Fully typed with MyPy (Success on 13 source files).
- [x] **Tests**: 5/5 passing tests in Pytest.

## 🚀 Recent Changes
- **Release v1.0.0**: Tagged and pushed to origin.
- **CI/CD Optimization**: Added explicit PostgreSQL 17 installation in GitHub Actions to avoid tool mismatched versions.
- **Code Cleanup**: Removed legacy `X1backup.py` file.
- **Debugging**: Integrated placeholder support for `PGHOSTADDR` and alternative connection pooling configurations.

## 📋 Next Steps
- [ ] Implement optional Neon branching via API for even faster restore testing.
- [ ] Add Slack/Discord notification hooks for failed backups.
- [ ] Expand restore tests to include basic data integrity checks (row counts, sensitive data presence).
