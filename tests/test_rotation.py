import unittest
from unittest.mock import MagicMock, patch
from supaneon_sync import backup


class TestSchemaRotation(unittest.TestCase):
    @patch("supaneon_sync.backup.psycopg.connect")
    @patch("supaneon_sync.backup.subprocess.Popen")
    @patch("supaneon_sync.backup.validate_env")
    def test_rotation_logic(self, mock_validate_env, mock_popen, mock_connect):
        # Setup mock config
        mock_cfg = MagicMock()
        mock_cfg.supabase_database_url = "postgres://supa"
        mock_cfg.neon_database_url = "postgres://neon"
        mock_cfg.neon_db_password = "pass"
        mock_validate_env.return_value = mock_cfg

        # Setup mock database connection for list_backup_schemas
        mock_conn = mock_connect.return_value.__enter__.return_value
        mock_cur = mock_conn.cursor.return_value.__enter__.return_value

        # Simulated schemas: 7 existing backups
        existing_schemas = [f"backup_20230101T00000{i}Z" for i in range(7)]
        mock_cur.fetchall.return_value = [[s] for s in existing_schemas]

        # Mock subprocess to avoid actual execution
        mock_popen.return_value.returncode = 0
        mock_popen.return_value.wait.return_value = 0
        mock_popen.return_value.poll.return_value = 0

        # Run the backup
        backup.run()

        # Verification:
        # 1. list_backup_schemas should be called (via the cursor execute)
        # 2. deletion should be called for the oldest 2 (7 - 5 = 2)
        # The oldest are indices 0 and 1.
        
        # We need to check the execute calls on the cursor
        execute_calls = [call.args[0] for call in mock_cur.execute.call_args_list]
        
        # Check for drops
        # Expected: DROP SCHEMA IF EXISTS "backup_20230101T000000Z" CASCADE
        # Expected: DROP SCHEMA IF EXISTS "backup_20230101T000001Z" CASCADE
        drops = [c for c in execute_calls if "DROP SCHEMA" in c]
        self.assertEqual(len(drops), 2)
        self.assertIn("backup_20230101T000000Z", drops[0])
        self.assertIn("backup_20230101T000001Z", drops[1])

        # Check for create
        creates = [c for c in execute_calls if "CREATE SCHEMA" in c]
        self.assertEqual(len(creates), 1)

        # Check subprocess calls (dump | sed | psql)
        self.assertEqual(mock_popen.call_count, 3)


if __name__ == "__main__":
    unittest.main()
