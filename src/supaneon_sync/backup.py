"""Backup orchestration: create Neon schema, run supabase db dump, and restore into schema."""

from __future__ import annotations

import datetime
import subprocess
import os
import re
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
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{new_schema}"')
            # Ensure uuid-ossp is enabled so uuid_generate_v4() works
            cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA public')

    print(f"Starting dump from Supabase via CLI...")

    dump_cmd = ["supabase", "db", "dump", "--db-url", supabase_url, "--schema", "public"]

    try:
        # Run dump and capture output
        result = subprocess.run(
            dump_cmd, capture_output=True, text=True, check=True, encoding="utf-8"
        )
        sql_content = result.stdout

        print(f"Processing and remapping 'public' to '{new_schema}'...")

        # Remap SQL content:
        # 1. Remove "extensions." prefix (will be found via search_path)
        # 2. Replace "public." with "backup_..." for tables/sequences
        # 3. Replace "search_path = public" with "search_path = backup_..., public"
        # 4. Replace "SCHEMA public" with new schema

        # First: Remove extensions schema prefix - functions will be resolved via search_path
        sql_content = re.sub(r'"extensions"\.', "", sql_content)

        # Second: Remap public schema references to new backup schema
        sql_content = re.sub(r"\bpublic\.", f"{new_schema}.", sql_content)
        sql_content = re.sub(r"search_path = public", f"search_path = {new_schema}, public", sql_content)
        sql_content = re.sub(r"SCHEMA public", f"SCHEMA {new_schema}", sql_content)

        print(f"Restoring SQL to Neon schema {new_schema}...")

        with psycopg.connect(neon_url) as conn:
            conn.autocommit = True
            with conn.cursor() as cur:
                # Set search_path first (session-level, will persist)
                cur.execute(f"SET search_path TO {new_schema}, public")
                # Execute the processed SQL
                cur.execute(sql_content)

        print(f"Backup completed successfully in schema {new_schema}.")

    except subprocess.CalledProcessError as e:
        print(f"ERROR: supabase db dump failed: {e.stderr}")
        raise SystemExit(1)
    except Exception as e:
        print(f"ERROR during backup: {e}")
        raise SystemExit(1)
    finally:
        print(f"backup.schema={new_schema}")
        print("backup.timestamp=" + _timestamp())


if __name__ == "__main__":
    run()
