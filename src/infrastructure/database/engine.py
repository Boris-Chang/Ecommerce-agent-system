from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url

from core.exceptions import DatabaseConfigurationError
from core.settings import DatabaseSettings, get_database_settings


def create_database_engine(
    settings: DatabaseSettings | None = None,
) -> Engine:
    """Create a pooled PostgreSQL engine forced into read-only transactions."""
    resolved = settings or get_database_settings()
    url = make_url(resolved.database_url)

    if url.get_backend_name() != "postgresql" or url.get_driver_name() != "psycopg":
        raise DatabaseConfigurationError(
            "DATABASE_URL must use postgresql+psycopg:// for the application runtime."
        )

    options = " ".join(
        [
            f"-c statement_timeout={resolved.db_statement_timeout_ms}",
            "-c default_transaction_read_only=on",
            "-c timezone=UTC",
        ]
    )

    return create_engine(
        url,
        pool_size=resolved.db_pool_size,
        max_overflow=resolved.db_max_overflow,
        pool_timeout=resolved.db_pool_timeout,
        pool_pre_ping=True,
        echo=resolved.db_echo,
        connect_args={
            "application_name": resolved.db_application_name,
            "options": options,
        },
    )
