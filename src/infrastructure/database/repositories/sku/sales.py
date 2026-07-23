from datetime import date

from sqlalchemy.orm import Session

from application.dto.sku import SkuDailySales, SkuWeeklySales
from infrastructure.database.repositories._common import (
    to_models,
    validate_channel_account_id,
    validate_date_range,
    validate_limit,
)


class PostgresSalesAnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_sku_daily_sales(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 1_000,
    ) -> list[SkuDailySales]:
        validate_date_range(start_date, end_date)
        return to_models(
            self._session,
            """
            SELECT *
            FROM analytics.v_sku_daily_sales
            WHERE channel_account_id = :channel_account_id
              AND sales_date BETWEEN :start_date AND :end_date
            ORDER BY sales_date DESC, sku_id, channel_account_id
            LIMIT :limit
            """,
            {
                "channel_account_id": validate_channel_account_id(
                    channel_account_id
                ),
                "start_date": start_date,
                "end_date": end_date,
                "limit": validate_limit(limit),
            },
            SkuDailySales,
        )

    def list_sku_weekly_sales(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10_000,
    ) -> list[SkuWeeklySales]:
        validate_date_range(start_date, end_date)
        return to_models(
            self._session,
            """
            SELECT
                DATE_TRUNC('week', sales_date)::date AS week_start,
                sku_id,
                channel_account_id,
                SUM(COALESCE(orders_count, 0))::integer AS orders_count,
                SUM(COALESCE(units_sold, 0))::integer AS units_sold,
                SUM(COALESCE(gross_sales, 0)) AS gross_sales,
                SUM(COALESCE(discount_amount, 0)) AS discount_amount,
                SUM(COALESCE(net_sales, 0)) AS net_sales,
                currency_code
            FROM analytics.v_sku_daily_sales
            WHERE channel_account_id = :channel_account_id
              AND sales_date BETWEEN :start_date AND :end_date
            GROUP BY week_start, sku_id, channel_account_id, currency_code
            ORDER BY sku_id, week_start, currency_code
            LIMIT :limit
            """,
            {
                "channel_account_id": validate_channel_account_id(
                    channel_account_id
                ),
                "start_date": start_date,
                "end_date": end_date,
                "limit": validate_limit(limit),
            },
            SkuWeeklySales,
        )
