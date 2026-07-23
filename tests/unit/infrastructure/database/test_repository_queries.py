from datetime import date
from decimal import Decimal

import pytest

from infrastructure.database.repositories.analytics import (
    PostgresInventoryRepository,
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
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        limit=25,
    )

    assert rows[0].sku_id == "sku-1"
    assert rows[0].net_sales == Decimal("55.00")
    assert session.params["limit"] == 25
    assert ":start_date" in session.statement


def test_repository_rejects_invalid_range_and_limit() -> None:
    session = FakeSession([])
    sales = PostgresSalesAnalyticsRepository(session)
    inventory = PostgresInventoryRepository(session)

    with pytest.raises(ValueError, match="start date"):
        sales.list_sku_daily_sales(
            start_date=date(2026, 8, 1),
            end_date=date(2026, 7, 1),
        )

    with pytest.raises(ValueError, match="limit"):
        inventory.list_inventory_cover(limit=10_001)
