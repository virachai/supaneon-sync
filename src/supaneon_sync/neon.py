"""Minimal Neon API client skeleton.

This module provides a small wrapper to manage Neon branches. Implementations
should be tested with mocks; network calls are explicit and authorized by
`NEON_API_KEY`.
"""
from __future__ import annotations

import datetime
import requests
from dataclasses import dataclass

NEON_API_BASE = "https://api.neon.tech"  # placeholder; adjust if needed


@dataclass
class NeonBranch:
    name: str
    created_at: datetime.datetime


class NeonClient:
    def __init__(self, api_key: str, project_id: str | None = None):
        self.api_key = api_key
        self.project_id = project_id
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"})

    def _url(self, path: str) -> str:
        return f"{NEON_API_BASE}{path}"

    def create_branch(self, branch_name: str) -> NeonBranch:
        """Create a Neon branch. Returns NeonBranch dataclass on success."""
        # Example POST: /v1/projects/{project}/branches
        path = f"/v1/projects/{self.project_id}/branches" if self.project_id else "/v1/branches"
        resp = self.session.post(self._url(path), json={"name": branch_name})
        resp.raise_for_status()
        data = resp.json()
        return NeonBranch(name=data.get("name", branch_name), created_at=datetime.datetime.utcnow())

    def delete_branch(self, branch_name: str) -> None:
        path = f"/v1/projects/{self.project_id}/branches/{branch_name}" if self.project_id else f"/v1/branches/{branch_name}"
        resp = self.session.delete(self._url(path))
        resp.raise_for_status()

    def list_branches(self) -> list[NeonBranch]:
        path = f"/v1/projects/{self.project_id}/branches" if self.project_id else "/v1/branches"
        resp = self.session.get(self._url(path))
        resp.raise_for_status()
        data = resp.json()
        return [NeonBranch(name=b.get("name"), created_at=datetime.datetime.fromisoformat(b.get("created_at"))) for b in data.get("branches", [])]

    def latest_backup_branch(self) -> str | None:
        branches = self.list_branches()
        backups = [b for b in branches if b.name.startswith("backup-")]
        if not backups:
            return None
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups[0].name
