from typing import Protocol, Sequence

from application.dto.inventory import InventoryBalance, InventoryCover


class InventoryRepository(Protocol):
    def list_inventory_balances(
        self,
        *,
        sku_id: str | None = None,
        warehouse_id: str | None = None,
        limit: int = 1_000,
    ) -> Sequence[InventoryBalance]: ...

    def list_inventory_cover(
        self,
        *,
        stock_status: str | None = None,
        limit: int = 1_000,
    ) -> Sequence[InventoryCover]: ...
