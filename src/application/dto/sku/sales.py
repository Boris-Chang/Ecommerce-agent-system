from datetime import date
from decimal import Decimal

from pydantic import Field

from application.dto.common import ReadModel


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


class SkuWeeklySales(ReadModel):
    week_start: date
    sku_id: str
    channel_account_id: str
    orders_count: int | None = Field(default=None, ge=0)
    units_sold: int = Field(ge=0)
    gross_sales: Decimal | None = None
    discount_amount: Decimal | None = None
    net_sales: Decimal | None = None
    currency_code: str | None = None
