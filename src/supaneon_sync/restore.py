"""Restore test orchestration: find latest backup branch, restore into test branch, run healthchecks."""

from __future__ import annotations

import os
import time
from .config import validate_env
from .neon import NeonClient
from .healthcheck import run_healthcheck


def run_restore_test():
    cfg = validate_env()
    client = NeonClient(api_key=cfg.neon_api_key, project_id=cfg.neon_project_id)

    print("Finding latest backup branch...")
    latest = client.latest_backup_branch()
    if not latest:
        raise SystemExit("No backup branches found")

    print(f"Latest backup: {latest.name} (id={latest.id})")

    # Creating a branch from a parent (COatW) is the fastest way to "restore"
    # the state of the backup for testing without re-importing data.
    test_branch_name = (
        f"restore-test-{latest.name.replace('backup-', '')}-{int(time.time())}"
    )

    print(f"Creating test branch {test_branch_name} from parent {latest.id}...")
    test_branch = client.create_branch(test_branch_name, parent_id=latest.id)

    # Fetch endpoint
    print(f"Fetching connection info for test branch {test_branch.id}...")
    host = client.get_branch_host(test_branch.id)
    print(f"Test branch host: {host}")

    # Construct DB URL
    user = cfg.neon_db_user or os.environ.get("NEON_DB_USER", "neondb_owner")
    password = cfg.neon_db_password

    # For healthchecks, we need a valid connection.
    if not password:
        print("WARNING: NEON_DB_PASSWORD not set (and not found in NEON_DATABASE_URL). Healthcheck might fail.")

    db_url = f"postgresql://{user}:{password}@{host}/neondb?sslmode=require"

    print(f"Running healthchecks against {db_url}...")
    try:
        run_healthcheck(db_url)
        print("Healthcheck passed!")
    except Exception as e:
        print(f"Healthcheck failed: {e}")
        # Don't delete immediately if debugging?
        # CI usually wants failure.
        raise SystemExit(1)
    finally:
        # Delete test branch after successful restore test
        print(f"Deleting test branch {test_branch_name}...")
        try:
            client.delete_branch(test_branch.id)
        except Exception as e:
            print(f"WARNING: Failed to delete test branch {test_branch_name}: {e}")
