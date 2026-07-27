from datetime import date

from application.repositories.order import OrderSummaryRepository


class OrderSummaryService:
    """Count non-cancelled orders within one channel and currency."""

    def __init__(self, repository: OrderSummaryRepository) -> None:
        self._repository = repository

    def count_orders(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        currency_code: str = "USD",
    ) -> int:
        channel = channel_account_id.strip()
        currency = currency_code.strip().upper()
        if not channel:
            raise ValueError("channel_account_id must not be blank.")
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date.")
        if not currency:
            raise ValueError("currency_code must not be blank.")
        value = self._repository.count_orders(
            channel_account_id=channel,
            start_date=start_date,
            end_date=end_date,
            currency_code=currency,
        )
        if value < 0:
            raise ValueError("repository returned a negative order count.")
        return value
