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
                    "SELECT table_name FROM information_schema.tables WHERE table_schema = %s",
                    (schema,),
                )
                tables = [row[0] for row in cur.fetchall()]

                if not tables:
                    raise ValueError(f"No tables found in schema '{schema}'")

                print(f"  Found {len(tables)} tables: {', '.join(tables)}")

                # Check at least one table has a 'data' column
                test_table = tables[0]
                cur.execute(
                    "SELECT column_name FROM information_schema.columns WHERE table_schema = %s AND table_name = %s AND column_name = 'data'",
                    (schema, test_table),
                )
                if not cur.fetchone():
                    raise ValueError(
                        f"Table '{test_table}' is missing the expected 'data' column"
                    )

                cur.execute(f'SELECT count(*) FROM "{test_table}"')
                row = cur.fetchone()
                count = row[0] if row is not None else 0
                print(f"  Verified table '{test_table}' has {count} rows.")

    except Exception as exc:  # pragma: no cover - integration-only
        raise SystemExit(f"Healthcheck failed for schema '{schema}': {exc}")
