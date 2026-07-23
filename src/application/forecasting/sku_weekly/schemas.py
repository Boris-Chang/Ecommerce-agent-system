"""Pure data structures used by the SKU weekly forecasting model."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal


@dataclass(frozen=True)
class WeeklyDemandPoint:
    week_start: date
    units_sold: Decimal


@dataclass(frozen=True)
class ForecastEstimate:
    week_start: date
    forecast_p50: Decimal
    forecast_p90: Decimal
