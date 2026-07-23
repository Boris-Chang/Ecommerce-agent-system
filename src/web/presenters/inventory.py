from collections.abc import Sequence
from datetime import datetime, timezone

from application.dto.inventory import InventoryBalance, InventoryCover
from web.presenters.common import format_timestamp
from web.view_models.inventory import (
    InventoryBalanceRowViewModel,
    InventoryPageViewModel,
    InventoryRiskRowViewModel,
)


MAX_CHART_ROWS = 20


class InventoryPresenter:
    @staticmethod
    def to_page(
        *,
        balances: Sequence[InventoryBalance],
        replenishment_risks: Sequence[InventoryCover],
        overstock_risks: Sequence[InventoryCover],
        generated_at: datetime | None = None,
    ) -> InventoryPageViewModel:
        resolved_generated_at = generated_at or datetime.now(timezone.utc)
        balance_rows = tuple(
            _to_balance_row(balance) for balance in balances
        )
        replenish_rows = tuple(
            _to_risk_row(risk, "需要补货") for risk in replenishment_risks
        )
        overstock_rows = tuple(
            _to_risk_row(risk, "库存积压") for risk in overstock_risks
        )
        chart_balances = list(balances[:MAX_CHART_ROWS])
        labels = [
            f"{row.sku_id} · {row.warehouse_id}" for row in chart_balances
        ]
        chart_options: dict[str, object] = {
            "animationDuration": 350,
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "legend": {"bottom": 0},
            "grid": {
                "left": 40,
                "right": 20,
                "top": 24,
                "bottom": 80,
                "containLabel": True,
            },
            "xAxis": {
                "type": "category",
                "data": labels,
                "axisLabel": {"rotate": 32},
            },
            "yAxis": {"type": "value", "name": "库存数量"},
            "series": [
                {
                    "name": "可售",
                    "type": "bar",
                    "stack": "current",
                    "data": [row.available_qty for row in chart_balances],
                },
                {
                    "name": "预占",
                    "type": "bar",
                    "stack": "current",
                    "data": [row.reserved_qty for row in chart_balances],
                },
                {
                    "name": "冻结",
                    "type": "bar",
                    "stack": "current",
                    "data": [row.blocked_qty for row in chart_balances],
                },
                {
                    "name": "在途",
                    "type": "bar",
                    "data": [row.incoming_qty for row in chart_balances],
                },
            ],
        }
        data_as_of = max(
            (row.updated_at for row in balances),
            default=None,
        )
        warning_count = sum(
            row.has_balance_warning for row in balance_rows
        )
        return InventoryPageViewModel(
            generated_at=resolved_generated_at.astimezone().strftime(
                "%Y-%m-%d %H:%M"
            ),
            data_as_of=format_timestamp(data_as_of),
            balance_count=len(balance_rows),
            replenishment_count=len(replenish_rows),
            overstock_count=len(overstock_rows),
            warning_count=warning_count,
            empty=not balances,
            chart_options=chart_options,
            balances=balance_rows,
            replenishment_risks=replenish_rows,
            overstock_risks=overstock_rows,
        )


def _to_balance_row(balance: InventoryBalance) -> InventoryBalanceRowViewModel:
    difference = (
        balance.on_hand_qty
        - balance.reserved_qty
        - balance.blocked_qty
        - balance.available_qty
    )
    return InventoryBalanceRowViewModel(
        sku_id=balance.sku_id,
        warehouse_id=balance.warehouse_id,
        on_hand_qty=balance.on_hand_qty,
        reserved_qty=balance.reserved_qty,
        blocked_qty=balance.blocked_qty,
        available_qty=balance.available_qty,
        incoming_qty=balance.incoming_qty,
        available_difference=difference,
        has_balance_warning=difference != 0,
        updated_at=format_timestamp(balance.updated_at),
    )


def _to_risk_row(
    risk: InventoryCover,
    status_label: str,
) -> InventoryRiskRowViewModel:
    cover_days = (
        str(risk.inventory_cover_days)
        if risk.inventory_cover_days is not None
        else "—"
    )
    return InventoryRiskRowViewModel(
        sku_id=risk.sku_id,
        warehouse_id=risk.warehouse_id,
        available_qty=risk.available_qty or 0,
        incoming_qty=risk.incoming_qty or 0,
        inventory_cover_days=cover_days,
        stock_status=risk.stock_status or "unknown",
        status_label=status_label,
    )
