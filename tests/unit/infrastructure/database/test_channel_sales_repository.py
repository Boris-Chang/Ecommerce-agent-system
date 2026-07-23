from datetime import date
from decimal import Decimal

from infrastructure.database.repositories.channel_sales import (
    PostgresChannelSalesRepository,
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


def test_channel_sales_repository_aggregates_snapshot_by_channel_and_currency() -> None:
    session = FakeSession(
        [
            {
                "channel_account_id": "shopify-us",
                "units_sold": 100,
                "gross_sales": Decimal("1200"),
                "discount_amount": Decimal("100"),
                "net_sales": Decimal("1100"),
                "currency_code": "USD",
            }
        ]
    )
    repository = PostgresChannelSalesRepository(session)

    rows = repository.list_channel_sales_totals(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )

    assert rows[0].net_sales == Decimal("1100")
    assert "FROM analytics.v_sku_daily_sales" in session.statement
    assert "GROUP BY channel_account_id, currency_code" in session.statement
    assert "LIMIT" not in session.statement
    assert session.params == {
        "start_date": date(2026, 7, 1),
        "end_date": date(2026, 7, 31),
    }
