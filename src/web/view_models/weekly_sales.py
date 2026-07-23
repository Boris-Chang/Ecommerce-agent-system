from dataclasses import dataclass


@dataclass(frozen=True)
class WeeklySalesTableRowViewModel:
    week_start: str
    sku_id: str
    orders_count: int
    units_sold: int
    gross_sales: str
    discount_amount: str
    net_sales: str
    currency_code: str


@dataclass(frozen=True)
class WeeklySalesPageViewModel:
    channel_account_id: str
    start_date: str
    end_date: str
    generated_at: str
    data_as_of: str
    row_count: int
    currency_codes: tuple[str, ...]
    has_multiple_currencies: bool
    empty: bool
    chart_options: dict[str, object]
    rows: tuple[WeeklySalesTableRowViewModel, ...]
