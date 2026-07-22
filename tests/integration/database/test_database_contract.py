import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError

from infrastructure.database.health import check_database_health
from infrastructure.database.schema_validation import validate_live_database


pytestmark = pytest.mark.integration


def test_database_is_read_only_and_matches_baseline(
    database_test_engine,
    database_test_settings,
) -> None:
    health = check_database_health(database_test_engine)
    contract = validate_live_database(database_test_engine)
    expected_database = make_url(database_test_settings.database_url).database

    assert health.healthy is True
    assert health.read_only is True
    assert health.database_name == expected_database
    assert contract.matched is True
    assert contract.actual_schema_count == 12
    assert contract.actual_table_count == 77


def test_application_connection_rejects_business_schema_ddl(
    database_test_engine,
) -> None:
    with database_test_engine.connect() as connection:
        with pytest.raises(DBAPIError):
            connection.execute(
                text("CREATE TABLE sales.__read_only_test_probe (id integer)")
            )
