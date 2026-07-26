from application.dto.inventory import InventoryDashboard
from web.presenters.common import format_money, format_timestamp
from web.view_models.inventory_dashboard import (
    InventoryCoverBucketViewModel,
    InventoryDashboardKpiViewModel,
    InventoryDashboardPageViewModel,
    InventoryOverstockViewModel,
    InventoryReplenishmentViewModel,
    InventoryWarningViewModel,
)


class InventoryDashboardPresenter:
    @staticmethod
    def to_page(
        dashboard: InventoryDashboard,
    ) -> InventoryDashboardPageViewModel:
        kpis = dashboard.kpis
        maximum = max(
            (item.count for item in dashboard.cover_buckets),
            default=0,
        )
        return InventoryDashboardPageViewModel(
            generated_at=format_timestamp(dashboard.generated_at),
            warehouse_id=dashboard.warehouse_id or "",
            warehouse_ids=dashboard.warehouse_ids,
            search=dashboard.search or "",
            kpis=(
                InventoryDashboardKpiViewModel(
                    label="可售库存金额",
                    value=f"${format_money(kpis.available_inventory_value)}",
                    meta=f"按成本估值 · {kpis.inventory_skus} SKU",
                    accent="primary",
                ),
                InventoryDashboardKpiViewModel(
                    label="缺货风险 SKU",
                    value=f"{kpis.stockout_risk_skus:,}",
                    meta=(
                        "预计断货损失 "
                        f"${format_money(kpis.estimated_stockout_loss)}"
                    ),
                    accent="danger",
                ),
                InventoryDashboardKpiViewModel(
                    label="平均覆盖天数",
                    value=f"{kpis.average_cover_days:,.0f}",
                    meta="目标区间 30 – 60 天",
                    accent="primary",
                ),
                InventoryDashboardKpiViewModel(
                    label="呆滞占压",
                    value=f"${format_money(kpis.overstock_tied_value)}",
                    meta=f"覆盖 > 120 天 · {kpis.overstock_skus} SKU",
                    accent="warning",
                ),
            ),
            cover_buckets=tuple(
                InventoryCoverBucketViewModel(
                    label=item.label,
                    count=item.count,
                    tone=item.tone,
                    height=(
                        f"{max(8, int(item.count / maximum * 100))}%"
                        if maximum
                        else "8%"
                    ),
                )
                for item in dashboard.cover_buckets
            ),
            replenishment_rows=tuple(
                InventoryReplenishmentViewModel(
                    sku_id=row.sku_id,
                    warehouse_id=row.warehouse_id,
                    available_qty=f"{row.available_qty:,}",
                    incoming_qty=f"{row.incoming_qty:,}",
                    forecast_weekly_units=f"{row.forecast_weekly_units:,.0f}",
                    inventory_cover_days=(
                        f"{row.inventory_cover_days} 天"
                        if row.inventory_cover_days is not None
                        else "—"
                    ),
                    cover_tone=(
                        "negative"
                        if row.inventory_cover_days is not None
                        and row.inventory_cover_days < 12
                        else "warning"
                    ),
                    recommended_order_qty=(
                        f"{row.recommended_order_qty:,}"
                    ),
                )
                for row in dashboard.replenishment_rows
            ),
            overstock_rows=tuple(
                InventoryOverstockViewModel(
                    sku_id=row.sku_id,
                    warehouse_id=row.warehouse_id,
                    inventory_cover_days=(
                        f"{row.inventory_cover_days} 天"
                        if row.inventory_cover_days is not None
                        else "—"
                    ),
                    tied_value=f"${format_money(row.tied_value)}",
                )
                for row in dashboard.overstock_rows
            ),
            warnings=tuple(
                InventoryWarningViewModel(
                    sku_id=row.sku_id,
                    warehouse_id=row.warehouse_id,
                    on_hand_qty=row.on_hand_qty,
                    reserved_qty=row.reserved_qty,
                    blocked_qty=row.blocked_qty,
                    available_qty=row.available_qty,
                    expected_available_qty=(
                        row.on_hand_qty
                        - row.reserved_qty
                        - row.blocked_qty
                    ),
                )
                for row in dashboard.balance_warnings
            ),
        )
