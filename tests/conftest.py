import os
from collections.abc import Iterator

import pytest
from dotenv import load_dotenv
from sqlalchemy import Engine
from sqlalchemy.engine import make_url

from core.settings import DatabaseSettings
from infrastructure.database.engine import create_database_engine


load_dotenv()


@pytest.fixture(scope="session")
def database_test_settings() -> DatabaseSettings:
    """Return guarded settings for an isolated, read-only PostgreSQL test DB."""
    database_url = os.getenv("DATABASE_TEST_URL")
    if not database_url:
        pytest.skip("DATABASE_TEST_URL is not configured.")

    parsed = make_url(database_url)
    if parsed.get_backend_name() != "postgresql" or parsed.get_driver_name() != "psycopg":
        pytest.fail("DATABASE_TEST_URL must use postgresql+psycopg://.")
    if not parsed.database or not parsed.database.lower().endswith("_test"):
        pytest.fail("DATABASE_TEST_URL database name must end with '_test'.")

    return DatabaseSettings(
        DATABASE_URL=database_url,
        DB_APPLICATION_NAME="python_langchain_agent_tests",
    )


@pytest.fixture(scope="session")
def database_test_engine(
    database_test_settings: DatabaseSettings,
) -> Iterator[Engine]:
    engine = create_database_engine(database_test_settings)
    try:
        yield engine
    finally:
        engine.dispose()
