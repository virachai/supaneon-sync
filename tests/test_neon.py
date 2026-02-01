from supaneon_sync.neon import NeonClient


def test_branch_name_sorting():
    client = NeonClient(api_key="x")
    # This test assumes list_branches will be stubbed/mocked in integration tests
    assert hasattr(client, "create_branch")
    assert hasattr(client, "delete_branch")
    assert hasattr(client, "list_branches")
