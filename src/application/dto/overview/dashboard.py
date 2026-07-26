from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from application.dto.common import ReadModel


class OverviewFilters(ReadModel):
    channel_account_ids: tuple[str, ...]
    start_date: date
    end_date: date
    currency_code: str
    comparison: Literal["previous_period"] = "previous_period"


class OverviewKpis(ReadModel):
    net_sales: Decimal
    net_sales_change_pct: Decimal | None = None
    units_sold: int = Field(ge=0)
    units_change_pct: Decimal | None = None
    orders_count: int = Field(ge=0)
    orders_change_pct: Decimal | None = None
    average_order_value: Decimal = Field(ge=0)
    average_order_value_change_pct: Decimal | None = None
    unit_refund_rate_pct: Decimal = Field(ge=0)
    unit_refund_rate_change_points: Decimal | None = None
    stockout_risk_skus: int = Field(ge=0)


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
    sales_change_pct: Decimal | None = None
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
    channel_account_ids: tuple[str, ...]
    start_date: date
    end_date: date
    current_net_sales: Decimal
    previous_net_sales: Decimal
    top_sku_units: tuple[tuple[str, int], ...]
    replenishment_skus: tuple[str, ...]
    overstock_skus: tuple[str, ...]


class OverviewSupplement(ReadModel):
    orders_count: int = Field(ge=0)
    previous_orders_count: int = Field(ge=0)
    gross_profit_share_pct: dict[str, Decimal]
    forecast_4w_p50: dict[str, Decimal]
    insights: tuple[OverviewInsight, ...]
    data_source: str


class OverviewDashboard(ReadModel):
    filters: OverviewFilters
    generated_at: datetime
    kpis: OverviewKpis
    trend: tuple[OverviewTrendPoint, ...]
    channel_contributions: tuple[OverviewChannelContribution, ...]
    sku_performance: tuple[OverviewSkuPerformance, ...]
    insights: tuple[OverviewInsight, ...]
    data_sources: tuple[str, ...]
