from decimal import Decimal

from pydantic import Field

from application.dto.common import ReadModel


class ChannelSalesTotals(ReadModel):
    """Channel sales totals in one currency for a requested date range."""

    channel_account_id: str
    units_sold: int = Field(ge=0)
    gross_sales: Decimal = Field(ge=0)
    discount_amount: Decimal = Field(ge=0)
    net_sales: Decimal = Field(ge=0)
    currency_code: str


class ChannelSalesShare(ChannelSalesTotals):
    """Channel contribution within channels that use the same currency."""

    units_share_pct: Decimal = Field(ge=0, le=100)
    net_sales_share_pct: Decimal = Field(ge=0, le=100)
