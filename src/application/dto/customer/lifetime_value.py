from datetime import datetime
from decimal import Decimal

from application.dto.common import ReadModel


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
