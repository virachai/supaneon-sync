"""Utility helpers for logging and safe printing."""
from __future__ import annotations

import logging
import re

logger = logging.getLogger("supaneon_sync")
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.setLevel(logging.INFO)

_sanitize_re = re.compile(r"postgres(?:ql)?://[^\s']+")


def safe_log(msg: str) -> None:
    """Log a message but redact database URLs to avoid leaking credentials."""
    redacted = _sanitize_re.sub("postgresql://<REDACTED>", msg)
    logger.info(redacted)
