from dataclasses import dataclass

from sqlalchemy import Engine, text


@dataclass(frozen=True)
class DatabaseHealth:
    healthy: bool
    database_name: str
    read_only: bool


def check_database_health(engine: Engine) -> DatabaseHealth:
    """Run a read-only readiness check without changing database state."""
    with engine.connect() as connection:
        row = connection.execute(
            text(
                """
                SELECT
                    current_database() AS database_name,
                    current_setting('transaction_read_only') AS transaction_read_only
                """
            )
        ).mappings().one()

    read_only = row["transaction_read_only"] == "on"
    return DatabaseHealth(
        healthy=read_only,
        database_name=row["database_name"],
        read_only=read_only,
    )
