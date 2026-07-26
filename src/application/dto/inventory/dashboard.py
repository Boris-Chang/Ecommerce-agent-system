from datetime import datetime
from decimal import Decimal

from pydantic import Field

from application.dto.common import ReadModel
from application.dto.inventory.balance import InventoryBalance


class InventoryDecisionInput(ReadModel):
    sku_id: str
    warehouse_id: str
    available_qty: int
    incoming_qty: int
    forecast_4w_units: Decimal | None = None
    inventory_cover_days: int | None = None
    stock_status: str | None = None


class InventoryDashboardSupplementRequest(ReadModel):
    rows: tuple[InventoryDecisionInput, ...]


class InventoryDashboardSupplement(ReadModel):
    available_inventory_value: Decimal = Field(ge=0)
    estimated_stockout_loss: Decimal = Field(ge=0)
    overstock_tied_value: Decimal = Field(ge=0)
    recommended_order_qty: dict[str, int]
    tied_value_by_key: dict[str, Decimal]
    data_source: str


class InventoryDashboardKpis(ReadModel):
    available_inventory_value: Decimal = Field(ge=0)
    inventory_skus: int = Field(ge=0)
    stockout_risk_skus: int = Field(ge=0)
    estimated_stockout_loss: Decimal = Field(ge=0)
    average_cover_days: Decimal = Field(ge=0)
    overstock_skus: int = Field(ge=0)
    overstock_tied_value: Decimal = Field(ge=0)


class InventoryCoverBucket(ReadModel):
    bucket_id: str
    label: str
    count: int = Field(ge=0)
    tone: str


class InventoryReplenishmentRow(ReadModel):
    sku_id: str
    warehouse_id: str
    available_qty: int
    incoming_qty: int
    forecast_weekly_units: Decimal
    inventory_cover_days: int | None = None
    recommended_order_qty: int = Field(ge=0)


class InventoryOverstockRow(ReadModel):
    sku_id: str
    warehouse_id: str
    inventory_cover_days: int | None = None
    tied_value: Decimal = Field(ge=0)


class InventoryDashboard(ReadModel):
    generated_at: datetime
    warehouse_id: str | None = None
    warehouse_ids: tuple[str, ...]
    search: str | None = None
    kpis: InventoryDashboardKpis
    cover_buckets: tuple[InventoryCoverBucket, ...]
    replenishment_rows: tuple[InventoryReplenishmentRow, ...]
    overstock_rows: tuple[InventoryOverstockRow, ...]
    balance_warnings: tuple[InventoryBalance, ...]
    data_sources: tuple[str, ...]
