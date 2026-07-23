from datetime import date, timedelta
from decimal import Decimal

import pytest

from application.forecasting.sku_weekly import (
    WeeklyDemandPoint,
    WeightedMovingAverageForecaster,
)
from application.forecasting.sku_weekly.features import fill_missing_weeks


def _history(*units: int) -> list[WeeklyDemandPoint]:
    first_week = date(2026, 4, 13)
    return [
        WeeklyDemandPoint(
            week_start=first_week + timedelta(days=7 * index),
            units_sold=Decimal(value),
        )
        for index, value in enumerate(units)
    ]


def test_forecast_uses_recent_weights_and_damped_trend() -> None:
    forecaster = WeightedMovingAverageForecaster()

    forecasts = forecaster.forecast(_history(10, 12, 14, 16), horizon_weeks=2)

    assert [row.week_start for row in forecasts] == [
        date(2026, 5, 11),
        date(2026, 5, 18),
    ]
    assert [row.forecast_p50 for row in forecasts] == [
        Decimal("15.000000"),
        Decimal("16.000000"),
    ]
    assert all(row.forecast_p90 >= row.forecast_p50 for row in forecasts)


def test_forecast_p90_adds_backtested_upper_demand_error() -> None:
    forecaster = WeightedMovingAverageForecaster()

    forecasts = forecaster.forecast(
        _history(10, 10, 10, 10, 20),
        horizon_weeks=1,
    )

    assert forecasts[0].forecast_p90 > forecasts[0].forecast_p50


def test_missing_weeks_are_filled_with_zero_demand() -> None:
    normalized = fill_missing_weeks(
        [
            WeeklyDemandPoint(date(2026, 4, 13), Decimal("8")),
            WeeklyDemandPoint(date(2026, 4, 27), Decimal("12")),
        ]
    )

    assert normalized == [
        WeeklyDemandPoint(date(2026, 4, 13), Decimal("8")),
        WeeklyDemandPoint(date(2026, 4, 20), Decimal("0")),
        WeeklyDemandPoint(date(2026, 4, 27), Decimal("12")),
    ]


def test_forecast_rejects_invalid_history_and_horizon() -> None:
    forecaster = WeightedMovingAverageForecaster()

    with pytest.raises(ValueError, match="at least two weeks"):
        forecaster.forecast(_history(10))

    with pytest.raises(ValueError, match="between 1 and 52"):
        forecaster.forecast(_history(10, 12), horizon_weeks=0)

    with pytest.raises(ValueError, match="Monday"):
        forecaster.forecast(
            [
                WeeklyDemandPoint(date(2026, 4, 14), Decimal("10")),
                WeeklyDemandPoint(date(2026, 4, 21), Decimal("12")),
            ]
        )
