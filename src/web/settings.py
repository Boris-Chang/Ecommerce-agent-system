from datetime import date

from pydantic import Field, PositiveInt
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebSettings(BaseSettings):
    """Server-rendered dashboard defaults."""

    web_title: str = Field(default="Ecommerce BI", validation_alias="WEB_TITLE")
    web_default_channel_account_id: str = Field(
        default="CA_SHOPIFY_US",
        validation_alias="WEB_DEFAULT_CHANNEL_ACCOUNT_ID",
    )
    web_sales_lookback_days: PositiveInt = Field(
        default=90,
        validation_alias="WEB_SALES_LOOKBACK_DAYS",
    )
    web_query_limit: int = Field(
        default=500,
        ge=1,
        le=10_000,
        validation_alias="WEB_QUERY_LIMIT",
    )
    web_default_end_date: date | None = Field(
        default=None,
        validation_alias="WEB_DEFAULT_END_DATE",
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
