from datetime import date
from decimal import Decimal

from application.dto.common import ReadModel


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
