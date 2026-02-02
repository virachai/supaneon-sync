import unittest
from unittest.mock import MagicMock, patch
from supaneon_sync import backup


class TestSchemaRotation(unittest.TestCase):
    @patch("supaneon_sync.backup.subprocess.run")
    @patch("supaneon_sync.backup.psycopg.connect")
    @patch("supaneon_sync.backup.validate_env")
    def test_rotation_logic(self, mock_validate_env, mock_connect, mock_subprocess):
        # Setup mock config
        mock_cfg = MagicMock()
        mock_cfg.supabase_database_url = "postgres://supabase"
        mock_cfg.neon_database_url = "postgres://neon"
        mock_cfg.neon_db_user = "neonuser"
        mock_validate_env.return_value = mock_cfg

        # Setup mock database connection for list_backup_schemas
        mock_conn = mock_connect.return_value.__enter__.return_value
        mock_cur = mock_conn.cursor.return_value.__enter__.return_value

        # Simulated schemas: 7 existing backups
        existing_schemas = [f"backup_20230101T00000{i}Z" for i in range(7)]
        mock_cur.fetchall.return_value = [[s] for s in existing_schemas]

        # Mock supabase db dump output
        # In the new version, we use subprocess.run for pg_dump and psql
        # No need to mock return_value.stdout for psql

        # Run the backup
        # Need to mock 'builtins.open' because backup.py now reads/writes files
        with patch("builtins.open", MagicMock()):
            with patch("os.path.exists", return_value=True):
                with patch("os.remove", MagicMock()):
                    backup.run()

        # Verification:
        # 1. list_backup_schemas should be called
        # 2. deletion should be called for the oldest 2
        # while len(backup_schemas) >= max_schemas:
        # 7 >= 6: delete 1, left 6.
        # 6 >= 6: delete 1, left 5.
        # So 2 deletions.

        # Check for drops
        execute_calls = [call.args[0] for call in mock_cur.execute.call_args_list]
        drops = [c for c in execute_calls if "DROP SCHEMA" in c]
        self.assertEqual(len(drops), 2)

        # Check for create
        creates = [c for c in execute_calls if "CREATE SCHEMA" in c]
        self.assertGreaterEqual(len(creates), 1)


if __name__ == "__main__":
    unittest.main()
