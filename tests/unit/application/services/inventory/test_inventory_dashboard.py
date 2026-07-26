from datetime import datetime, timezone
from decimal import Decimal

from application.dto.inventory import InventoryBalance, InventoryCover
from application.services.inventory import InventoryDashboardService
from infrastructure.mock import FixedInventoryDashboardSupplementProvider


class InventoryRepository:
    def list_inventory_balances(self, **kwargs) -> list[InventoryBalance]:
        return [
            InventoryBalance(
                sku_id="SKU001",
                warehouse_id="WH_US",
                on_hand_qty=100,
                reserved_qty=10,
                blocked_qty=5,
                available_qty=85,
                incoming_qty=20,
                updated_at=datetime(2026, 7, 26, tzinfo=timezone.utc),
            )
        ]

    def list_inventory_cover(self, **kwargs) -> list[InventoryCover]:
        return [
            InventoryCover(
                sku_id="SKU001",
                warehouse_id="WH_US",
                available_qty=85,
                incoming_qty=20,
                forecast_4w_units=Decimal("400"),
                inventory_cover_days=9,
                stock_status="replenish",
            ),
            InventoryCover(
                sku_id="SKU002",
                warehouse_id="WH_US",
                available_qty=500,
                incoming_qty=0,
                forecast_4w_units=Decimal("20"),
                inventory_cover_days=150,
                stock_status="overstock",
            ),
        ]


def test_inventory_dashboard_builds_decision_lists() -> None:
    dashboard = InventoryDashboardService(
        repository=InventoryRepository(),
        supplement_provider=FixedInventoryDashboardSupplementProvider(),
    ).get_dashboard()

    assert dashboard.kpis.stockout_risk_skus == 1
    assert dashboard.kpis.overstock_skus == 1
    assert dashboard.kpis.average_cover_days == Decimal("79.50")
    assert dashboard.replenishment_rows[0].forecast_weekly_units == Decimal(
        "100.00"
    )
    assert dashboard.replenishment_rows[0].recommended_order_qty > 0
    assert dashboard.overstock_rows[0].tied_value > 0
