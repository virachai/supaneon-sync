import pytest

from supaneon_sync.config import validate_env


def test_validate_env_missing(monkeypatch):
    monkeypatch.delenv("MONGODB_SRV_URL", raising=False)
    monkeypatch.delenv("NEON_DATABASE_URL", raising=False)
    with pytest.raises(SystemExit):
        validate_env()


def test_validate_env_requires_mongo_scheme(monkeypatch):
    monkeypatch.setenv("MONGODB_SRV_URL", "postgres://user@localhost/db")
    monkeypatch.setenv(
        "NEON_DATABASE_URL", "postgres://user@localhost/db?sslmode=require"
    )
    with pytest.raises(SystemExit):
        validate_env()


def test_validate_env_ok(monkeypatch):
    monkeypatch.setenv("MONGODB_SRV_URL", "mongodb+srv://user@cluster.mongodb.net/db")
    monkeypatch.setenv(
        "NEON_DATABASE_URL", "postgres://user@localhost/db?sslmode=require"
    )
    cfg = validate_env()
    assert cfg.mongodb_srv_url.startswith("mongodb+srv://")
    assert cfg.neon_database_url.endswith("sslmode=require")
