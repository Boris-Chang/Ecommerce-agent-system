from datetime import date
from decimal import Decimal

from application.dto.inventory import InventoryCover
from application.dto.overview import (
    OverviewInsight,
    OverviewSupplement,
    OverviewSupplementRequest,
)
from application.dto.sku import (
    SkuDailyRefunds,
    SkuDailySales,
    SkuWeeklySales,
)
from application.services.overview import OverviewDashboardService


class FakeSalesRepository:
    def list_sku_daily_sales(self, **kwargs) -> list[SkuDailySales]:
        current = kwargs["start_date"] == date(2026, 7, 1)
        values = {
            "CA_SHOPIFY_US": (
                Decimal("100") if current else Decimal("80"),
                10 if current else 8,
            ),
            "CA_AMAZON_US": (
                Decimal("50") if current else Decimal("20"),
                5 if current else 2,
            ),
        }
        net_sales, units = values[kwargs["channel_account_id"]]
        return [
            SkuDailySales(
                sales_date=kwargs["end_date"],
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
                units_sold=units,
                net_sales=net_sales,
                currency_code="USD",
            )
        ]

    def list_sku_weekly_sales(self, **kwargs) -> list[SkuWeeklySales]:
        return [
            SkuWeeklySales(
                week_start=kwargs["start_date"],
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
                units_sold=10,
                net_sales=Decimal("100"),
                currency_code="USD",
            ),
            SkuWeeklySales(
                week_start=kwargs["start_date"].replace(
                    day=kwargs["start_date"].day + 7
                ),
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
                units_sold=12,
                net_sales=Decimal("120"),
                currency_code="USD",
            ),
        ]


class FakeRefundRepository:
    def list_sku_daily_refunds(self, **kwargs) -> list[SkuDailyRefunds]:
        current = kwargs["start_date"] == date(2026, 7, 1)
        return [
            SkuDailyRefunds(
                refund_date=kwargs["end_date"],
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
                refund_count=1 if current else 0,
                refunded_order_count=1 if current else 0,
                refunded_units=1 if current else 0,
                item_refund_amount=Decimal("10") if current else Decimal("0"),
                tax_refund_amount=Decimal("0"),
                shipping_refund_amount=Decimal("0"),
                currency_code="USD",
            )
        ]

    def list_sku_weekly_refunds(self, **kwargs) -> list:
        return []


class FakeInventoryRepository:
    def list_inventory_cover(self, **kwargs) -> list[InventoryCover]:
        return [
            InventoryCover(
                sku_id="SKU001",
                warehouse_id="WH_US",
                inventory_cover_days=7,
                stock_status="replenish",
            ),
            InventoryCover(
                sku_id="SKU002",
                warehouse_id="WH_US",
                inventory_cover_days=140,
                stock_status="overstock",
            ),
        ]

    def list_inventory_balances(self, **kwargs) -> list:
        return []


class FakeSupplementProvider:
    def get_supplement(
        self,
        request: OverviewSupplementRequest,
    ) -> OverviewSupplement:
        return OverviewSupplement(
            orders_count=3,
            previous_orders_count=2,
            gross_profit_share_pct={
                "CA_SHOPIFY_US": Decimal("70"),
                "CA_AMAZON_US": Decimal("30"),
            },
            forecast_4w_p50={"SKU001": Decimal("999")},
            insights=(
                OverviewInsight(
                    category="库存",
                    severity="high",
                    title="SKU001 需要补货",
                    detail="测试结论",
                    href="/inventory",
                ),
            ),
            data_source="fake",
        )


def test_overview_dashboard_combines_real_metrics_and_typed_supplement() -> None:
    dashboard = OverviewDashboardService(
        sales_repository=FakeSalesRepository(),
        refund_repository=FakeRefundRepository(),
        inventory_repository=FakeInventoryRepository(),
        supplement_provider=FakeSupplementProvider(),
    ).get_dashboard(
        channel_account_ids=("CA_SHOPIFY_US", "CA_AMAZON_US"),
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 14),
        currency_code="USD",
    )

    assert dashboard.kpis.net_sales == Decimal("150")
    assert dashboard.kpis.units_sold == 15
    assert dashboard.kpis.orders_count == 3
    assert dashboard.kpis.average_order_value == Decimal("50.00")
    assert dashboard.kpis.unit_refund_rate_pct == Decimal("13.3333")
    assert dashboard.kpis.stockout_risk_skus == 1
    assert len(dashboard.channel_contributions) == 2
    assert dashboard.channel_contributions[0].net_sales_share_pct == Decimal(
        "66.6667"
    )
    assert dashboard.sku_performance[0].inventory_cover_days == 7
    assert dashboard.sku_performance[0].forecast_4w_p50 != Decimal("999")
    assert "sku_weighted_moving_average:v0.1" in dashboard.data_sources
