"""Deterministic smoke tests run against a Neon branch DB URL."""
from __future__ import annotations

import psycopg


def run_healthcheck(db_url: str) -> None:
    """Run a set of deterministic, fast, non-destructive checks.

    Raises SystemExit on failure.
    """
    try:
        with psycopg.connect(db_url, autocommit=True) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
                # Placeholder: check for expected schemas/tables
                # cur.execute("SELECT to_regclass('public.some_table')")
    except Exception as exc:  # pragma: no cover - integration-only
        raise SystemExit(f"Healthcheck failed: {exc}")
