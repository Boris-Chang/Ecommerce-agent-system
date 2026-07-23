from datetime import date
from decimal import Decimal

import pytest

from application.dto.channel import ChannelSalesTotals
from application.services import ChannelSalesShareService


class FakeChannelSalesRepository:
    def __init__(self, rows: list[ChannelSalesTotals]) -> None:
        self.rows = rows
        self.calls: list[dict] = []

    def list_channel_sales_totals(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[ChannelSalesTotals]:
        self.calls.append({"start_date": start_date, "end_date": end_date})
        return self.rows


def _totals(
    channel: str,
    *,
    currency: str,
    units: int,
    net_sales: str,
) -> ChannelSalesTotals:
    amount = Decimal(net_sales)
    return ChannelSalesTotals(
        channel_account_id=channel,
        units_sold=units,
        gross_sales=amount,
        discount_amount=Decimal("0"),
        net_sales=amount,
        currency_code=currency,
    )


def test_sales_shares_are_calculated_within_each_currency() -> None:
    repository = FakeChannelSalesRepository(
        [
            _totals("shopify-us", currency="USD", units=75, net_sales="600"),
            _totals("amazon-us", currency="USD", units=25, net_sales="400"),
            _totals("shopify-eu", currency="EUR", units=10, net_sales="200"),
        ]
    )
    service = ChannelSalesShareService(repository)

    result = service.list_sales_shares(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )

    assert result[0].units_share_pct == Decimal("75.0000")
    assert result[0].net_sales_share_pct == Decimal("60.0000")
    assert result[1].units_share_pct == Decimal("25.0000")
    assert result[1].net_sales_share_pct == Decimal("40.0000")
    assert result[2].units_share_pct == Decimal("100.0000")
    assert result[2].net_sales_share_pct == Decimal("100.0000")
    assert repository.calls == [
        {
            "start_date": date(2026, 7, 1),
            "end_date": date(2026, 7, 31),
        }
    ]


def test_zero_totals_produce_zero_share() -> None:
    repository = FakeChannelSalesRepository(
        [_totals("shopify-us", currency="USD", units=0, net_sales="0")]
    )

    result = ChannelSalesShareService(repository).list_sales_shares(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )

    assert result[0].units_share_pct == 0
    assert result[0].net_sales_share_pct == 0


def test_sales_share_rejects_invalid_date_range() -> None:
    repository = FakeChannelSalesRepository([])
    service = ChannelSalesShareService(repository)

    with pytest.raises(ValueError, match="start_date"):
        service.list_sales_shares(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 7, 31),
        )

    assert repository.calls == []
