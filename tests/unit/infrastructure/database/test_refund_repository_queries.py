from datetime import date
from decimal import Decimal

from infrastructure.database.repositories.sku.refunds import (
    PostgresSkuRefundRepository,
)


class FakeMappings:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def all(self) -> list[dict]:
        return self._rows


class FakeResult:
    def __init__(self, rows: list[dict]) -> None:
        self._rows = rows

    def mappings(self) -> FakeMappings:
        return FakeMappings(self._rows)


class FakeSession:
    def __init__(self, rows: list[dict]) -> None:
        self.rows = rows
        self.statement = ""
        self.params: dict = {}

    def execute(self, statement, params: dict) -> FakeResult:
        self.statement = str(statement)
        self.params = params
        return FakeResult(self.rows)


def _refund_row(period_field: str, period: date) -> dict:
    return {
        period_field: period,
        "sku_id": "sku-1",
        "channel_account_id": "shopify-1",
        "refund_reason": "damaged",
        "refund_status": "completed",
        "refund_count": 2,
        "refunded_order_count": 1,
        "refunded_units": 3,
        "item_refund_amount": Decimal("27.00"),
        "tax_refund_amount": Decimal("2.00"),
        "shipping_refund_amount": Decimal("4.00"),
        "currency_code": "USD",
    }


def test_daily_refund_repository_joins_line_level_sku_facts() -> None:
    session = FakeSession([_refund_row("refund_date", date(2026, 7, 20))])
    repository = PostgresSkuRefundRepository(session)

    rows = repository.list_sku_daily_refunds(
        channel_account_id="shopify-1",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        limit=25,
    )

    assert rows[0].refund_date == date(2026, 7, 20)
    assert rows[0].refunded_units == 3
    assert rows[0].item_refund_amount == Decimal("27.00")
    assert "JOIN sales.refund_lines" in session.statement
    assert "JOIN sales.order_lines" in session.statement
    assert "JOIN sales.orders" in session.statement
    assert "SUM(refund_lines.refund_amount)" in session.statement
    assert "refunds.refund_amount" not in session.statement
    assert session.params["channel_account_id"] == "shopify-1"
    assert session.params["limit"] == 25


def test_weekly_refund_repository_preserves_channel_and_reason_dimensions() -> None:
    session = FakeSession([_refund_row("week_start", date(2026, 7, 13))])
    repository = PostgresSkuRefundRepository(session)

    rows = repository.list_sku_weekly_refunds(
        channel_account_id="shopify-1",
        start_date=date(2026, 7, 13),
        end_date=date(2026, 7, 19),
        limit=50,
    )

    assert rows[0].week_start == date(2026, 7, 13)
    assert rows[0].channel_account_id == "shopify-1"
    assert rows[0].refund_reason == "damaged"
    assert "DATE_TRUNC('week', refunds.refunded_at)" in session.statement
    assert "orders.channel_account_id = :channel_account_id" in session.statement
    assert "refunds.refund_reason" in session.statement
    assert session.params["limit"] == 50
