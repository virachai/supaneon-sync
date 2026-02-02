import unittest
from unittest.mock import MagicMock, patch
from supaneon_sync import backup


class TestSchemaRotation(unittest.TestCase):
    @patch("supaneon_sync.backup.psycopg.connect")
    @patch("supaneon_sync.backup.pymongo.MongoClient")
    @patch("supaneon_sync.backup.validate_env")
    def test_rotation_logic(self, mock_validate_env, mock_mongo, mock_connect):
        # Setup mock config
        mock_cfg = MagicMock()
        mock_cfg.mongodb_srv_url = "mongodb://mongo"
        mock_cfg.neon_database_url = "postgres://neon"
        mock_cfg.neon_db_password = "pass"
        mock_validate_env.return_value = mock_cfg

        # Setup mock database connection for list_backup_schemas
        mock_conn = mock_connect.return_value.__enter__.return_value
        mock_cur = mock_conn.cursor.return_value.__enter__.return_value

        # Simulated schemas: 7 existing backups
        existing_schemas = [f"backup_20230101T00000{i}Z" for i in range(7)]
        mock_cur.fetchall.return_value = [[s] for s in existing_schemas]

        # Mock MongoDB
        mock_mongo_client = mock_mongo.return_value
        mock_db = mock_mongo_client.__getitem__.return_value
        mock_db.list_collection_names.return_value = ["coll1", "coll2"]
        mock_coll = mock_db.__getitem__.return_value
        mock_coll.find.return_value = [{"_id": "1", "name": "test"}]

        # Run the backup
        backup.run()

        # Verification:
        # 1. list_backup_schemas should be called
        # 2. deletion should be called for the oldest 2 (7 - 6 + 1 = 2)
        # Wait, max_schemas = 6. 7 existing. Delete 7-6 = 1?
        # Let's check rotation logic in backup.py:
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
        self.assertEqual(len(creates), 1)

        # Check for table creates for collections
        tbl_creates = [c for c in execute_calls if "CREATE TABLE" in c]
        self.assertEqual(len(tbl_creates), 2)


if __name__ == "__main__":
    unittest.main()
