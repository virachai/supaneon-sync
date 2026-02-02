"""Minimal Neon API client skeleton.

This module provides a small wrapper to manage Neon branches. Implementations
should be tested with mocks; network calls are explicit and authorized by
`NEON_API_KEY`.
"""

from __future__ import annotations

import datetime
import requests
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

NEON_API_BASE = "https://api.neon.tech"  # placeholder; adjust if needed


@dataclass
class NeonBranch:
    id: str
    name: str
    created_at: datetime.datetime
    # Host might not be available immediately upon create, but usually is via endpoints.
    host: str | None = None


class NeonClient:
    def __init__(self, api_key: str, project_id: str):
        self.api_key = api_key
        self.project_id = project_id

        # Configure retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,  # wait 1s, 2s, 4s
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST", "DELETE"],
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)

        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    def _url(self, path: str) -> str:
        return f"{NEON_API_BASE}{path}"

    def _request(self, method: str, path: str, **kwargs) -> requests.Response:
        url = self._url(path)
        try:
            resp = self.session.request(method, url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.exceptions.ConnectionError as e:
            # Provide a more helpful message for DNS/network issues
            raise SystemExit(
                f"ERROR: Could not connect to Neon API at {NEON_API_BASE}.\n"
                f"Details: {e}\n"
                "Please check your internet connection and DNS settings."
            ) from e
        except requests.exceptions.HTTPError as e:
            # Handle specific API errors
            err_msg = f"HTTP Error {e.response.status_code}: {e.response.text}"
            raise SystemExit(f"ERROR: Neon API request failed: {err_msg}") from e

    def create_branch(
        self, branch_name: str, parent_id: str | None = None
    ) -> NeonBranch:
        """Create a Neon branch. Returns NeonBranch dataclass on success."""
        # Example POST: /v1/projects/{project}/branches
        path = f"/v1/projects/{self.project_id}/branches"
        payload = {"name": branch_name}
        if parent_id:
            payload["parent_id"] = parent_id

        resp = self._request("POST", path, json=payload)
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

        return NeonBranch(
            id=branch_id,
            name=branch_data.get("name", branch_name),
            created_at=created_at,
            host=None,
        )

    def delete_branch(self, branch_id: str) -> None:
        """Delete a branch by its ID."""
        path = f"/v1/projects/{self.project_id}/branches/{branch_id}"
        self._request("DELETE", path)

    def list_branches(self) -> list[NeonBranch]:
        path = f"/v1/projects/{self.project_id}/branches"
        resp = self._request("GET", path)
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
                    host=None,
                )
            )
        return results

    def latest_backup_branch(
        self,
    ) -> NeonBranch | None:
        branches = self.list_branches()
        backups = [b for b in branches if b.name.startswith("backup-")]
        if not backups:
            return None
        backups.sort(key=lambda b: b.created_at, reverse=True)
        return backups[0]

    def get_branch_host(self, branch_id: str) -> str:
        """Fetch the read-write endpoint host for a branch."""
        path = f"/v1/projects/{self.project_id}/branches/{branch_id}/endpoints"
        resp = self._request("GET", path)
        data = resp.json()

        endpoints = data.get("endpoints", [])
        for ep in endpoints:
            if ep.get("type") == "read_write":
                return ep.get("host")

        if endpoints:
            return endpoints[0].get("host")

        raise RuntimeError(f"No endpoints found for branch {branch_id}")
