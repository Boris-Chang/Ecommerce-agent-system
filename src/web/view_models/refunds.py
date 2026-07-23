from dataclasses import dataclass


@dataclass(frozen=True)
class RefundTableRowViewModel:
    period_start: str
    sku_id: str
    refund_reason: str
    refund_status: str
    refund_count: int
    refunded_order_count: int
    refunded_units: int
    item_refund_amount: str
    tax_refund_amount: str
    shipping_refund_amount: str
    currency_code: str


@dataclass(frozen=True)
class RefundsPageViewModel:
    channel_account_id: str
    start_date: str
    end_date: str
    generated_at: str
    data_as_of: str
    daily_row_count: int
    weekly_row_count: int
    currency_codes: tuple[str, ...]
    has_multiple_currencies: bool
    empty: bool
    chart_options: dict[str, object]
    daily_rows: tuple[RefundTableRowViewModel, ...]
    weekly_rows: tuple[RefundTableRowViewModel, ...]
