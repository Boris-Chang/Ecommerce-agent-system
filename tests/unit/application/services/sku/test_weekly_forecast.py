"""Tests for the SKU weekly forecast application service."""

from datetime import date, datetime, timezone
from uuid import UUID

import pytest

from application.dto.sku import SkuWeeklySales
from application.services import SkuWeeklyForecastService


CHANNEL_ACCOUNT_ID = "channel-1"


class FakeSalesAnalyticsRepository:
    def __init__(self, rows: list[SkuWeeklySales]) -> None:
        self.rows = rows
        self.calls: list[dict] = []

    def list_sku_weekly_sales(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10_000,
    ) -> list[SkuWeeklySales]:
        self.calls.append(
            {
                "channel_account_id": channel_account_id,
                "start_date": start_date,
                "end_date": end_date,
                "limit": limit,
            }
        )
        return self.rows[:limit]


def test_service_generates_versioned_forecast_run_per_sku() -> None:
    repository = FakeSalesAnalyticsRepository(
        [
            SkuWeeklySales(
                week_start=date(2026, 6, 15),
                sku_id="sku-b",
                channel_account_id=CHANNEL_ACCOUNT_ID,
                units_sold=8,
            ),
            SkuWeeklySales(
                week_start=date(2026, 6, 22),
                sku_id="sku-b",
                channel_account_id=CHANNEL_ACCOUNT_ID,
                units_sold=10,
            ),
            SkuWeeklySales(
                week_start=date(2026, 6, 15),
                sku_id="sku-a",
                channel_account_id=CHANNEL_ACCOUNT_ID,
                units_sold=4,
            ),
            SkuWeeklySales(
                week_start=date(2026, 6, 22),
                sku_id="sku-a",
                channel_account_id=CHANNEL_ACCOUNT_ID,
                units_sold=6,
            ),
        ]
    )
    generated_at = datetime(2026, 7, 1, 8, tzinfo=timezone.utc)
    service = SkuWeeklyForecastService(
        repository,
        clock=lambda: generated_at,
        id_factory=lambda: UUID("12345678-1234-5678-1234-567812345678"),
    )

    result = service.generate(
        channel_account_id=CHANNEL_ACCOUNT_ID,
        training_start=date(2026, 6, 15),
        training_end=date(2026, 6, 28),
        horizon_weeks=2,
    )

    assert result.forecast_run_id == (
        "FCRUN-12345678123456781234567812345678"
    )
    assert result.model_name == "sku_weighted_moving_average"
    assert result.model_version == "v0.1"
    assert result.channel_account_id == CHANNEL_ACCOUNT_ID
    assert result.generated_at == generated_at
    assert result.status == "calculated"
    assert len(result.forecasts) == 4
    assert [row.sku_id for row in result.forecasts] == [
        "sku-a",
        "sku-a",
        "sku-b",
        "sku-b",
    ]
    assert result.forecasts[0].week_start == date(2026, 6, 29)
    assert all(
        row.channel_account_id == CHANNEL_ACCOUNT_ID
        for row in result.forecasts
    )
    assert result.parameters_json["series_grain"] == "sku_channel_account"
    assert repository.calls == [
        {
            "channel_account_id": CHANNEL_ACCOUNT_ID,
            "start_date": date(2026, 6, 15),
            "end_date": date(2026, 6, 28),
            "limit": 10_000,
        }
    ]


def test_service_skips_sku_with_less_than_two_weeks() -> None:
    repository = FakeSalesAnalyticsRepository(
        [
            SkuWeeklySales(
                week_start=date(2026, 6, 15),
                sku_id="new-sku",
                channel_account_id=CHANNEL_ACCOUNT_ID,
                units_sold=1,
            ),
            SkuWeeklySales(
                week_start=date(2026, 6, 15),
                sku_id="ready-sku",
                channel_account_id=CHANNEL_ACCOUNT_ID,
                units_sold=4,
            ),
            SkuWeeklySales(
                week_start=date(2026, 6, 22),
                sku_id="ready-sku",
                channel_account_id=CHANNEL_ACCOUNT_ID,
                units_sold=6,
            ),
        ]
    )
    service = SkuWeeklyForecastService(repository)

    result = service.generate(
        channel_account_id=CHANNEL_ACCOUNT_ID,
        training_start=date(2026, 6, 15),
        training_end=date(2026, 6, 28),
        horizon_weeks=1,
    )

    assert [row.sku_id for row in result.forecasts] == ["ready-sku"]


def test_service_fills_trailing_no_sales_weeks_before_forecasting() -> None:
    repository = FakeSalesAnalyticsRepository(
        [
            SkuWeeklySales(
                week_start=date(2026, 6, 15),
                sku_id="sku-a",
                channel_account_id=CHANNEL_ACCOUNT_ID,
                units_sold=10,
            ),
            SkuWeeklySales(
                week_start=date(2026, 6, 22),
                sku_id="sku-a",
                channel_account_id=CHANNEL_ACCOUNT_ID,
                units_sold=12,
            ),
        ]
    )
    service = SkuWeeklyForecastService(repository)

    result = service.generate(
        channel_account_id=CHANNEL_ACCOUNT_ID,
        training_start=date(2026, 6, 15),
        training_end=date(2026, 7, 5),
        horizon_weeks=1,
    )

    assert result.forecasts[0].week_start == date(2026, 7, 6)


def test_service_requires_complete_monday_to_sunday_training_period() -> None:
    repository = FakeSalesAnalyticsRepository([])
    service = SkuWeeklyForecastService(repository)

    with pytest.raises(ValueError, match="Monday"):
        service.generate(
            channel_account_id=CHANNEL_ACCOUNT_ID,
            training_start=date(2026, 6, 16),
            training_end=date(2026, 6, 28),
        )

    with pytest.raises(ValueError, match="Sunday"):
        service.generate(
            channel_account_id=CHANNEL_ACCOUNT_ID,
            training_start=date(2026, 6, 15),
            training_end=date(2026, 6, 27),
        )

    assert repository.calls == []


def test_service_rejects_blank_channel_account() -> None:
    repository = FakeSalesAnalyticsRepository([])
    service = SkuWeeklyForecastService(repository)

    with pytest.raises(ValueError, match="channel_account_id"):
        service.generate(
            channel_account_id=" ",
            training_start=date(2026, 6, 15),
            training_end=date(2026, 6, 28),
        )

    assert repository.calls == []


def test_service_rejects_training_rows_from_another_channel() -> None:
    repository = FakeSalesAnalyticsRepository(
        [
            SkuWeeklySales(
                week_start=date(2026, 6, 15),
                sku_id="sku-a",
                channel_account_id="amazon-us",
                units_sold=10,
            ),
            SkuWeeklySales(
                week_start=date(2026, 6, 22),
                sku_id="sku-a",
                channel_account_id="amazon-us",
                units_sold=12,
            ),
        ]
    )
    service = SkuWeeklyForecastService(repository)

    with pytest.raises(ValueError, match="another channel"):
        service.generate(
            channel_account_id="shopify-us",
            training_start=date(2026, 6, 15),
            training_end=date(2026, 6, 28),
        )
