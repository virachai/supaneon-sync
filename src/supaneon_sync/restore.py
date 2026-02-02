"""Restore test orchestration: find latest backup schema, run healthchecks."""

from __future__ import annotations

from .config import validate_env
from .healthcheck import run_healthcheck
from .backup import list_backup_schemas


def run_restore_test():
    cfg = validate_env()
    neon_url = cfg.neon_database_url

    print("Finding latest backup schema...")
    try:
        backup_schemas = list_backup_schemas(neon_url)
    except Exception as e:
        raise SystemExit(f"Failed to list backup schemas: {e}")

    if not backup_schemas:
        raise SystemExit("No backup schemas found")

    # list_backup_schemas returns sorted ascending, so last is latest
    latest_schema = backup_schemas[-1]
    print(f"Latest backup schema: {latest_schema}")

    print(f"Running healthchecks against schema {latest_schema}...")
    try:
        run_healthcheck(neon_url, schema=latest_schema)
        print("Healthcheck passed!")
    except Exception as e:
        print(f"Healthcheck failed: {e}")
        raise SystemExit(1)


if __name__ == "__main__":
    run_restore_test()
