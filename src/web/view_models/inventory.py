from dataclasses import dataclass


@dataclass(frozen=True)
class InventoryBalanceRowViewModel:
    sku_id: str
    warehouse_id: str
    on_hand_qty: int
    reserved_qty: int
    blocked_qty: int
    available_qty: int
    incoming_qty: int
    available_difference: int
    has_balance_warning: bool
    updated_at: str


@dataclass(frozen=True)
class InventoryRiskRowViewModel:
    sku_id: str
    warehouse_id: str
    available_qty: int
    incoming_qty: int
    inventory_cover_days: str
    stock_status: str
    status_label: str


@dataclass(frozen=True)
class InventoryPageViewModel:
    generated_at: str
    data_as_of: str
    balance_count: int
    replenishment_count: int
    overstock_count: int
    warning_count: int
    empty: bool
    chart_options: dict[str, object]
    balances: tuple[InventoryBalanceRowViewModel, ...]
    replenishment_risks: tuple[InventoryRiskRowViewModel, ...]
    overstock_risks: tuple[InventoryRiskRowViewModel, ...]
