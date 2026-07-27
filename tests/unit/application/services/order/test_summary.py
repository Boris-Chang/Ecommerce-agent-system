from datetime import date

import pytest

from application.services.order import OrderSummaryService


class FakeOrderSummaryRepository:
    def __init__(self, count: int) -> None:
        self.count = count
        self.calls: list[dict] = []

    def count_orders(self, **kwargs) -> int:
        self.calls.append(kwargs)
        return self.count


def test_count_orders_normalizes_filters_and_returns_repository_value() -> None:
    repository = FakeOrderSummaryRepository(8)
    service = OrderSummaryService(repository)

    result = service.count_orders(
        channel_account_id=" CA_SHOPIFY_US ",
        start_date=date(2026, 7, 27),
        end_date=date(2026, 7, 27),
        currency_code=" usd ",
    )

    assert result == 8
    assert repository.calls == [
        {
            "channel_account_id": "CA_SHOPIFY_US",
            "start_date": date(2026, 7, 27),
            "end_date": date(2026, 7, 27),
            "currency_code": "USD",
        }
    ]


def test_count_orders_rejects_invalid_inputs_before_querying() -> None:
    repository = FakeOrderSummaryRepository(0)
    service = OrderSummaryService(repository)

    with pytest.raises(ValueError, match="start_date"):
        service.count_orders(
            channel_account_id="CA_SHOPIFY_US",
            start_date=date(2026, 7, 28),
            end_date=date(2026, 7, 27),
        )

    assert repository.calls == []


def test_count_orders_rejects_negative_repository_value() -> None:
    service = OrderSummaryService(FakeOrderSummaryRepository(-1))

    with pytest.raises(ValueError, match="negative"):
        service.count_orders(
            channel_account_id="CA_SHOPIFY_US",
            start_date=date(2026, 7, 27),
            end_date=date(2026, 7, 27),
        )
