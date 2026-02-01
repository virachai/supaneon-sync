"""Restore test orchestration: find latest backup branch, restore into test branch, run healthchecks."""

from __future__ import annotations

from .config import validate_env
from .neon import NeonClient
from .healthcheck import run_healthcheck


def run_restore_test():
    cfg = validate_env()
    client = NeonClient(api_key=cfg.neon_api_key, project_id=cfg.neon_project_id)

    latest = client.latest_backup_branch()
    if not latest:
        raise SystemExit("No backup branches found")

    test_branch = f"restore-test-{latest}-{__import__('time').time():.0f}"
    client.create_branch(test_branch)

    # RESTORE: In practice, we would restore the contents of `latest` into `test_branch`.
    # This is a placeholder for the actual pg_restore invocation.

    # Run healthchecks against the test branch endpoint; here we assume an environment
    # or a way to get a DB URL for the test branch.
    db_url = f"postgresql://{test_branch}"
    run_healthcheck(db_url)

    # On success, delete test branch
    client.delete_branch(test_branch)
