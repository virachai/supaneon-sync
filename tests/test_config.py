import pytest

from supaneon_sync.config import validate_env


def test_validate_env_missing(monkeypatch):
    monkeypatch.delenv("SUPABASE_DATABASE_URL", raising=False)
    monkeypatch.delenv("NEON_DATABASE_URL", raising=False)
    with pytest.raises(SystemExit):
        validate_env()


def test_validate_env_requires_sslmode(monkeypatch):
    monkeypatch.setenv("SUPABASE_DATABASE_URL", "postgres://user@localhost/db")
    monkeypatch.setenv(
        "NEON_DATABASE_URL", "postgres://user@localhost/db?sslmode=require"
    )
    with pytest.raises(SystemExit):
        validate_env()


def test_validate_env_ok(monkeypatch):
    monkeypatch.setenv("SUPABASE_DATABASE_URL", "postgres://user@localhost/db?sslmode=require")
    monkeypatch.setenv(
        "NEON_DATABASE_URL", "postgres://user@localhost/db?sslmode=require"
    )
    cfg = validate_env()
    assert cfg.supabase_database_url.startswith("postgres")
    assert cfg.supabase_database_url.endswith("sslmode=require")
    assert cfg.neon_database_url.endswith("sslmode=require")


