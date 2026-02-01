def test_backup_run_smoke():
    # smoke test placeholder: ensure module importable
    import supaneon_sync.backup as b

    assert hasattr(b, "run")
