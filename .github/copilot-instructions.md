The absence of an existing structure is **not** a blocker.

---

## GitHub Actions Expectations 🤖

- Scheduled execution via cron
- Manual trigger via `workflow_dispatch`
- Clear job separation:
  - backup
  - restore-test
- Fail fast on errors
- Masked secrets
- Minimal but meaningful logs

---

## Restore Testing Requirements 🧪

Automated restore testing is mandatory:

- Restore latest backup into a temporary Neon branch
- Run smoke tests:
  - connectivity
  - schema existence
  - table presence
  - basic row counts
- Delete test branch on success
- Preserve branch and fail workflow on failure

---

## Failover Model ⚡

- No code changes required to promote Neon
- Failover achieved by switching `DATABASE_URL`
- RPO equals last successful backup
- Document failover steps clearly in README

---

## Code Quality Standards 🧾

- Pythonic, readable, modular code
- Explicit error handling
- Type hints where appropriate
- Idempotent behavior
- Deterministic execution
- README-quality inline documentation

---

## PR & Change Expectations ✅

When creating commits or PRs:

- Small, focused changes
- Clear commit messages
- Update README if behavior or assumptions change
- Prefer correctness and safety over clever optimizations

---

## Agent Guidance Summary 🧠

- Do not wait for instructions
- Do not ask unnecessary questions
- Implement completely
- Document assumptions
- Optimize for production reliability

If blocked, proceed with best defaults and continue.
