"""
Backup orchestration:
- Dump Supabase schema (schema-only)
- Dump Supabase data (data-only)
- Restore into timestamped Neon schema
"""

from __future__ import annotations

import datetime
import subprocess
import psycopg
import os
from typing import Optional

from .config import validate_env

SCHEMA_DUMP = "schema.sql"
SCHEMA_REMAPPED = "schema.remapped.sql"
DATA_DUMP = "data.sql"


def _timestamp() -> str:
    return datetime.datetime.now(datetime.UTC).strftime("%Y%m%dT%H%M%SZ").lower()


# ---------------------------------------------------------------------
# Schema rotation helpers
# ---------------------------------------------------------------------


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


# ---------------------------------------------------------------------
# Schema remapping
# ---------------------------------------------------------------------


def remap_schema_file(src: str, dst: str, new_schema: str) -> None:
    SKIP_PREFIXES = (
        "GRANT ",
        "REVOKE ",
        "ALTER DEFAULT PRIVILEGES",
        "SET ROLE",
        "CREATE POLICY",
        "ALTER POLICY",
        "DROP POLICY",
    )

    SKIP_CONTAINS = (
        "ROW LEVEL SECURITY",
        "TO anon",
        "TO authenticated",
    )

    with (
        open(src, "r", encoding="utf-8") as fin,
        open(dst, "w", encoding="utf-8") as fout,
    ):

        for line in fin:
            if line.startswith(SKIP_PREFIXES) or any(x in line for x in SKIP_CONTAINS):
                continue

            # Core remapping logic
            # Handle quoted "public"
            line = line.replace('"public"', f'"{new_schema}"')

            # Handle unquoted public. with various prefixes
            for prefix in (" ", "(", "=", ",", "ON "):
                line = line.replace(f"{prefix}public.", f"{prefix}{new_schema}.")

            # Case where public. starts the line
            if line.startswith("public."):
                line = f"{new_schema}." + line[7:]

            # Handle schema creation
            line = line.replace("SCHEMA public", f"SCHEMA {new_schema}")
            # Handle search_path
            line = line.replace("search_path = public", f"search_path = {new_schema}")

            # Remap extensions to public (Neon's default)
            line = line.replace("extensions.", "public.")
            line = line.replace('"extensions".', '"public".')
            line = line.replace(
                "'extensions", f"'{new_schema}"
            )  # Used in some defaults

            # Replace Supabase extension UUID calls
            line = line.replace("extensions.uuid_generate_v4()", "gen_random_uuid()")

            fout.write(line)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------


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

    new_schema = f"backup_{_timestamp()}".lower()
    print(f"Creating backup schema {new_schema}...")

    # ---------------------------
    # Prepare Neon schema
    # ---------------------------
    with psycopg.connect(neon_url) as conn:
        conn.autocommit = True
        with conn.cursor() as cur:
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{new_schema.lower()}"')
            cur.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    try:
        # ---------------------------
        # Dump schema-only
        # ---------------------------
        print("Dumping Supabase schema (schema-only)...")

        subprocess.run(
            [
                "pg_dump",
                "--schema-only",
                "--schema=public",
                "--no-owner",
                "--no-acl",
                supabase_url,
            ],
            check=True,
            stdout=open(SCHEMA_DUMP, "w"),
        )

        # ---------------------------
        # Dump data-only
        # ---------------------------
        print("Dumping Supabase data (data-only)...")

        subprocess.run(
            [
                "pg_dump",
                "--data-only",
                "--schema=public",
                "--disable-triggers",
                supabase_url,
            ],
            check=True,
            stdout=open(DATA_DUMP, "w"),
        )

        # ---------------------------
        # Remap schema
        # ---------------------------
        print(f"Remapping schema to {new_schema}...")
        remap_schema_file(SCHEMA_DUMP, SCHEMA_REMAPPED, new_schema)

        # ---------------------------
        # Restore schema
        # ---------------------------
        print("Restoring schema into Neon...")

        subprocess.run(
            [
                "psql",
                neon_url,
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                SCHEMA_REMAPPED,
            ],
            check=True,
        )

        # ---------------------------
        # Restore data (via search_path)
        # ---------------------------
        print("Restoring data into Neon...")

        restore_data_sql = f"""
        SET search_path TO "{new_schema}";
        \\i {DATA_DUMP}
        """

        subprocess.run(
            ["psql", neon_url, "-v", "ON_ERROR_STOP=1"],
            input=restore_data_sql,
            text=True,
            check=True,
        )

        print(f"Backup completed successfully in schema {new_schema}.")

    finally:
        for f in (SCHEMA_DUMP, SCHEMA_REMAPPED, DATA_DUMP):
            if os.path.exists(f):
                os.remove(f)

        print(f"backup.schema={new_schema}")
        print("backup.timestamp=" + _timestamp())


if __name__ == "__main__":
    run()
