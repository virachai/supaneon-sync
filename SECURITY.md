# SECURITY

This project follows a strict security-first model (see runbook):

- **No secrets in code or logs.** All credentials must be provided via environment variables or GitHub secrets.
- **Require TLS.** All database URLs must include `sslmode=require`.
- **Least privilege.** Use dedicated backup/restore roles with minimal privileges.
- **No PII in logs.** Do not log raw SQL, row data, or connection strings.
- **Restore testing required.** Backups are validated via automated restore tests; a failed restore is considered a failure.
