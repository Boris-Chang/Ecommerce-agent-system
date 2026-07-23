from datetime import datetime

import pytest

from application.dto.inventory import InventoryBalance
from application.services.inventory import InventoryBalanceService


class FakeInventoryRepository:
    def __init__(self, rows: list[InventoryBalance] | None = None) -> None:
        self.rows = rows or []
        self.calls: list[dict] = []

    def list_inventory_balances(
        self,
        *,
        sku_id: str | None = None,
        warehouse_id: str | None = None,
        limit: int = 1_000,
    ) -> list[InventoryBalance]:
        self.calls.append(
            {
                "sku_id": sku_id,
                "warehouse_id": warehouse_id,
                "limit": limit,
            }
        )
        return self.rows[:limit]


def test_list_current_inventory_delegates_with_trimmed_filters() -> None:
    row = InventoryBalance(
        sku_id="sku-1",
        warehouse_id="warehouse-1",
        on_hand_qty=20,
        reserved_qty=3,
        blocked_qty=2,
        available_qty=15,
        incoming_qty=8,
        updated_at=datetime(2026, 7, 23, 10, 0),
    )
    repository = FakeInventoryRepository([row])
    service = InventoryBalanceService(repository)

    result = service.list_current_inventory(
        sku_id=" sku-1 ",
        warehouse_id=" warehouse-1 ",
        limit=25,
    )

    assert result == [row]
    assert repository.calls == [
        {
            "sku_id": "sku-1",
            "warehouse_id": "warehouse-1",
            "limit": 25,
        }
    ]


@pytest.mark.parametrize(
    ("field", "kwargs"),
    [
        ("sku_id", {"sku_id": " "}),
        ("warehouse_id", {"warehouse_id": " "}),
        ("limit", {"limit": 0}),
        ("limit", {"limit": 10_001}),
    ],
)
def test_list_current_inventory_rejects_invalid_query(
    field: str,
    kwargs: dict,
) -> None:
    repository = FakeInventoryRepository()
    service = InventoryBalanceService(repository)

    with pytest.raises(ValueError, match=field):
        service.list_current_inventory(**kwargs)

    assert repository.calls == []
