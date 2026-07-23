from application.dto.analytics import InventoryCover
from application.services.inventory_risk import InventoryRiskService


class FakeInventoryRepository:
    def __init__(self, rows_by_status: dict[str, list[InventoryCover]]) -> None:
        self.rows_by_status = rows_by_status
        self.calls: list[dict] = []

    def list_inventory_cover(
        self,
        *,
        stock_status: str | None = None,
        limit: int = 1_000,
    ) -> list[InventoryCover]:
        self.calls.append({"stock_status": stock_status, "limit": limit})
        return self.rows_by_status.get(stock_status or "", [])[:limit]


def _inventory(
    sku_id: str,
    *,
    status: str,
    cover_days: int | None,
) -> InventoryCover:
    return InventoryCover(
        sku_id=sku_id,
        warehouse_id="warehouse-1",
        inventory_cover_days=cover_days,
        stock_status=status,
    )


def test_list_inventory_risks_prioritizes_replenishment_and_respects_limit() -> None:
    repository = FakeInventoryRepository(
        {
            "replenish": [
                _inventory("sku-replenish", status="replenish", cover_days=0)
            ],
            "overstock": [
                _inventory("sku-overstock", status="overstock", cover_days=120)
            ],
        }
    )
    service = InventoryRiskService(repository)

    risks = service.list_inventory_risks(limit=1)

    assert [risk.sku_id for risk in risks] == ["sku-replenish"]
    assert repository.calls == [
        {"stock_status": "replenish", "limit": 1},
        {"stock_status": "overstock", "limit": 1},
    ]


def test_list_overstock_risks_orders_largest_cover_first() -> None:
    repository = FakeInventoryRepository(
        {
            "overstock": [
                _inventory("sku-120", status="overstock", cover_days=120),
                _inventory("sku-300", status="overstock", cover_days=300),
                _inventory("sku-unknown", status="overstock", cover_days=None),
            ]
        }
    )
    service = InventoryRiskService(repository)

    risks = service.list_overstock_risks(limit=10)

    assert [risk.sku_id for risk in risks] == [
        "sku-300",
        "sku-120",
        "sku-unknown",
    ]


def test_list_replenishment_risks_uses_repository_status_filter() -> None:
    repository = FakeInventoryRepository({"replenish": []})
    service = InventoryRiskService(repository)

    assert service.list_replenishment_risks(limit=25) == []
    assert repository.calls == [{"stock_status": "replenish", "limit": 25}]


def test_inventory_risk_service_rejects_non_positive_limit() -> None:
    repository = FakeInventoryRepository({})
    service = InventoryRiskService(repository)

    try:
        service.list_inventory_risks(limit=0)
    except ValueError as exc:
        assert str(exc) == "limit must be at least 1."
    else:
        raise AssertionError("Expected a ValueError for a non-positive limit.")

    assert repository.calls == []
