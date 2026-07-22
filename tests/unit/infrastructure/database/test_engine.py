import pytest

from core.exceptions import DatabaseConfigurationError
from core.settings import DatabaseSettings
from infrastructure.database import engine as engine_module


def _settings(database_url: str = "postgresql+psycopg://app:secret@localhost/db"):
    return DatabaseSettings(
        DATABASE_URL=database_url,
        DB_POOL_SIZE=3,
        DB_MAX_OVERFLOW=2,
        DB_POOL_TIMEOUT=10,
        DB_STATEMENT_TIMEOUT_MS=5000,
        DB_ECHO=False,
        DB_APPLICATION_NAME="test-suite",
    )


def test_engine_configuration_forces_read_only(monkeypatch) -> None:
    captured = {}

    def fake_create_engine(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return "engine"

    monkeypatch.setattr(engine_module, "create_engine", fake_create_engine)

    result = engine_module.create_database_engine(_settings())

    assert result == "engine"
    assert captured["pool_size"] == 3
    assert captured["pool_pre_ping"] is True
    assert captured["connect_args"]["application_name"] == "test-suite"
    assert "default_transaction_read_only=on" in captured["connect_args"]["options"]
    assert "statement_timeout=5000" in captured["connect_args"]["options"]


def test_engine_rejects_non_postgresql_url() -> None:
    with pytest.raises(DatabaseConfigurationError):
        engine_module.create_database_engine(_settings("sqlite:///test.db"))
