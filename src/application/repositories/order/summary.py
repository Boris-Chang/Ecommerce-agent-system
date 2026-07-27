from datetime import date
from typing import Protocol


class OrderSummaryRepository(Protocol):
    def count_orders(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        currency_code: str,
    ) -> int: ...
