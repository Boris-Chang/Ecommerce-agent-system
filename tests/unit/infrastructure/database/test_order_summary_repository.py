from datetime import date

from infrastructure.database.repositories.order import (
    PostgresOrderSummaryRepository,
)


class FakeResult:
    def __init__(self, value: int) -> None:
        self.value = value

    def scalar_one(self) -> int:
        return self.value


class FakeSession:
    def __init__(self, value: int) -> None:
        self.value = value
        self.statement = ""
        self.params: dict = {}

    def execute(self, statement, params: dict) -> FakeResult:
        self.statement = str(statement)
        self.params = params
        return FakeResult(self.value)


def test_order_summary_repository_counts_business_dates_and_excludes_cancelled() -> None:
    session = FakeSession(8)
    repository = PostgresOrderSummaryRepository(session)

    result = repository.count_orders(
        channel_account_id="CA_SHOPIFY_US",
        start_date=date(2026, 7, 27),
        end_date=date(2026, 7, 27),
        currency_code="USD",
    )

    assert result == 8
    assert "FROM sales.orders" in session.statement
    assert "AT TIME ZONE 'Asia/Shanghai'" in session.statement
    assert "order_status <> 'cancelled'" in session.statement
    assert session.params == {
        "channel_account_id": "CA_SHOPIFY_US",
        "start_date": date(2026, 7, 27),
        "end_date": date(2026, 7, 27),
        "currency_code": "USD",
    }
