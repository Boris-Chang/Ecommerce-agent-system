from decimal import Decimal, ROUND_HALF_UP

from application.dto.inventory.dashboard import (
    InventoryDashboardSupplement,
    InventoryDashboardSupplementRequest,
)


UNIT_COST = Decimal("18.75")
TWO_PLACES = Decimal("0.01")


class FixedInventoryDashboardSupplementProvider:
    """Temporary valuation and replenishment adapter with stable outputs."""

    def get_supplement(
        self,
        request: InventoryDashboardSupplementRequest,
    ) -> InventoryDashboardSupplement:
        available_value = sum(
            (
                Decimal(max(0, row.available_qty)) * UNIT_COST
                for row in request.rows
            ),
            Decimal("0"),
        )
        tied_value_by_key = {
            _key(row.sku_id, row.warehouse_id): (
                Decimal(max(0, row.available_qty)) * UNIT_COST
            ).quantize(TWO_PLACES, ROUND_HALF_UP)
            for row in request.rows
            if row.stock_status == "overstock"
        }
        recommended = {
            _key(row.sku_id, row.warehouse_id): _recommended_order(row)
            for row in request.rows
            if row.stock_status == "replenish"
        }
        replenish_count = sum(
            row.stock_status == "replenish" for row in request.rows
        )
        return InventoryDashboardSupplement(
            available_inventory_value=available_value.quantize(
                TWO_PLACES,
                ROUND_HALF_UP,
            ),
            estimated_stockout_loss=(
                Decimal(replenish_count) * Decimal("5200")
            ).quantize(TWO_PLACES),
            overstock_tied_value=sum(
                tied_value_by_key.values(),
                Decimal("0"),
            ).quantize(TWO_PLACES),
            recommended_order_qty=recommended,
            tied_value_by_key=tied_value_by_key,
            data_source="fixed_inventory_decision_metrics_v1",
        )


def _recommended_order(row: object) -> int:
    four_week_demand = row.forecast_4w_units or Decimal("600")
    target = four_week_demand * Decimal("2")
    net_supply = Decimal(row.available_qty + row.incoming_qty)
    return max(0, int((target - net_supply).to_integral_value()))


def _key(sku_id: str, warehouse_id: str) -> str:
    return f"{sku_id}|{warehouse_id}"
