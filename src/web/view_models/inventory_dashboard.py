from dataclasses import dataclass


@dataclass(frozen=True)
class InventoryDashboardKpiViewModel:
    label: str
    value: str
    meta: str
    accent: str


@dataclass(frozen=True)
class InventoryCoverBucketViewModel:
    label: str
    count: int
    tone: str
    height: str


@dataclass(frozen=True)
class InventoryReplenishmentViewModel:
    sku_id: str
    warehouse_id: str
    available_qty: str
    incoming_qty: str
    forecast_weekly_units: str
    inventory_cover_days: str
    cover_tone: str
    recommended_order_qty: str


@dataclass(frozen=True)
class InventoryOverstockViewModel:
    sku_id: str
    warehouse_id: str
    inventory_cover_days: str
    tied_value: str


@dataclass(frozen=True)
class InventoryWarningViewModel:
    sku_id: str
    warehouse_id: str
    on_hand_qty: int
    reserved_qty: int
    blocked_qty: int
    available_qty: int
    expected_available_qty: int


@dataclass(frozen=True)
class InventoryDashboardPageViewModel:
    generated_at: str
    warehouse_id: str
    warehouse_ids: tuple[str, ...]
    search: str
    kpis: tuple[InventoryDashboardKpiViewModel, ...]
    cover_buckets: tuple[InventoryCoverBucketViewModel, ...]
    replenishment_rows: tuple[InventoryReplenishmentViewModel, ...]
    overstock_rows: tuple[InventoryOverstockViewModel, ...]
    warnings: tuple[InventoryWarningViewModel, ...]
