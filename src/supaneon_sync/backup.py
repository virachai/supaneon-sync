"""Backup orchestration: create Neon branch, run pg_dump from Supabase, restore into branch."""

from __future__ import annotations

import datetime
import subprocess
import os
from typing import Optional

from .config import validate_env
from .neon import NeonClient


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def run(supabase_url: Optional[str] = None, neon_api_key: Optional[str] = None):
    cfg = validate_env()
    supabase_url = supabase_url or cfg.supabase_database_url
    neon_api_key = neon_api_key or cfg.neon_api_key

    client = NeonClient(api_key=neon_api_key, project_id=cfg.neon_project_id)
    branch_name = f"backup-{_timestamp()}"

    # Rotation Policy: Max 6 backup branches.
    # If we already have >= 6, delete oldest until we have 5 (so the new one becomes the 6th).
    branches = client.list_branches()
    backup_branches = [b for b in branches if b.name.startswith("backup-")]
    # Sort by created_at (oldest first)
    backup_branches.sort(key=lambda b: b.created_at)

    max_branches = 6
    while len(backup_branches) >= max_branches:
        oldest = backup_branches.pop(0)
        print(f"Rotation: deleting old branch {oldest.name}...")
        try:
            # delete_branch() expects a branch ID (see neon.py)
            client.delete_branch(oldest.id)
        except Exception as e:
            print(f"WARNING: Failed to delete old branch {oldest.name}: {e}")

    print(f"Creating branch {branch_name}...")
    branch = client.create_branch(branch_name)

    # Need to wait/fetch for endpoint host?
    # Usually create_branch returns fast, but endpoint might take a moment or be computable.
    # The NeonClient.create_branch implementation we just wrote attempts to parse it but defaults to None if missing.
    # So we should call get_branch_host.

    print(f"Fetching connection info for {branch.id}...")
    host = client.get_branch_host(branch.id)
    print(f"Target host: {host}")

    # Construct connection string
    # User must provide password via NEON_DB_PASSWORD env, or we assume something else?
    # The RUNBOOK mentions creating a restore_user.
    # If NEON_DB_PASSWORD is not set, this might fail unless .pgpass is used.
    # We will use the env var if present.

    user = cfg.neon_db_user or os.environ.get(
        "NEON_DB_USER", "neondb_owner"
    )  # Default or from env
    password = cfg.neon_db_password

    if not password:
        print(
            "WARNING: NEON_DB_PASSWORD not set (and not found in NEON_DATABASE_URL). pg_restore might fail if authentication is required."
        )

    # Connection string for pg_restore
    # postgresql://user:password@host/neondb?sslmode=require
    # Note: Neon DB name is usually 'neondb'

    target_db_url = f"postgresql://{user}:{password}@{host}/neondb?sslmode=require"

    # Use pg_dump -> pg_restore piping where possible
    print("Starting pg_dump | pg_restore pipeline...")
    dump_cmd = ["pg_dump", "--format=custom", "--no-owner", "--no-acl", supabase_url]

    restore_cmd = [
        "pg_restore",
        "--dbname",
        target_db_url,
        "--no-owner",  # Often good for cloud targets to avoid role errors
        "--no-acl",
    ]

    try:
        dump_proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE)
        if dump_proc.stdout is None:
            raise RuntimeError("Failed to capture pg_dump stdout")

        restore_env = os.environ.copy()
        if password:
            restore_env["PGPASSWORD"] = password

        restore_proc = subprocess.Popen(
            restore_cmd, stdin=dump_proc.stdout, env=restore_env
        )
        dump_proc.stdout.close()

        while restore_proc.poll() is None:
            # Wait for it
            pass

        rc = restore_proc.returncode
        if rc != 0:
            raise SystemExit(f"Restore failed with exit code {rc}")

        # Check dump process too
        drc = dump_proc.wait()
        if drc != 0:
            raise SystemExit(f"Dump failed with exit code {drc}")

        print("Backup and restore completed successfully.")

    finally:
        # Placeholders for cleanup/metadata logging
        print(f"backup.branch={branch_name}")
        print("backup.timestamp=" + _timestamp())
