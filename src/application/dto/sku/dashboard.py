from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import Field

from application.dto.common import ReadModel


class SkuDashboardFilters(ReadModel):
    channel_account_id: str
    start_date: date
    end_date: date
    currency_code: str
    grain: Literal["daily", "weekly"]
    search: str | None = None


class SkuDashboardKpis(ReadModel):
    active_skus: int = Field(ge=0)
    listed_skus: int = Field(ge=0)
    top_10_concentration_pct: Decimal = Field(ge=0, le=100)
    unit_refund_rate_pct: Decimal = Field(ge=0)
    slow_moving_skus: int = Field(ge=0)


class SkuTrendPoint(ReadModel):
    period_start: date
    sku_id: str
    units_sold: int = Field(ge=0)


class SkuRefundReasonShare(ReadModel):
    reason: str
    refunded_units: int = Field(ge=0)
    share_pct: Decimal = Field(ge=0, le=100)


class SkuDetailPoint(ReadModel):
    sales_date: date
    units_sold: int = Field(ge=0)
    refunded_units: int = Field(ge=0)


class SkuDashboardRow(ReadModel):
    sku_id: str
    units_sold: int = Field(ge=0)
    net_sales: Decimal
    sales_change_pct: Decimal | None = None
    unit_refund_rate_pct: Decimal = Field(ge=0)
    primary_refund_reason: str
    inventory_cover_days: int | None = None
    detail_points: tuple[SkuDetailPoint, ...]
    refund_reasons: tuple[SkuRefundReasonShare, ...]


class SkuDashboardSupplementRequest(ReadModel):
    channel_account_id: str
    start_date: date
    end_date: date
    active_skus: int = Field(ge=0)


class SkuDashboardSupplement(ReadModel):
    listed_skus: int = Field(ge=0)
    slow_moving_skus: int = Field(ge=0)
    data_source: str


class SkuDashboard(ReadModel):
    filters: SkuDashboardFilters
    generated_at: datetime
    kpis: SkuDashboardKpis
    trend: tuple[SkuTrendPoint, ...]
    rows: tuple[SkuDashboardRow, ...]
    data_sources: tuple[str, ...]
