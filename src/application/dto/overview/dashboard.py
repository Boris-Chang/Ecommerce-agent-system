from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from application.dto.common import ReadModel


class OverviewFilters(ReadModel):
    channel_account_id: str
    day: date
    week_start: date
    week_end: date
    trend_start: date
    trend_end: date
    currency_code: str


class OverviewKpis(ReadModel):
    net_sales: Decimal
    units_sold: int = Field(ge=0)
    orders_count: int = Field(ge=0)
    average_order_value: Decimal = Field(ge=0)
    unit_refund_rate_pct: Decimal = Field(ge=0)


class OverviewTrendPoint(ReadModel):
    sales_date: date
    channel_account_id: str
    net_sales: Decimal


class OverviewChannelContribution(ReadModel):
    channel_account_id: str
    units_sold: int = Field(ge=0)
    net_sales: Decimal
    units_share_pct: Decimal = Field(ge=0, le=100)
    net_sales_share_pct: Decimal = Field(ge=0, le=100)
    gross_profit_share_pct: Decimal = Field(ge=0, le=100)


class OverviewSkuPerformance(ReadModel):
    sku_id: str
    units_sold: int = Field(ge=0)
    net_sales: Decimal
    unit_refund_rate_pct: Decimal = Field(ge=0)
    inventory_cover_days: int | None = None
    forecast_4w_p50: Decimal = Field(ge=0)


class OverviewInsight(ReadModel):
    category: str
    severity: Literal["high", "medium", "low", "info"]
    title: str
    detail: str
    href: str


class OverviewSupplementRequest(ReadModel):
    channel_account_id: str
    day: date
    week_start: date
    week_end: date
    top_sku_units: tuple[tuple[str, int], ...]
    replenishment_skus: tuple[str, ...]
    overstock_skus: tuple[str, ...]


class OverviewSupplement(ReadModel):
    gross_profit_share_pct: dict[str, Decimal]
    forecast_4w_p50: dict[str, Decimal]
    insights: tuple[OverviewInsight, ...]
    data_source: str


class OverviewDashboard(ReadModel):
    filters: OverviewFilters
    generated_at: datetime
    daily_kpis: OverviewKpis
    weekly_kpis: OverviewKpis
    trend: tuple[OverviewTrendPoint, ...]
    channel_contributions: tuple[OverviewChannelContribution, ...]
    sku_performance: tuple[OverviewSkuPerformance, ...]
    insights: tuple[OverviewInsight, ...]
    data_sources: tuple[str, ...]
