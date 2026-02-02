"""
Backup orchestration:
- Dump Supabase schema (schema-only)
- Dump Supabase data (data-only)
- Remap public -> backup_<timestamp>
- Restore into timestamped Neon schema
"""

from __future__ import annotations

import datetime
import subprocess
import psycopg
import os
import re
from typing import Optional

from .config import validate_env

SCHEMA_DUMP = "schema.sql"
SCHEMA_REMAPPED = "schema.remapped.sql"
DATA_DUMP = "data.sql"
DATA_REMAPPED = "data.remapped.sql"


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
# Schema + Data remapping
# ---------------------------------------------------------------------


def remap_schema_file(src: str, dst: str, new_schema: str) -> None:
    """Robust regex-based schema remapper for PostgreSQL dumps."""

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
        "TO service_role",
        "EXTENSION ",
    )

    public_quoted_re = re.compile(r'"public"')
    public_unquoted_re = re.compile(r"(?<!\w)public\.")
    extensions_re = re.compile(r'("extensions"|extensions)\.')

    with (
        open(src, "r", encoding="utf-8") as fin,
        open(dst, "w", encoding="utf-8") as fout,
    ):
        for line in fin:
            if line.startswith(SKIP_PREFIXES) or any(x in line for x in SKIP_CONTAINS):
                continue

            if "SCHEMA public" in line:
                continue

            line = public_quoted_re.sub(f'"{new_schema}"', line)
            line = public_unquoted_re.sub(f"{new_schema}.", line)
            line = extensions_re.sub("public.", line)

            line = line.replace("search_path = public", f"search_path = {new_schema}")
            line = line.replace("extensions.uuid_generate_v4()", "gen_random_uuid()")
            line = line.replace("'extensions'", f"'{new_schema}'")

            fout.write(line)


def remap_data_file(src: str, dst: str, new_schema: str) -> None:
    """Rewrite data-only dump so INSERT/COPY target backup schema."""
    public_re = re.compile(r"(?<!\w)public\.")
    with (
        open(src, "r", encoding="utf-8") as fin,
        open(dst, "w", encoding="utf-8") as fout,
    ):
        for line in fin:
            fout.write(public_re.sub(f"{new_schema}.", line))


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
            cur.execute(f'CREATE SCHEMA IF NOT EXISTS "{new_schema}"')
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
                supabase_url,
            ],
            check=True,
            stdout=open(DATA_DUMP, "w"),
        )

        # ---------------------------
        # Remap schema + data
        # ---------------------------
        print(f"Remapping schema to {new_schema}...")
        remap_schema_file(SCHEMA_DUMP, SCHEMA_REMAPPED, new_schema)

        print(f"Remapping data to {new_schema}...")
        remap_data_file(DATA_DUMP, DATA_REMAPPED, new_schema)

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
        # Restore data
        # ---------------------------
        print("Restoring data into Neon...")

        subprocess.run(
            [
                "psql",
                neon_url,
                "-v",
                "ON_ERROR_STOP=1",
                "-f",
                DATA_REMAPPED,
            ],
            check=True,
        )

        print(f"Backup completed successfully in schema {new_schema}.")

    finally:
        for f in (
            SCHEMA_DUMP,
            SCHEMA_REMAPPED,
            DATA_DUMP,
            DATA_REMAPPED,
        ):
            if os.path.exists(f):
                os.remove(f)

        print(f"backup.schema={new_schema}")
        print("backup.timestamp=" + _timestamp())


if __name__ == "__main__":
    run()
