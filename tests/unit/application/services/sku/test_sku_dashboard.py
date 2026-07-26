from datetime import date
from decimal import Decimal

from application.dto.inventory import InventoryCover
from application.dto.sku import (
    SkuDailyRefunds,
    SkuDailySales,
    SkuWeeklySales,
)
from application.services.sku import SkuDashboardService
from infrastructure.mock import FixedSkuDashboardSupplementProvider


class SalesRepository:
    def list_sku_daily_sales(self, **kwargs) -> list[SkuDailySales]:
        current = kwargs["end_date"] == date(2026, 7, 14)
        return [
            SkuDailySales(
                sales_date=kwargs["end_date"],
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
                units_sold=10 if current else 5,
                net_sales=Decimal("100") if current else Decimal("50"),
                currency_code="USD",
            )
        ]

    def list_sku_weekly_sales(self, **kwargs) -> list[SkuWeeklySales]:
        return [
            SkuWeeklySales(
                week_start=date(2026, 7, 6),
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
                units_sold=10,
                net_sales=Decimal("100"),
                currency_code="USD",
            )
        ]


class RefundRepository:
    def list_sku_daily_refunds(self, **kwargs) -> list[SkuDailyRefunds]:
        return [
            SkuDailyRefunds(
                refund_date=date(2026, 7, 14),
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
                refund_reason="尺码不符",
                refund_count=1,
                refunded_order_count=1,
                refunded_units=1,
                item_refund_amount=Decimal("10"),
                tax_refund_amount=Decimal("0"),
                shipping_refund_amount=Decimal("0"),
                currency_code="USD",
            )
        ]

    def list_sku_weekly_refunds(self, **kwargs) -> list:
        return []


class InventoryRepository:
    def list_inventory_cover(self, **kwargs) -> list[InventoryCover]:
        return [
            InventoryCover(
                sku_id="SKU001",
                warehouse_id="WH_US",
                inventory_cover_days=9,
                stock_status="replenish",
            )
        ]

    def list_inventory_balances(self, **kwargs) -> list:
        return []


def test_sku_dashboard_merges_sales_refunds_and_inventory() -> None:
    dashboard = SkuDashboardService(
        sales_repository=SalesRepository(),
        refund_repository=RefundRepository(),
        inventory_repository=InventoryRepository(),
        supplement_provider=FixedSkuDashboardSupplementProvider(),
    ).get_dashboard(
        channel_account_id="CA_SHOPIFY_US",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 14),
    )

    assert dashboard.kpis.active_skus == 1
    assert dashboard.kpis.top_10_concentration_pct == Decimal("100.0000")
    assert dashboard.kpis.unit_refund_rate_pct == Decimal("10.0000")
    assert dashboard.rows[0].sales_change_pct == Decimal("100.0000")
    assert dashboard.rows[0].primary_refund_reason == "尺码不符"
    assert dashboard.rows[0].inventory_cover_days == 9
