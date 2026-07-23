from datetime import date

from application.dto.sku import SkuDailyRefunds, SkuWeeklyRefunds
from application.repositories.sku import SkuRefundRepository
from application.services.sku._validation import (
    validate_channel_account_id,
    validate_query,
)


class SkuRefundService:
    """Expose channel-scoped daily and weekly SKU refund facts."""

    def __init__(self, repository: SkuRefundRepository) -> None:
        self._repository = repository

    def list_daily_refunds(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 1_000,
    ) -> list[SkuDailyRefunds]:
        validate_query(start_date, end_date, limit)
        resolved_channel = validate_channel_account_id(channel_account_id)
        rows = list(
            self._repository.list_sku_daily_refunds(
                channel_account_id=resolved_channel,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        )
        _assert_channel_scope(rows, resolved_channel)
        return rows

    def list_weekly_refunds(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10_000,
    ) -> list[SkuWeeklyRefunds]:
        """Return calendar-week refunds; boundary weeks may be partial."""
        validate_query(start_date, end_date, limit)
        resolved_channel = validate_channel_account_id(channel_account_id)
        rows = list(
            self._repository.list_sku_weekly_refunds(
                channel_account_id=resolved_channel,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
        )
        _assert_channel_scope(rows, resolved_channel)
        return rows


def _assert_channel_scope(
    rows: list[SkuDailyRefunds] | list[SkuWeeklyRefunds],
    channel_account_id: str,
) -> None:
    if any(row.channel_account_id != channel_account_id for row in rows):
        raise ValueError("repository returned refunds from another channel account.")
