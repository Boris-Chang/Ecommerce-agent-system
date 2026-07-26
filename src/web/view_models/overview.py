from dataclasses import dataclass


@dataclass(frozen=True)
class OverviewFilterViewModel:
    channel_account_ids: tuple[str, ...]
    available_channel_account_ids: tuple[str, ...]
    start_date: str
    end_date: str
    currency_code: str


@dataclass(frozen=True)
class OverviewKpiViewModel:
    label: str
    value: str
    change: str
    change_tone: str
    meta: str
    accent: str


@dataclass(frozen=True)
class OverviewChannelViewModel:
    channel_account_id: str
    net_sales: str
    net_sales_share_pct: str
    units_share_pct: str
    gross_profit_share_pct: str
    bar_width: str


@dataclass(frozen=True)
class OverviewSkuRowViewModel:
    sku_id: str
    units_sold: str
    net_sales: str
    sales_change: str
    sales_change_tone: str
    unit_refund_rate: str
    refund_tone: str
    inventory_cover_days: str
    inventory_tone: str
    forecast_4w_p50: str


@dataclass(frozen=True)
class OverviewInsightViewModel:
    category: str
    severity_label: str
    severity: str
    title: str
    detail: str
    href: str


@dataclass(frozen=True)
class OverviewPageViewModel:
    filters: OverviewFilterViewModel
    generated_at: str
    kpis: tuple[OverviewKpiViewModel, ...]
    sales_chart_options: dict[str, object]
    channels: tuple[OverviewChannelViewModel, ...]
    sku_rows: tuple[OverviewSkuRowViewModel, ...]
    insights: tuple[OverviewInsightViewModel, ...]
    empty: bool
