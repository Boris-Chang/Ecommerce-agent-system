from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ReadModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class SkuDailySales(ReadModel):
    sales_date: date
    sku_id: str
    channel_account_id: str
    orders_count: int | None = None
    units_sold: int | None = None
    gross_sales: Decimal | None = None
    discount_amount: Decimal | None = None
    net_sales: Decimal | None = None
    currency_code: str | None = None
    data_origin: str | None = None


class InventoryCover(ReadModel):
    sku_id: str
    warehouse_id: str
    available_qty: int | None = None
    incoming_qty: int | None = None
    forecast_4w_units: Decimal | None = None
    forecast_daily_units: Decimal | None = None
    inventory_cover_days: int | None = None
    stock_status: str | None = None
    snapshot_at: datetime | None = None
    data_origin: str | None = None


class CustomerLifetimeValue(ReadModel):
    customer_id: str
    first_order_at: datetime | None = None
    last_order_at: datetime | None = None
    order_count: int | None = None
    net_revenue: Decimal | None = None
    estimated_contribution_profit: Decimal | None = None
    avg_order_value: Decimal | None = None
    repeat_customer: bool | None = None
    ltv_segment: str | None = None
    currency_code: str | None = None
    data_origin: str | None = None


class SkuProfitMonthly(ReadModel):
    month: date
    sku_id: str
    channel_account_id: str
    units_sold: int | None = None
    gross_revenue: Decimal | None = None
    refund_amount: Decimal | None = None
    net_revenue: Decimal | None = None
    product_and_landed_cost: Decimal | None = None
    fulfillment_cost: Decimal | None = None
    platform_and_payment_fees: Decimal | None = None
    ad_cost_allocated: Decimal | None = None
    contribution_profit: Decimal | None = None
    currency_code: str | None = None
    data_origin: str | None = None


class ChannelProfitMonthly(ReadModel):
    month: date
    channel_account_id: str
    units_sold: int | None = None
    gross_revenue: Decimal | None = None
    refund_amount: Decimal | None = None
    net_revenue: Decimal | None = None
    product_and_landed_cost: Decimal | None = None
    fulfillment_cost: Decimal | None = None
    platform_and_payment_fees: Decimal | None = None
    ad_cost_allocated: Decimal | None = None
    contribution_profit: Decimal | None = None
    currency_code: str | None = None
    data_origin: str | None = None
