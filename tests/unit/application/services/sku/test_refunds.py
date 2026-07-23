"""Tests for the SKU refund application service."""

from datetime import date

import pytest

from application.dto.sku import SkuDailyRefunds, SkuWeeklyRefunds
from application.services import SkuRefundService


class FakeSkuRefundRepository:
    def __init__(
        self,
        *,
        daily: list[SkuDailyRefunds] | None = None,
        weekly: list[SkuWeeklyRefunds] | None = None,
    ) -> None:
        self.daily = daily or []
        self.weekly = weekly or []
        self.calls: list[tuple[str, dict]] = []

    def list_sku_daily_refunds(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 1_000,
    ) -> list[SkuDailyRefunds]:
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

    def list_sku_weekly_refunds(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10_000,
    ) -> list[SkuWeeklyRefunds]:
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


def test_list_daily_refunds_delegates_to_repository() -> None:
    row = SkuDailyRefunds(
        refund_date=date(2026, 7, 20),
        sku_id="sku-1",
        channel_account_id="shopify-1",
        refund_count=2,
        refunded_order_count=1,
        refunded_units=2,
        item_refund_amount="18.50",
        tax_refund_amount="1.50",
        shipping_refund_amount="0",
    )
    repository = FakeSkuRefundRepository(daily=[row])
    service = SkuRefundService(repository)

    result = service.list_daily_refunds(
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


def test_list_weekly_refunds_delegates_to_repository() -> None:
    row = SkuWeeklyRefunds(
        week_start=date(2026, 7, 13),
        sku_id="sku-1",
        channel_account_id="amazon-us",
        refund_count=3,
        refunded_order_count=2,
        refunded_units=3,
        item_refund_amount="30.00",
        tax_refund_amount="2.00",
        shipping_refund_amount="5.00",
    )
    repository = FakeSkuRefundRepository(weekly=[row])
    service = SkuRefundService(repository)

    result = service.list_weekly_refunds(
        channel_account_id="amazon-us",
        start_date=date(2026, 7, 13),
        end_date=date(2026, 7, 19),
        limit=50,
    )

    assert result == [row]
    assert repository.calls[0][0] == "weekly"
    assert repository.calls[0][1]["channel_account_id"] == "amazon-us"


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
    repository = FakeSkuRefundRepository()
    service = SkuRefundService(repository)

    with pytest.raises(ValueError, match=message):
        service.list_daily_refunds(
            channel_account_id="shopify-1",
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )

    assert repository.calls == []


def test_service_rejects_blank_channel_account() -> None:
    repository = FakeSkuRefundRepository()
    service = SkuRefundService(repository)

    with pytest.raises(ValueError, match="channel_account_id"):
        service.list_daily_refunds(
            channel_account_id=" ",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )

    assert repository.calls == []


def test_service_rejects_rows_from_another_channel() -> None:
    repository = FakeSkuRefundRepository(
        daily=[
            SkuDailyRefunds(
                refund_date=date(2026, 7, 20),
                sku_id="sku-1",
                channel_account_id="amazon-us",
                refund_count=1,
                refunded_order_count=1,
                refunded_units=1,
                item_refund_amount="10.00",
                tax_refund_amount="0.80",
                shipping_refund_amount="0",
            )
        ]
    )
    service = SkuRefundService(repository)

    with pytest.raises(ValueError, match="another channel"):
        service.list_daily_refunds(
            channel_account_id="shopify-us",
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
        )
