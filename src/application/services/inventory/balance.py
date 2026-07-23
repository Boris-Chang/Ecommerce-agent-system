from application.dto.inventory import InventoryBalance
from application.repositories.inventory import InventoryRepository


class InventoryBalanceService:
    """Read current SKU inventory quantities at warehouse grain."""

    def __init__(self, repository: InventoryRepository) -> None:
        self._repository = repository

    def list_current_inventory(
        self,
        *,
        sku_id: str | None = None,
        warehouse_id: str | None = None,
        limit: int = 1_000,
    ) -> list[InventoryBalance]:
        resolved_sku_id = _validate_optional_identifier(sku_id, "sku_id")
        resolved_warehouse_id = _validate_optional_identifier(
            warehouse_id,
            "warehouse_id",
        )
        _validate_limit(limit)
        return list(
            self._repository.list_inventory_balances(
                sku_id=resolved_sku_id,
                warehouse_id=resolved_warehouse_id,
                limit=limit,
            )
        )


def _validate_optional_identifier(value: str | None, field: str) -> str | None:
    if value is None:
        return None
    resolved = value.strip()
    if not resolved:
        raise ValueError(f"{field} must not be blank.")
    return resolved


def _validate_limit(limit: int) -> None:
    if not 1 <= limit <= 10_000:
        raise ValueError("limit must be between 1 and 10000.")
