"""Tests for the SKU sales application service."""

from datetime import date

import pytest

from application.dto.sku import SkuDailySales, SkuWeeklySales
from application.services import SkuSalesService


class FakeSalesAnalyticsRepository:
    def __init__(
        self,
        *,
        daily: list[SkuDailySales] | None = None,
        weekly: list[SkuWeeklySales] | None = None,
    ) -> None:
        self.daily = daily or []
        self.weekly = weekly or []
        self.calls: list[tuple[str, dict]] = []

    def list_sku_daily_sales(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 1_000,
    ) -> list[SkuDailySales]:
        self.calls.append(
            (
                "daily",
                {
                    "channel_account_id": channel_account_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                },
            )
        )
        return self.daily[:limit]

    def list_sku_weekly_sales(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10_000,
    ) -> list[SkuWeeklySales]:
        self.calls.append(
            (
                "weekly",
                {
                    "channel_account_id": channel_account_id,
                    "start_date": start_date,
                    "end_date": end_date,
                    "limit": limit,
                },
            )
        )
        return self.weekly[:limit]


def test_list_daily_sales_delegates_to_repository() -> None:
    row = SkuDailySales(
        sales_date=date(2026, 7, 20),
        sku_id="sku-1",
        channel_account_id="shopify-1",
        units_sold=3,
    )
    repository = FakeSalesAnalyticsRepository(daily=[row])
    service = SkuSalesService(repository)

    result = service.list_daily_sales(
        channel_account_id="shopify-1",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        limit=25,
    )

    assert result == [row]
    assert repository.calls == [
        (
            "daily",
            {
                "channel_account_id": "shopify-1",
                "start_date": date(2026, 7, 1),
                "end_date": date(2026, 7, 31),
                "limit": 25,
            },
        )
    ]


def test_list_weekly_sales_delegates_to_repository() -> None:
    row = SkuWeeklySales(
        week_start=date(2026, 7, 13),
        sku_id="sku-1",
        channel_account_id="amazon-us",
        units_sold=12,
    )
    repository = FakeSalesAnalyticsRepository(weekly=[row])
    service = SkuSalesService(repository)

    result = service.list_weekly_sales(
        channel_account_id="amazon-us",
        start_date=date(2026, 7, 13),
        end_date=date(2026, 7, 19),
        limit=50,
    )

    assert result == [row]
    assert repository.calls == [
        (
            "weekly",
            {
                "channel_account_id": "amazon-us",
                "start_date": date(2026, 7, 13),
                "end_date": date(2026, 7, 19),
                "limit": 50,
            },
        )
    ]


@pytest.mark.parametrize(
    ("start_date", "end_date", "limit", "message"),
    [
        (date(2026, 8, 1), date(2026, 7, 1), 10, "start_date"),
        (date(2026, 7, 1), date(2026, 7, 31), 0, "limit"),
        (date(2026, 7, 1), date(2026, 7, 31), 10_001, "limit"),
    ],
)
def test_service_rejects_invalid_query(
    start_date: date,
    end_date: date,
    limit: int,
    message: str,
) -> None:
    repository = FakeSalesAnalyticsRepository()
    service = SkuSalesService(repository)

    with pytest.raises(ValueError, match=message):
        service.list_daily_sales(
            channel_account_id="shopify-1",
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    assert repository.calls == []


def test_service_rejects_blank_channel_account() -> None:
    repository = FakeSalesAnalyticsRepository()
    service = SkuSalesService(repository)

    with pytest.raises(ValueError, match="channel_account_id"):
        service.list_daily_sales(
            channel_account_id=" ",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )

    assert repository.calls == []


def test_service_rejects_rows_from_another_channel() -> None:
    repository = FakeSalesAnalyticsRepository(
        daily=[
            SkuDailySales(
                sales_date=date(2026, 7, 20),
                sku_id="sku-1",
                channel_account_id="amazon-us",
            )
        ]
    )
    service = SkuSalesService(repository)

    with pytest.raises(ValueError, match="another channel"):
        service.list_daily_sales(
            channel_account_id="shopify-us",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
