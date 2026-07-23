from datetime import datetime
from decimal import Decimal

from application.dto.common import ReadModel


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
