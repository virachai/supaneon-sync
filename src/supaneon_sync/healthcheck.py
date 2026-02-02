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
                cur.execute("SELECT 1")
                cur.fetchone()
                # Additional checks could go here
    except Exception as exc:  # pragma: no cover - integration-only
        raise SystemExit(f"Healthcheck failed for schema '{schema}': {exc}")
