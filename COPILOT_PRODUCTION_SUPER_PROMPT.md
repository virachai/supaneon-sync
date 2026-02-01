# Dev Lead pick

You are acting as a Staff / Principal Engineer with strong experience in
SRE, cloud infrastructure, PostgreSQL, and disaster recovery systems.

Your task is to design and implement **supaneon-sync** as a
**production-grade, security-first, free-tier-friendly**
database backup and standby synchronization system.

This is NOT a demo or tutorial.
Assume this system protects a real production database.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 SYSTEM OVERVIEW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

supaneon-sync automates logical PostgreSQL backups from:

- **Supabase** (Primary / Active DB)
→ **Neon** (Standby / Backup DB)

using:

- Python 3.11+
- GitHub Actions (cron + manual triggers)
- pg_dump / pg_restore
- Neon branching (copy-on-write)

Primary objectives:

- Prevent Supabase free-tier pause outages
- Maintain an always-ready standby database
- Enable instant failover by switching a single DATABASE_URL
- Provide verifiable backups through automated restore testing
- Operate entirely on free tiers

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏗️ ARCHITECTURAL PRINCIPLES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Stateless execution (no servers, no daemons)
- Immutable backups
- Explicit over implicit
- Fail fast, fail safely
- Least privilege everywhere
- Backups that cannot be restored are considered failures
- Favor reliability and clarity over clever optimizations

Out of scope:

- Streaming replication
- Active-active databases
- Paid services
- Long-running infrastructure
- Vendor-specific lock-in beyond PostgreSQL

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 SECURITY & PRIVACY (NON-NEGOTIABLE)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Secrets & Access:

- No secrets in code, logs, or repo
- All credentials via environment variables only
- Enforce `sslmode=require` on all DB connections
- Use least-privilege database roles:
  - Supabase: read-only backup role
  - Neon: restore-only role (optionally schema-scoped)

Logging:

- Never log connection strings
- Never log SQL statements
- Never log PII or row-level data
- Log only high-level steps and outcomes

Data handling:

- Avoid persistent dump files when possible (pipe pg_dump → pg_restore)
- If temp files are used, delete immediately after use
- Exclude volatile or sensitive tables by default (configurable)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 BACKUP STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Logical backups using `pg_dump`
- Restore using `pg_restore`
- Support:
  - full database backups
  - schema-isolated restores
- Deterministic execution
- Clear error propagation
- Timestamped backup identity

Expected behavior:

- A failed dump MUST abort restore
- A failed restore MUST fail the workflow
- Partial success is not acceptable

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🌿 NEON BRANCH STRATEGY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Use Neon branching to ensure safety and rollback capability.

Rules:

- Never restore directly into Neon `main`
- Create a new branch for every backup run
- Branch names must include timestamps (UTC)
- Branch creation must happen BEFORE restore
- Old branches may be cleaned up optionally

Branch purposes:

- main            → stable standby
- backup-YYYYMMDD → immutable backups
- restore-test    → temporary validation branch

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚡ FAILOVER & PROMOTION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Failover design:

- No code changes required
- Promotion achieved by switching DATABASE_URL only
- Application must be Neon-compatible without modification

Document and implement:

- Clear promotion steps
- Known limitations (RPO = last backup)
- Rollback considerations

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 AUTOMATED RESTORE TESTING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Restore testing is mandatory.

Workflow:

1. Create temporary Neon test branch
2. Restore latest backup into test branch
3. Run smoke tests:
   - DB connectivity
   - Schema existence
   - Table presence
   - Basic row counts
4. On success:
   - Delete test branch
5. On failure:
   - Preserve branch for inspection
   - Fail the workflow

Smoke tests must be:

- Fast
- Deterministic
- Non-destructive

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🤖 GITHUB ACTIONS REQUIREMENTS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

- Scheduled execution via cron
- Manual trigger via workflow_dispatch
- Separate workflows for:
  - backup
  - restore-test
- Proper exit codes
- Clear step boundaries
- Minimal but sufficient logging
- Masked secrets

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧾 OBSERVABILITY & AUDITABILITY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Logs must include:

- Timestamps
- Current phase (dump / restore / test)
- Target Neon branch
- Final success or failure state

Optional:

- Backup checksum
- Metadata table in Neon

Do NOT include:

- Raw SQL
- Table data
- Credentials

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📁 EXPECTED PROJECT STRUCTURE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

supaneon-sync/
├── src/
│   ├── config.py        # env parsing & validation
│   ├── backup.py        # pg_dump orchestration
│   ├── restore.py       # pg_restore logic
│   ├── neon.py          # Neon API / branch management
│   ├── healthcheck.py   # smoke tests
│   └── utils.py         # shared helpers
├── .github/workflows/
│   ├── backup.yml
│   └── restore-test.yml
├── README.md            # usage & DR guide
└── SECURITY.md          # threat model & guarantees

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧠 ENGINEERING EXPECTATIONS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Code:

- Pythonic, readable, modular
- Type hints where appropriate
- Explicit exceptions
- Idempotent behavior
- Configurable via env vars
- No hidden side effects

Documentation:

- README must explain:
  - setup
  - security model
  - failover procedure
  - limitations
- SECURITY.md must explain:
  - threat model
  - mitigations
  - user responsibilities

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🏁 SUCCESS CRITERIA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

The implementation is complete only if:

- Supabase data is reliably backed up to Neon
- Neon branches are used safely
- Restore tests run automatically
- Failover can be done in seconds
- No paid infrastructure is required
- The system is production-ready in design and execution

Do not ask questions.
Do not simplify.
Implement completely and decisively.
