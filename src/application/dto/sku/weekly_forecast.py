from datetime import date, datetime
from decimal import Decimal

from pydantic import Field

from application.dto.common import ReadModel


class SkuWeeklyForecast(ReadModel):
    forecast_id: str
    forecast_run_id: str
    sku_id: str
    warehouse_id: str | None = None
    channel_account_id: str
    week_start: date
    forecast_p50: Decimal = Field(ge=0)
    forecast_p90: Decimal = Field(ge=0)
    actual_units: int | None = Field(default=None, ge=0)
    data_origin: str


class SkuForecastRun(ReadModel):
    forecast_run_id: str
    channel_account_id: str
    model_name: str
    model_version: str
    training_start: date
    training_end: date
    generated_at: datetime
    parameters_json: dict[str, object]
    status: str
    forecasts: tuple[SkuWeeklyForecast, ...]
