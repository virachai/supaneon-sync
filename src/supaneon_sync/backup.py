"""Backup orchestration: create Neon schema, run pg_dump from Supabase, restore into schema."""

from __future__ import annotations

import datetime
import subprocess
import os
import psycopg
from typing import Optional

from .config import validate_env


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def list_backup_schemas(conn_url: str) -> list[str]:
    """List all schemas in Neon that start with 'backup_'."""
    with psycopg.connect(conn_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT schema_name FROM information_schema.schemata WHERE schema_name LIKE 'backup_%' ORDER BY schema_name ASC"
            )
            return [row[0] for row in cur.fetchall()]


def delete_schema(conn_url: str, schema_name: str) -> None:
    """Delete a schema and all its contents."""
    with psycopg.connect(conn_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')


def run(supabase_url: Optional[str] = None, neon_url: Optional[str] = None):
    cfg = validate_env()
    supabase_url = supabase_url or cfg.supabase_database_url
    neon_url = neon_url or cfg.neon_database_url

    # Rotation Policy: Max 6 backup schemas.
    # If we already have >= 6, delete oldest until we have 5.
    backup_schemas = list_backup_schemas(neon_url)

    max_schemas = 6
    while len(backup_schemas) >= max_schemas:
        oldest = backup_schemas.pop(0)
        print(f"Rotation: deleting old schema {oldest}...")
        try:
            delete_schema(neon_url, oldest)
        except Exception as e:
            print(f"WARNING: Failed to delete old schema {oldest}: {e}")

    new_schema = f"backup_{_timestamp()}"
    print(f"Creating backup schema {new_schema}...")

    with psycopg.connect(neon_url) as conn:
        with conn.cursor() as cur:
            cur.execute(f'CREATE SCHEMA "{new_schema}"')

    print("Starting pg_dump (Supabase) | sed (remap) | psql (Neon) pipeline...")

    # We use format=plain to allow sed-based remapping
    dump_cmd = [
        "pg_dump",
        "--format=plain",
        "--no-owner",
        "--no-acl",
        "--schema=public",
        supabase_url,
    ]

    # Sed commands to remap 'public' to the new schema name
    # 1. Replace "public." with "backup_...".
    # 2. Replace "search_path = public" with "search_path = backup_...".
    # 3. Replace "CREATE SCHEMA public" (if any) with new schema.
    # We use -e multiple times or a script. Let's use multiple -e.
    sed_cmd = [
        "sed",
        "-e",
        f"s/\\bpublic\\./{new_schema}./g",
        "-e",
        f"s/search_path = public/search_path = {new_schema}/g",
        "-e",
        f"s/SCHEMA public/SCHEMA {new_schema}/g",
    ]

    psql_cmd = ["psql", "--dbname", neon_url, "--quiet", "--no-password"]

    try:
        # PGPASSWORD might be needed for psql if not in URL (though it should be)
        env = os.environ.copy()
        if cfg.neon_db_password:
            env["PGPASSWORD"] = cfg.neon_db_password

        # Chain: dump | sed | psql
        dump_proc = subprocess.Popen(dump_cmd, stdout=subprocess.PIPE)
        sed_proc = subprocess.Popen(
            sed_cmd, stdin=dump_proc.stdout, stdout=subprocess.PIPE
        )
        psql_proc = subprocess.Popen(psql_cmd, stdin=sed_proc.stdout, env=env)

        # Close local handles
        if dump_proc.stdout:
            dump_proc.stdout.close()
        if sed_proc.stdout:
            sed_proc.stdout.close()

        psql_proc.wait()

        if psql_proc.returncode != 0:
            raise SystemExit(f"psql failed with exit code {psql_proc.returncode}")
        if sed_proc.wait() != 0:
            raise SystemExit(f"sed failed with exit code {sed_proc.returncode}")
        if dump_proc.wait() != 0:
            raise SystemExit(f"pg_dump failed with exit code {dump_proc.returncode}")

        print(f"Backup completed successfully in schema {new_schema}.")

    finally:
        print(f"backup.schema={new_schema}")
        print("backup.timestamp=" + _timestamp())


if __name__ == "__main__":
    run()
