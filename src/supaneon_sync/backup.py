"""Backup orchestration: dump Supabase database and restore into timestamped Neon schema."""

from __future__ import annotations

import datetime
import subprocess
import psycopg
import os
from typing import Optional

from .config import validate_env

DUMP_FILE = "supabase.dump"


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ")


def list_backup_schemas(conn_url: str) -> list[str]:
    with psycopg.connect(conn_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT schema_name
                FROM information_schema.schemata
                WHERE schema_name LIKE 'backup_%'
                ORDER BY schema_name ASC
                """)
            return [row[0] for row in cur.fetchall()]


def delete_schema(conn_url: str, schema_name: str) -> None:
    with psycopg.connect(conn_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f'DROP SCHEMA IF EXISTS "{schema_name}" CASCADE')


def run(supabase_url: Optional[str] = None, neon_url: Optional[str] = None):
    cfg = validate_env()
    supabase_url = supabase_url or cfg.supabase_database_url
    neon_url = neon_url or cfg.neon_database_url

    # ---------------------------
    # Rotation policy
    # ---------------------------
    max_schemas = 6
    backup_schemas = list_backup_schemas(neon_url)

    while len(backup_schemas) >= max_schemas:
        oldest = backup_schemas.pop(0)
        print(f"Rotation: deleting old schema {oldest}...")
        delete_schema(neon_url, oldest)

    new_schema = f"backup_{_timestamp()}"
    print(f"Creating backup schema {new_schema}...")

    # ---------------------------
    # Prepare Neon schema
    # ---------------------------
    with psycopg.connect(neon_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{new_schema}"')
            cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    try:
        # ---------------------------
        # Dump Supabase using pg_dump
        # ---------------------------
        print("Dumping Supabase database (plain format)...")

        dump_cmd = [
            "pg_dump",
            "--format=plain",
            "--schema=public",
            "--no-owner",
            "--no-privileges",
            "--file",
            DUMP_FILE,
            supabase_url,
        ]

        subprocess.run(dump_cmd, check=True)

        # ---------------------------
        # Schema Remapping
        # ---------------------------
        print(f"Remapping schema 'public' to '{new_schema}'...")
        REMAPPED_FILE = f"{DUMP_FILE}.remapped"

        # We replace "public" with the new schema name in the SQL dump.
        # This handles table creation and references.
        with open(DUMP_FILE, "r", encoding="utf-8") as fin:
            with open(REMAPPED_FILE, "w", encoding="utf-8") as fout:
                for line in fin:
                    new_line = line.replace('"public"', f'"{new_schema}"')
                    new_line = new_line.replace(" public.", f" {new_schema}.")
                    new_line = new_line.replace("SCHEMA public", f"SCHEMA {new_schema}")

                    # Supabase → Neon fix
                    new_line = new_line.replace("extensions.", "public.")
                    new_line = new_line.replace('"extensions".', '"public".')

                    new_line = new_line.replace("'public.", f"'{new_schema}.")

                    fout.write(new_line)

        # ---------------------------
        # Restore into Neon
        # ---------------------------
        print(f"Restoring into Neon schema {new_schema}...")

        restore_cmd = [
            "psql",
            "--dbname",
            neon_url,
            "--file",
            REMAPPED_FILE,
            "--quiet",
            "--set",
            "ON_ERROR_STOP=1",
        ]

        subprocess.run(restore_cmd, check=True)

        print(f"Backup completed successfully in schema {new_schema}.")

    finally:
        if os.path.exists(DUMP_FILE):
            os.remove(DUMP_FILE)
        if "REMAPPED_FILE" in locals() and os.path.exists(REMAPPED_FILE):
            os.remove(REMAPPED_FILE)

        print(f"backup.schema={new_schema}")
        print("backup.timestamp=" + _timestamp())


if __name__ == "__main__":
    run()
