from datetime import datetime

from application.dto.common import ReadModel


class InventoryBalance(ReadModel):
    sku_id: str
    warehouse_id: str
    on_hand_qty: int
    reserved_qty: int
    blocked_qty: int
    available_qty: int
    incoming_qty: int
    updated_at: datetime
    data_origin: str | None = None
