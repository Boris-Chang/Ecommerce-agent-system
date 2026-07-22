from application.dto.analytics import InventoryCover
from application.repositories.analytics import InventoryRepository


REPLENISH_STATUS = "replenish"
OVERSTOCK_STATUS = "overstock"


class InventoryRiskService:
    """Expose inventory snapshots that require replenishment or stock reduction."""

    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    def list_inventory_risks(self, *, limit: int = 1_000) -> list[InventoryCover]:
        """Return replenishment risks first, followed by the largest overstocks."""
        _validate_limit(limit)
        replenish = self.list_replenishment_risks(limit=limit)
        overstock = self.list_overstock_risks(limit=limit)
        return (replenish + overstock)[:limit]

    def list_replenishment_risks(
        self,
        *,
        limit: int = 1_000,
    ) -> list[InventoryCover]:
        """Return inventory snapshots marked for replenishment."""
        _validate_limit(limit)
        return list(
            self._repository.list_inventory_cover(
                stock_status=REPLENISH_STATUS,
                limit=limit,
            )
        )

    def list_overstock_risks(
        self,
        *,
        limit: int = 1_000,
    ) -> list[InventoryCover]:
        """Return overstock snapshots ordered from highest cover to lowest."""
        _validate_limit(limit)
        rows = self._repository.list_inventory_cover(
            stock_status=OVERSTOCK_STATUS,
            limit=limit,
        )
        return sorted(rows, key=_overstock_sort_key)


def _validate_limit(limit: int) -> None:
    if limit < 1:
        raise ValueError("limit must be at least 1.")


def _overstock_sort_key(item: InventoryCover) -> tuple[bool, int, str, str]:
    cover_days = item.inventory_cover_days
    return (
        cover_days is None,
        -(cover_days or 0),
        item.sku_id,
        item.warehouse_id,
    )
