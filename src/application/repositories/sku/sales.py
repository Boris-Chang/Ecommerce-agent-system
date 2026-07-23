from datetime import date
from typing import Protocol, Sequence

from application.dto.sku import SkuDailySales, SkuWeeklySales


class SalesAnalyticsRepository(Protocol):
    def list_sku_daily_sales(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 1_000,
    ) -> Sequence[SkuDailySales]: ...

    def list_sku_weekly_sales(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10_000,
    ) -> Sequence[SkuWeeklySales]: ...
