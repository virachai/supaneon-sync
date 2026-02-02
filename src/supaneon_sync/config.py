import os
import re
from dataclasses import dataclass
from urllib.parse import urlparse

from dotenv import load_dotenv

load_dotenv()

REQUIRED_ENVS = ["SUPABASE_DATABASE_URL", "NEON_DATABASE_URL"]

DB_URL_RE = re.compile(r"^postgres(?:ql)?:\/\/.*[?&]sslmode=require")


@dataclass
class Config:
    supabase_database_url: str
    neon_database_url: str
    neon_api_key: str | None = None
    neon_project_id: str | None = None
    neon_db_password: str | None = None
    neon_db_user: str | None = None


def validate_env() -> Config:
    """Validate required environment variables.

    Raises SystemExit on validation errors.
    """
    missing = [k for k in REQUIRED_ENVS if k not in os.environ or not os.environ[k]]
    if missing:
        raise SystemExit(
            f"Missing required environment variables: {', '.join(missing)}"
        )

    supabase_url = os.environ["SUPABASE_DATABASE_URL"].strip()
    if not DB_URL_RE.search(supabase_url):
        raise SystemExit("SUPABASE_DATABASE_URL must include sslmode=require")

    neon_url = os.environ["NEON_DATABASE_URL"].strip()
    if not DB_URL_RE.search(neon_url):
        raise SystemExit("NEON_DATABASE_URL must include sslmode=require")

    neon_key = os.environ.get("NEON_API_KEY")
    if neon_key:
        neon_key = neon_key.strip()

    neon_project = os.environ.get("NEON_PROJECT_ID")
    if neon_project:
        neon_project = neon_project.strip()

    neon_password = os.environ.get("NEON_DB_PASSWORD")
    neon_user = os.environ.get("NEON_DB_USER")

    # Always parse NEON_DATABASE_URL for credentials if they aren't explicitly provided
    try:
        parsed = urlparse(neon_url)
        if parsed.password and not neon_password:
            neon_password = parsed.password
        if parsed.username and not neon_user:
            neon_user = parsed.username
    except Exception:
        pass

    return Config(
        supabase_database_url=supabase_url,
        neon_database_url=neon_url,
        neon_api_key=neon_key,
        neon_project_id=neon_project,
        neon_db_password=neon_password,
        neon_db_user=neon_user,
    )
