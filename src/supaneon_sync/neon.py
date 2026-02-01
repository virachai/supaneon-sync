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
    id: str
    name: str
    created_at: datetime.datetime
    # Host might not be available immediately upon create, but usually is via endpoints.
    host: str | None = None


class NeonClient:
    def __init__(self, api_key: str, project_id: str | None = None):
        self.api_key = api_key
        self.project_id = project_id
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    def _url(self, path: str) -> str:
        return f"{NEON_API_BASE}{path}"

    def create_branch(
        self, branch_name: str, parent_id: str | None = None
    ) -> NeonBranch:
        """Create a Neon branch. Returns NeonBranch dataclass on success."""
        # Example POST: /v1/projects/{project}/branches
        path = (
            f"/v1/projects/{self.project_id}/branches"
            if self.project_id
            else "/v1/branches"
        )
        payload = {"name": branch_name}
        if parent_id:
            payload["parent_id"] = parent_id

        resp = self.session.post(self._url(path), json=payload)
        resp.raise_for_status()
        data = resp.json()

        # Depending on API response, we might get the endpoint host here or need a separate call.
        # Usually 'branch' object contains 'endpoints'.
        # Let's try to extract it if present.
        branch_data = data.get("branch", data)  # Some APIs wrap in 'branch'

        branch_id = branch_data.get("id")
        created_at_str = branch_data.get("created_at")

        # Ensure we have a valid datetime
        created_at = (
            datetime.datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            if created_at_str
            else datetime.datetime.utcnow()
        )

        # Check for endpoints
        host = None
        # Often the create response includes computed endpoints or we need to fetch them.
        # For robustness, we can call get_branch_endpoints(branch_id) if missing.

        return NeonBranch(
            id=branch_id,
            name=branch_data.get("name", branch_name),
            created_at=created_at,
            host=host,
        )

    def delete_branch(self, branch_id: str) -> None:
        """Delete a branch by its ID.

        Note: The Neon API DELETE endpoint expects a branch ID in the URL path.
        While the parameter was historically named 'branch_name', it should be
        passed a branch ID (from NeonBranch.id) for correct operation.
        """
        path = (
            f"/v1/projects/{self.project_id}/branches/{branch_id}"
            if self.project_id
            else f"/v1/branches/{branch_id}"
        )
        resp = self.session.delete(self._url(path))
        resp.raise_for_status()

    def list_branches(self) -> list[NeonBranch]:
        path = (
            f"/v1/projects/{self.project_id}/branches"
            if self.project_id
            else "/v1/branches"
        )
        resp = self.session.get(self._url(path))
        resp.raise_for_status()
        data = resp.json()

        results = []
        for b in data.get("branches", []):
            results.append(
                NeonBranch(
                    id=b.get("id"),
                    name=b.get("name"),
                    created_at=datetime.datetime.fromisoformat(
                        b.get("created_at").replace("Z", "+00:00")
                    ),
                    host=None,  # endpoints usually require separate pass or deep inspection
                )
            )
        return results

    def latest_backup_branch(
        self,
    ) -> NeonBranch | None:  # Return full object not just string
        branches = self.list_branches()
        backups = [b for b in branches if b.name.startswith("backup-")]
        if not backups:
            return None
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups[0]

    def get_branch_host(self, branch_id: str) -> str:
        """Fetch the read-write endpoint host for a branch."""
        # GET /projects/{project_id}/branches/{branch_id}/endpoints
        path = f"/v1/projects/{self.project_id}/branches/{branch_id}/endpoints"
        resp = self.session.get(self._url(path))
        resp.raise_for_status()
        data = resp.json()

        endpoints = data.get("endpoints", [])
        for ep in endpoints:
            if ep.get("type") == "read_write":
                return ep.get("host")

        # Fallback if no specific RW found (rare)
        if endpoints:
            return endpoints[0].get("host")

        raise RuntimeError(f"No endpoints found for branch {branch_id}")
