# Verification Rule

Every time code is created or updated, the agent MUST run the following command to verify that all checks pass:

```bash
/check-all-passed
```

This ensures that:
1. Code formatting is consistent (Black).
2. Linting rules are followed (Ruff).
3. Type hints are correct (Mypy).
4. Tests are passing (Pytest).

DO NOT consider a task complete until these checks have been run and passed. If any check fails, the agent MUST fix the issues before proceeding or notifying the user.
