import unittest
from unittest.mock import MagicMock, patch
import datetime
from supaneon_sync.neon import NeonBranch

# Import the module where 'run' is defined.
# We will patch 'supaneon_sync.backup.NeonClient'
from supaneon_sync import backup


class TestBranchRotation(unittest.TestCase):
    @patch("supaneon_sync.backup.NeonClient")
    @patch("supaneon_sync.backup.subprocess")
    @patch("supaneon_sync.backup.validate_env")
    def test_rotation_logic(self, mock_validate_env, mock_subprocess, MockNeonClient):
        # Setup mock config
        mock_cfg = MagicMock()
        mock_cfg.supabase_database_url = "postgres://supa"
        mock_cfg.neon_api_key = "neonc"
        mock_cfg.neon_project_id = "proj"
        mock_cfg.neon_db_password = "pass"
        mock_validate_env.return_value = mock_cfg

        # Setup mock client instance
        client = MockNeonClient.return_value

        # simulated branches: 7 existing backups (oldest first)
        base_time = datetime.datetime(2023, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc)
        branches = []
        for i in range(7):
            branches.append(
                NeonBranch(
                    id=f"id-{i}",
                    name=f"backup-20230101T00000{i}Z",
                    created_at=base_time + datetime.timedelta(minutes=i),
                    host="host",
                )
            )
        # Add a non-backup branch to ensure it's ignored
        branches.append(
            NeonBranch(id="id-other", name="main", created_at=base_time, host="host")
        )

        client.list_branches.return_value = branches

        # Setup create_branch return
        new_branch = NeonBranch(
            id="new-id",
            name="backup-NEW",
            created_at=datetime.datetime.now(),
            host="new-host",
        )
        client.create_branch.return_value = new_branch
        client.get_branch_host.return_value = "new-host"

        # mock subprocess to avoid actual execution
        mock_subprocess.Popen.return_value.returncode = 0
        mock_subprocess.Popen.return_value.wait.return_value = 0
        mock_subprocess.Popen.return_value.poll.side_effect = [None, 0]  # wait loop

        # Run the backup
        backup.run()

        # Verification
        # We expect 7 existing backups. Limit is 6.
        # So it should delete existing backups until count is 5 (so new one makes 6).
        # Meaning: 7 - 5 = 2 deletions needed.
        # The oldest are index 0 and 1.

        # The implementation correctly passes branch IDs to delete_branch()
        # even though the parameter is misleadingly named "branch_name"
        # The Neon API DELETE endpoint expects branch IDs in the URL path
        expected_deleted_ids = ["id-0", "id-1"]

        # Verify delete_branch calls
        self.assertEqual(client.delete_branch.call_count, 2)

        # Check that delete_branch was called with branch IDs (not names)
        calls = client.delete_branch.call_args_list
        # call_args_list is list of calls, each call is (args, kwargs)
        deleted_ids = [c[0][0] for c in calls]

        self.assertEqual(sorted(deleted_ids), sorted(expected_deleted_ids))


if __name__ == "__main__":
    unittest.main()
