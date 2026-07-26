from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from application.dto.inventory.dashboard import (
    InventoryCoverBucket,
    InventoryDashboard,
    InventoryDashboardKpis,
    InventoryDashboardSupplementRequest,
    InventoryDecisionInput,
    InventoryOverstockRow,
    InventoryReplenishmentRow,
)
from application.repositories.inventory import (
    InventoryDashboardSupplementProvider,
    InventoryRepository,
)


TWO_PLACES = Decimal("0.01")


class InventoryDashboardService:
    """Turn inventory snapshots into replenishment and reduction decisions."""

    def __init__(
        self,
        *,
        repository: InventoryRepository,
        supplement_provider: InventoryDashboardSupplementProvider,
    ) -> None:
        self._repository = repository
        self._supplement_provider = supplement_provider

    def get_dashboard(
        self,
        *,
        warehouse_id: str | None = None,
        search: str | None = None,
        limit: int = 10_000,
        generated_at: datetime | None = None,
    ) -> InventoryDashboard:
        if not 1 <= limit <= 10_000:
            raise ValueError("limit must be between 1 and 10000.")
        resolved_warehouse = (
            warehouse_id.strip()
            if warehouse_id and warehouse_id.strip()
            else None
        )
        resolved_search = search.strip() if search and search.strip() else None
        all_balances = list(
            self._repository.list_inventory_balances(limit=limit)
        )
        warehouse_ids = tuple(
            sorted({row.warehouse_id for row in all_balances})
        )
        if resolved_warehouse and resolved_warehouse not in warehouse_ids:
            raise ValueError(
                f"Unsupported warehouse_id: {resolved_warehouse}."
            )
        balances = [
            row
            for row in all_balances
            if (
                resolved_warehouse is None
                or row.warehouse_id == resolved_warehouse
            )
            and (
                resolved_search is None
                or resolved_search.casefold() in row.sku_id.casefold()
            )
        ]
        cover_rows = [
            row
            for row in self._repository.list_inventory_cover(limit=limit)
            if (
                resolved_warehouse is None
                or row.warehouse_id == resolved_warehouse
            )
            and (
                resolved_search is None
                or resolved_search.casefold() in row.sku_id.casefold()
            )
        ]
        warnings = tuple(
            row
            for row in balances
            if (
                row.on_hand_qty
                - row.reserved_qty
                - row.blocked_qty
                != row.available_qty
            )
        )
        warning_keys = {
            _key(row.sku_id, row.warehouse_id) for row in warnings
        }
        valid_cover = [
            row
            for row in cover_rows
            if _key(row.sku_id, row.warehouse_id) not in warning_keys
        ]
        decision_inputs = tuple(
            InventoryDecisionInput(
                sku_id=row.sku_id,
                warehouse_id=row.warehouse_id,
                available_qty=row.available_qty or 0,
                incoming_qty=row.incoming_qty or 0,
                forecast_4w_units=row.forecast_4w_units,
                inventory_cover_days=row.inventory_cover_days,
                stock_status=row.stock_status,
            )
            for row in valid_cover
        )
        supplement = self._supplement_provider.get_supplement(
            InventoryDashboardSupplementRequest(rows=decision_inputs)
        )
        replenishment = sorted(
            (
                row
                for row in valid_cover
                if row.stock_status == "replenish"
            ),
            key=lambda row: (
                row.inventory_cover_days is None,
                row.inventory_cover_days or 0,
                row.sku_id,
                row.warehouse_id,
            ),
        )
        overstock = sorted(
            (
                row
                for row in valid_cover
                if row.stock_status == "overstock"
            ),
            key=lambda row: (
                -(row.inventory_cover_days or 0),
                row.sku_id,
                row.warehouse_id,
            ),
        )
        cover_values = [
            Decimal(row.inventory_cover_days)
            for row in valid_cover
            if row.inventory_cover_days is not None
        ]
        average_cover = (
            (
                sum(cover_values, Decimal("0"))
                / Decimal(len(cover_values))
            ).quantize(TWO_PLACES, ROUND_HALF_UP)
            if cover_values
            else Decimal("0")
        )
        return InventoryDashboard(
            generated_at=generated_at or datetime.now(timezone.utc),
            warehouse_id=resolved_warehouse,
            warehouse_ids=warehouse_ids,
            search=resolved_search,
            kpis=InventoryDashboardKpis(
                available_inventory_value=(
                    supplement.available_inventory_value
                ),
                inventory_skus=len({row.sku_id for row in balances}),
                stockout_risk_skus=len(
                    {row.sku_id for row in replenishment}
                ),
                estimated_stockout_loss=(
                    supplement.estimated_stockout_loss
                ),
                average_cover_days=average_cover,
                overstock_skus=len({row.sku_id for row in overstock}),
                overstock_tied_value=supplement.overstock_tied_value,
            ),
            cover_buckets=_cover_buckets(valid_cover),
            replenishment_rows=tuple(
                InventoryReplenishmentRow(
                    sku_id=row.sku_id,
                    warehouse_id=row.warehouse_id,
                    available_qty=row.available_qty or 0,
                    incoming_qty=row.incoming_qty or 0,
                    forecast_weekly_units=_weekly_forecast(row),
                    inventory_cover_days=row.inventory_cover_days,
                    recommended_order_qty=(
                        supplement.recommended_order_qty.get(
                            _key(row.sku_id, row.warehouse_id),
                            0,
                        )
                    ),
                )
                for row in replenishment
            ),
            overstock_rows=tuple(
                InventoryOverstockRow(
                    sku_id=row.sku_id,
                    warehouse_id=row.warehouse_id,
                    inventory_cover_days=row.inventory_cover_days,
                    tied_value=supplement.tied_value_by_key.get(
                        _key(row.sku_id, row.warehouse_id),
                        Decimal("0"),
                    ),
                )
                for row in overstock
            ),
            balance_warnings=warnings,
            data_sources=(
                "inventory.inventory_balances",
                "analytics.v_inventory_cover",
                supplement.data_source,
            ),
        )


def _cover_buckets(rows: list) -> tuple[InventoryCoverBucket, ...]:
    definitions = (
        ("lt7", "< 7 天", lambda value: value < 7, "danger"),
        ("7to14", "7 – 14 天", lambda value: 7 <= value < 14, "danger"),
        ("14to30", "14 – 30 天", lambda value: 14 <= value < 30, "info"),
        ("30to60", "30 – 60 · 健康", lambda value: 30 <= value <= 60, "healthy"),
        ("60to120", "60 – 120 天", lambda value: 60 < value <= 120, "warning"),
        ("gt120", "> 120 · 呆滞", lambda value: value > 120, "overstock"),
    )
    values = [
        row.inventory_cover_days
        for row in rows
        if row.inventory_cover_days is not None
    ]
    return tuple(
        InventoryCoverBucket(
            bucket_id=bucket_id,
            label=label,
            count=sum(predicate(value) for value in values),
            tone=tone,
        )
        for bucket_id, label, predicate, tone in definitions
    )


def _weekly_forecast(row: object) -> Decimal:
    if row.forecast_4w_units is not None:
        return (row.forecast_4w_units / Decimal("4")).quantize(
            TWO_PLACES,
            ROUND_HALF_UP,
        )
    if row.forecast_daily_units is not None:
        return (row.forecast_daily_units * Decimal("7")).quantize(
            TWO_PLACES,
            ROUND_HALF_UP,
        )
    return Decimal("0")


def _key(sku_id: str, warehouse_id: str) -> str:
    return f"{sku_id}|{warehouse_id}"
