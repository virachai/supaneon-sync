"""Backup orchestration: create Neon branch, run pg_dump from Supabase, restore into branch."""

from __future__ import annotations

import datetime
import subprocess
from typing import Optional

from .config import validate_env
from .neon import NeonClient


def _timestamp() -> str:
    return datetime.datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def run(supabase_url: Optional[str] = None, neon_api_key: Optional[str] = None):
    cfg = validate_env()
    supabase_url = supabase_url or cfg.supabase_database_url
    neon_api_key = neon_api_key or cfg.neon_api_key

    client = NeonClient(api_key=neon_api_key, project_id=cfg.neon_project_id)
    branch = f"backup-{_timestamp()}"
    client.create_branch(branch)

    # Use pg_dump -> pg_restore piping where possible
    dump_cmd = ["pg_dump", "--format=custom", "--no-owner", "--no-acl", supabase_url]
    restore_cmd = [
        "pg_restore",
        "--dbname",
        f"postgresql://{branch}",
    ]  # placeholder, replace with real branch target

    # Note: In Actions the DB target for the branch must be obtained via Neon API.

    try:
        dump_proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE)
        if dump_proc.stdout is None:
            raise RuntimeError("Failed to capture pg_dump stdout")
        restore_proc = subprocess.Popen(restore_cmd, stdin=dump_proc.stdout)
        dump_proc.stdout.close()
        rc = restore_proc.wait()
        if rc != 0:
            raise SystemExit(rc)
    finally:
        # Placeholders for cleanup/metadata logging
        print(f"backup.branch={branch}")
        print("backup.timestamp=" + _timestamp())
