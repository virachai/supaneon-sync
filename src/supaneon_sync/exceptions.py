class SupaNeonError(Exception):
    """Base exception for the supaneon-sync package."""


class ConfigError(SupaNeonError):
    pass


class BackupError(SupaNeonError):
    pass


class RestoreError(SupaNeonError):
    pass
