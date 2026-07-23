from datetime import date
from decimal import Decimal

from pydantic import Field

from application.dto.common import ReadModel


class SkuRefundMetrics(ReadModel):
    sku_id: str
    channel_account_id: str
    refund_reason: str | None = None
    refund_status: str | None = None
    refund_count: int = Field(ge=0)
    refunded_order_count: int = Field(ge=0)
    refunded_units: int = Field(ge=0)
    item_refund_amount: Decimal = Field(ge=0)
    tax_refund_amount: Decimal = Field(ge=0)
    shipping_refund_amount: Decimal = Field(ge=0)
    currency_code: str | None = None


class SkuDailyRefunds(SkuRefundMetrics):
    refund_date: date


class SkuWeeklyRefunds(SkuRefundMetrics):
    week_start: date
