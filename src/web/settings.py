from datetime import date

from pydantic import Field, PositiveInt
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class WebSettings(BaseSettings):
    """Server-rendered dashboard defaults."""

    web_title: str = Field(default="Ecommerce BI", validation_alias="WEB_TITLE")
    web_default_channel_account_id: str = Field(
        default="CA_SHOPIFY_US",
        validation_alias="WEB_DEFAULT_CHANNEL_ACCOUNT_ID",
    )
    web_channel_account_ids: str = Field(
        default="CA_SHOPIFY_US,CA_AMAZON_US",
        validation_alias="WEB_CHANNEL_ACCOUNT_IDS",
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
    web_overview_query_limit: int = Field(
        default=10_000,
        ge=1,
        le=10_000,
        validation_alias="WEB_OVERVIEW_QUERY_LIMIT",
    )
    web_default_end_date: date | None = Field(
        default=None,
        validation_alias="WEB_DEFAULT_END_DATE",
    )

    @field_validator(
        "web_default_channel_account_id",
        "web_channel_account_ids",
    )
    @classmethod
    def validate_channel_configuration_text(cls, value: str) -> str:
        resolved = value.strip()
        if not resolved:
            raise ValueError("Web channel configuration must not be blank.")
        return resolved

    @model_validator(mode="after")
    def validate_default_channel_is_allowed(self) -> "WebSettings":
        if self.web_default_channel_account_id not in self.channel_account_ids:
            raise ValueError(
                "WEB_DEFAULT_CHANNEL_ACCOUNT_ID must be included in "
                "WEB_CHANNEL_ACCOUNT_IDS."
            )
        return self

    @property
    def channel_account_ids(self) -> tuple[str, ...]:
        values = tuple(
            dict.fromkeys(
                value.strip()
                for value in self.web_channel_account_ids.split(",")
                if value.strip()
            )
        )
        if not values:
            raise ValueError(
                "WEB_CHANNEL_ACCOUNT_IDS must contain at least one channel."
            )
        return values

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )
