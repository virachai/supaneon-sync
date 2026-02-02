import unittest
from unittest.mock import MagicMock, patch
from supaneon_sync import backup


class TestIPv4Fix(unittest.TestCase):
    @patch("supaneon_sync.backup.socket.getaddrinfo")
    def test_resolve_to_ipv4(self, mock_getaddrinfo):
        # Mock successful resolution
        mock_getaddrinfo.return_value = [(None, None, None, None, ("1.2.3.4", 5432))]

        ip = backup._resolve_to_ipv4("example.com")
        self.assertEqual(ip, "1.2.3.4")
        mock_getaddrinfo.assert_called_with(
            "example.com", None, backup.socket.AF_INET, backup.socket.SOCK_STREAM
        )

    @patch("supaneon_sync.backup.socket.getaddrinfo")
    def test_resolve_to_ipv4_failure(self, mock_getaddrinfo):
        # Mock failure
        mock_getaddrinfo.side_effect = backup.socket.gaierror(
            "Name or service not known"
        )

        ip = backup._resolve_to_ipv4("invalid.host")
        self.assertIsNone(ip)

    @patch("supaneon_sync.backup.subprocess.Popen")
    @patch("supaneon_sync.backup.socket.getaddrinfo")
    @patch("supaneon_sync.backup.psycopg.connect")
    @patch("supaneon_sync.backup.validate_env")
    def test_run_sets_pghostaddr(
        self, mock_validate_env, mock_connect, mock_getaddrinfo, mock_popen
    ):
        # Setup mock config
        mock_cfg = MagicMock()
        mock_cfg.supabase_database_url = (
            "postgres://user:pass@supabase.host:5432/db?sslmode=require"
        )
        mock_cfg.neon_database_url = (
            "postgres://user:pass@neon.host:5432/db?sslmode=require"
        )
        mock_cfg.neon_db_password = "password"
        mock_validate_env.return_value = mock_cfg

        # Mock IP resolution
        mock_getaddrinfo.return_value = [(None, None, None, None, ("1.2.3.4", 5432))]

        # Mock subprocess
        mock_popen.return_value.returncode = 0
        mock_popen.return_value.wait.return_value = 0
        mock_popen.return_value.poll.return_value = 0

        # Run backup
        backup.run()

        # Check if Popen for pg_dump was called with PGHOSTADDR
        # Find the call where the first argument is "pg_dump"
        pg_dump_call = None
        for call in mock_popen.call_args_list:
            if call.args[0][0] == "pg_dump":
                pg_dump_call = call
                break

        self.assertIsNotNone(pg_dump_call)
        env = pg_dump_call.kwargs.get("env")
        self.assertIsNotNone(env)
        self.assertEqual(env.get("PGHOSTADDR"), "1.2.3.4")


if __name__ == "__main__":
    unittest.main()
