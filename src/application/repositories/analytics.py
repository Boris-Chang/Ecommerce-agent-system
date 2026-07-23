from datetime import date
from typing import Protocol, Sequence

from application.dto.analytics import (
    ChannelProfitMonthly,
    CustomerLifetimeValue,
    InventoryCover,
    SkuDailySales,
    SkuProfitMonthly,
)


class SalesAnalyticsRepository(Protocol):
    def list_sku_daily_sales(
        self,
        *,
        start_date: date,
        end_date: date,
        limit: int = 1_000,
    ) -> Sequence[SkuDailySales]: ...


class InventoryRepository(Protocol):
    def list_inventory_cover(
        self,
        *,
        stock_status: str | None = None,
        limit: int = 1_000,
    ) -> Sequence[InventoryCover]: ...


class CustomerRepository(Protocol):
    def list_customer_lifetime_value(
        self,
        *,
        ltv_segment: str | None = None,
        repeat_customer: bool | None = None,
        limit: int = 1_000,
    ) -> Sequence[CustomerLifetimeValue]: ...


class ProfitRepository(Protocol):
    def list_sku_profit_monthly(
        self,
        *,
        start_month: date,
        end_month: date,
        limit: int = 1_000,
    ) -> Sequence[SkuProfitMonthly]: ...

    def list_channel_profit_monthly(
        self,
        *,
        start_month: date,
        end_month: date,
        limit: int = 1_000,
    ) -> Sequence[ChannelProfitMonthly]: ...
