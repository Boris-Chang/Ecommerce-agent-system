from datetime import date

from sqlalchemy import text
from sqlalchemy.orm import Session


class PostgresOrderSummaryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def count_orders(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        currency_code: str,
    ) -> int:
        value = self._session.execute(
            text(
                """
                SELECT COUNT(*)
                FROM sales.orders
                WHERE channel_account_id = :channel_account_id
                  AND (ordered_at AT TIME ZONE 'Asia/Shanghai')::date
                      BETWEEN CAST(:start_date AS date)
                          AND CAST(:end_date AS date)
                  AND order_currency = :currency_code
                  AND order_status <> 'cancelled'
                """
            ),
            {
                "channel_account_id": channel_account_id,
                "start_date": start_date,
                "end_date": end_date,
                "currency_code": currency_code,
            },
        ).scalar_one()
        return int(value)
