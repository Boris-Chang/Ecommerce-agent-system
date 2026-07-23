from datetime import date
from decimal import Decimal

import pytest

from infrastructure.database.repositories.inventory.cover import (
    PostgresInventoryRepository,
)
from infrastructure.database.repositories.sku.sales import (
    PostgresSalesAnalyticsRepository,
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
        self.statement = None
        self.params = None

    def execute(self, statement, params: dict) -> FakeResult:
        self.statement = str(statement)
        self.params = params
        return FakeResult(self.rows)


def test_sales_repository_uses_parameters_and_returns_dto() -> None:
    session = FakeSession(
        [
            {
                "sales_date": date(2026, 7, 20),
                "sku_id": "sku-1",
                "channel_account_id": "shopify-1",
                "orders_count": 2,
                "units_sold": 3,
                "gross_sales": Decimal("60.00"),
                "discount_amount": Decimal("5.00"),
                "net_sales": Decimal("55.00"),
                "currency_code": "USD",
                "data_origin": "approved_fixture",
            }
        ]
    )
    repository = PostgresSalesAnalyticsRepository(session)

    rows = repository.list_sku_daily_sales(
        channel_account_id="shopify-1",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        limit=25,
    )

    assert rows[0].sku_id == "sku-1"
    assert rows[0].net_sales == Decimal("55.00")
    assert session.params["limit"] == 25
    assert session.params["channel_account_id"] == "shopify-1"
    assert "channel_account_id = :channel_account_id" in session.statement
    assert ":start_date" in session.statement


def test_sales_repository_aggregates_weekly_units_by_sku() -> None:
    session = FakeSession(
        [
            {
                "week_start": date(2026, 7, 13),
                "sku_id": "sku-1",
                "channel_account_id": "amazon-us",
                "orders_count": 8,
                "units_sold": 12,
                "gross_sales": Decimal("260.00"),
                "discount_amount": Decimal("20.00"),
                "net_sales": Decimal("240.00"),
                "currency_code": "USD",
            }
        ]
    )
    repository = PostgresSalesAnalyticsRepository(session)

    rows = repository.list_sku_weekly_sales(
        channel_account_id="amazon-us",
        start_date=date(2026, 7, 13),
        end_date=date(2026, 7, 19),
        limit=50,
    )

    assert rows[0].week_start == date(2026, 7, 13)
    assert rows[0].sku_id == "sku-1"
    assert rows[0].channel_account_id == "amazon-us"
    assert rows[0].orders_count == 8
    assert rows[0].units_sold == 12
    assert rows[0].gross_sales == Decimal("260.00")
    assert rows[0].discount_amount == Decimal("20.00")
    assert rows[0].net_sales == Decimal("240.00")
    assert "DATE_TRUNC('week', sales_date)" in session.statement
    assert "SUM(COALESCE(units_sold, 0))" in session.statement
    assert "SUM(COALESCE(gross_sales, 0))" in session.statement
    assert "SUM(COALESCE(discount_amount, 0))" in session.statement
    assert (
        "GROUP BY week_start, sku_id, channel_account_id, currency_code"
        in session.statement
    )
    assert session.params["channel_account_id"] == "amazon-us"
    assert session.params["limit"] == 50


def test_inventory_repository_returns_current_balance_components() -> None:
    session = FakeSession(
        [
            {
                "sku_id": "sku-1",
                "warehouse_id": "warehouse-1",
                "on_hand_qty": 20,
                "reserved_qty": 3,
                "blocked_qty": 2,
                "available_qty": 15,
                "incoming_qty": 8,
                "updated_at": "2026-07-23T10:00:00",
                "data_origin": "approved_fixture",
            }
        ]
    )
    repository = PostgresInventoryRepository(session)

    rows = repository.list_inventory_balances(
        sku_id="sku-1",
        warehouse_id="warehouse-1",
        limit=25,
    )

    assert rows[0].on_hand_qty == 20
    assert rows[0].reserved_qty == 3
    assert rows[0].blocked_qty == 2
    assert rows[0].available_qty == 15
    assert rows[0].incoming_qty == 8
    assert "FROM inventory.inventory_balances" in session.statement
    assert session.params == {
        "sku_id": "sku-1",
        "warehouse_id": "warehouse-1",
        "limit": 25,
    }


def test_repository_rejects_invalid_range_and_limit() -> None:
    session = FakeSession([])
    sales = PostgresSalesAnalyticsRepository(session)
    inventory = PostgresInventoryRepository(session)

    with pytest.raises(ValueError, match="start date"):
        sales.list_sku_daily_sales(
            channel_account_id="shopify-1",
            start_date=date(2026, 8, 1),
            end_date=date(2026, 7, 1),
        )

    with pytest.raises(ValueError, match="limit"):
        inventory.list_inventory_cover(limit=10_001)


def test_inventory_cover_query_casts_optional_status_parameter() -> None:
    session = FakeSession([])
    repository = PostgresInventoryRepository(session)

    repository.list_inventory_cover(stock_status="replenish", limit=25)

    assert "CAST(:stock_status AS text)" in session.statement
    assert session.params == {"stock_status": "replenish", "limit": 25}
