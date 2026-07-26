from dataclasses import dataclass


@dataclass(frozen=True)
class SkuDashboardFilterViewModel:
    channel_account_id: str
    channel_account_ids: tuple[str, ...]
    start_date: str
    end_date: str
    currency_code: str
    grain: str
    search: str


@dataclass(frozen=True)
class SkuDashboardKpiViewModel:
    label: str
    value: str
    meta: str
    accent: str


@dataclass(frozen=True)
class SkuRefundReasonViewModel:
    reason: str
    share_pct: str
    bar_width: str


@dataclass(frozen=True)
class SkuDashboardRowViewModel:
    sku_id: str
    collapse_id: str
    units_sold: str
    net_sales: str
    sales_change: str
    sales_change_tone: str
    unit_refund_rate: str
    refund_tone: str
    primary_refund_reason: str
    inventory_cover_days: str
    inventory_tone: str
    detail_chart_options: dict[str, object]
    refund_reasons: tuple[SkuRefundReasonViewModel, ...]


@dataclass(frozen=True)
class SkuDashboardPageViewModel:
    filters: SkuDashboardFilterViewModel
    generated_at: str
    grain_label: str
    kpis: tuple[SkuDashboardKpiViewModel, ...]
    trend_chart_options: dict[str, object]
    rows: tuple[SkuDashboardRowViewModel, ...]
    empty: bool
