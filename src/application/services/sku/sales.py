from datetime import date

from application.dto.sku import SkuDailySales, SkuWeeklySales
from application.repositories.sku import SalesAnalyticsRepository
from application.services.sku._validation import (
    validate_channel_account_id,
    validate_query,
)


class SkuSalesService:
    """Expose application-level daily and weekly SKU sales queries."""

    def __init__(self, repository: SalesAnalyticsRepository) -> None:
        self._repository = repository

    def list_daily_sales(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 1_000,
    ) -> list[SkuDailySales]:
        validate_query(start_date, end_date, limit)
        resolved_channel = validate_channel_account_id(channel_account_id)
        rows = list(
            self._repository.list_sku_daily_sales(
                channel_account_id=resolved_channel,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        )
        _assert_channel_scope(rows, resolved_channel)
        return rows

    def list_weekly_sales(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10_000,
    ) -> list[SkuWeeklySales]:
        """Return calendar-week sales; boundary weeks may be partial."""
        validate_query(start_date, end_date, limit)
        resolved_channel = validate_channel_account_id(channel_account_id)
        rows = list(
            self._repository.list_sku_weekly_sales(
                channel_account_id=resolved_channel,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        )
        _assert_channel_scope(rows, resolved_channel)
        return rows


def _assert_channel_scope(
    rows: list[SkuDailySales] | list[SkuWeeklySales],
    channel_account_id: str,
) -> None:
    if any(row.channel_account_id != channel_account_id for row in rows):
        raise ValueError("repository returned sales from another channel account.")
