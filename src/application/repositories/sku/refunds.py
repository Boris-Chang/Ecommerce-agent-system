from datetime import date
from typing import Protocol, Sequence

from application.dto.sku import SkuDailyRefunds, SkuWeeklyRefunds


class SkuRefundRepository(Protocol):
    def list_sku_daily_refunds(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 1_000,
    ) -> Sequence[SkuDailyRefunds]: ...

    def list_sku_weekly_refunds(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10_000,
    ) -> Sequence[SkuWeeklyRefunds]: ...
