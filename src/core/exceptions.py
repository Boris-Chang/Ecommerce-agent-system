class DatabaseConfigurationError(RuntimeError):
    """Raised when database runtime configuration is unsafe or incomplete."""


class DatabaseContractError(RuntimeError):
    """Raised when the live database does not match the approved baseline."""
