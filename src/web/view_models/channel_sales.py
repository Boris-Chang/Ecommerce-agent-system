from dataclasses import dataclass


@dataclass(frozen=True)
class ChannelSalesShareRowViewModel:
    channel_account_id: str
    units_sold: int
    gross_sales: str
    discount_amount: str
    net_sales: str
    units_share_pct: str
    net_sales_share_pct: str
    currency_code: str


@dataclass(frozen=True)
class ChannelSalesSharePageViewModel:
    start_date: str
    end_date: str
    generated_at: str
    channel_count: int
    row_count: int
    currency_codes: tuple[str, ...]
    has_multiple_currencies: bool
    empty: bool
    chart_options: dict[str, object]
    rows: tuple[ChannelSalesShareRowViewModel, ...]
