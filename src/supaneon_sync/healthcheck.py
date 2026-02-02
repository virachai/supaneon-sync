"""Deterministic smoke tests run against a Neon branch DB URL."""

from __future__ import annotations

import psycopg


def run_healthcheck(db_url: str, schema: str = "public") -> None:
    """Run a set of deterministic, fast, non-destructive checks against a specific schema.

    Raises SystemExit on failure.
    """
    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                # Set search_path so we query the backup schema instead of public
                cur.execute(f'SET search_path TO "{schema}"')

                # Check for table existence
                cur.execute(
                    "SELECT table_name "
                    "FROM information_schema.tables "
                    "WHERE table_schema = %s",
                    (schema,),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError(
                        f"COUNT query returned no rows for schema '{schema}'"
                    )

                tables = [row[0] for row in cur.fetchall()]

                if not tables:
                    raise ValueError(f"No tables found in schema '{schema}'")

                print(f"  Found {len(tables)} tables: {', '.join(tables)}")

                # Check at least one table has rows
                total_rows = 0
                for table in tables:
                    cur.execute(f'SELECT count(*) FROM "{schema}"."{table}"')

                    row = cur.fetchone()
                    if row is None:
                        raise ValueError(
                            f"COUNT query returned no rows for table '{table}'"
                        )

                    count: int = row[0]
                    total_rows += count

                    if count > 0:
                        print(f"  Verified table '{table}' has {count} rows.")

                if total_rows == 0:
                    raise ValueError(f"All tables in schema '{schema}' are empty")

                print(f"  Total rows across all tables: {total_rows}")

    except Exception as exc:  # pragma: no cover - integration-only
        raise SystemExit(f"Healthcheck failed for schema '{schema}': {exc}")
