from functools import lru_cache

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseSettings(BaseSettings):
    """PostgreSQL runtime configuration loaded without import-time side effects."""

    database_url: str = Field(validation_alias="DATABASE_URL")
    db_pool_size: PositiveInt = Field(default=5, validation_alias="DB_POOL_SIZE")
    db_max_overflow: int = Field(default=5, ge=0, validation_alias="DB_MAX_OVERFLOW")
    db_pool_timeout: PositiveInt = Field(default=30, validation_alias="DB_POOL_TIMEOUT")
    db_statement_timeout_ms: PositiveInt = Field(
        default=15_000,
        validation_alias="DB_STATEMENT_TIMEOUT_MS",
    )
    db_echo: bool = Field(default=False, validation_alias="DB_ECHO")
    db_application_name: str = Field(
        default="python_langchain_agent",
        validation_alias="DB_APPLICATION_NAME",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_database_settings() -> DatabaseSettings:
    return DatabaseSettings()
