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
        rows = [
            SkuDailySales(
                sales_date=kwargs["start_date"],
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
                units_sold=6,
                net_sales=Decimal("60"),
                currency_code="USD",
            ),
            SkuDailySales(
                sales_date=kwargs["end_date"],
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
                units_sold=4,
                net_sales=Decimal("40"),
                currency_code="USD",
            )
        ]
        if kwargs["start_date"] == date(2026, 6, 24):
            rows.append(
                SkuDailySales(
                    sales_date=date(2026, 7, 1),
                    sku_id="SKU002",
                    channel_account_id=kwargs["channel_account_id"],
                    units_sold=20,
                    net_sales=Decimal("200"),
                    currency_code="USD",
                )
            )
        return rows

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
        return [
            SkuDailyRefunds(
                refund_date=kwargs["end_date"],
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
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


class FakeOrderRepository:
    def count_orders(self, **kwargs) -> int:
        if kwargs["start_date"] == kwargs["end_date"]:
            return 2
        return 4


class FakeSupplementProvider:
    def get_supplement(
        self,
        request: OverviewSupplementRequest,
    ) -> OverviewSupplement:
        return OverviewSupplement(
            gross_profit_share_pct={
                "CA_SHOPIFY_US": Decimal("70"),
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
        order_repository=FakeOrderRepository(),
        supplement_provider=FakeSupplementProvider(),
    ).get_dashboard(
        channel_account_id="CA_SHOPIFY_US",
        as_of_date=date(2026, 7, 14),
        currency_code="USD",
    )

    assert dashboard.filters.channel_account_id == "CA_SHOPIFY_US"
    assert dashboard.filters.day == date(2026, 7, 14)
    assert dashboard.filters.week_start == date(2026, 7, 13)
    assert dashboard.filters.trend_start == date(2026, 6, 24)
    assert dashboard.filters.trend_end == date(2026, 7, 14)
    assert dashboard.daily_kpis.net_sales == Decimal("40")
    assert dashboard.daily_kpis.units_sold == 4
    assert dashboard.daily_kpis.orders_count == 2
    assert dashboard.daily_kpis.average_order_value == Decimal("20.00")
    assert dashboard.daily_kpis.unit_refund_rate_pct == Decimal("25.0000")
    assert dashboard.weekly_kpis.net_sales == Decimal("100")
    assert dashboard.weekly_kpis.units_sold == 10
    assert dashboard.weekly_kpis.orders_count == 4
    assert dashboard.weekly_kpis.average_order_value == Decimal("25.00")
    assert dashboard.weekly_kpis.unit_refund_rate_pct == Decimal("10.0000")
    assert len(dashboard.trend) == 21
    assert dashboard.trend[0].sales_date == date(2026, 6, 24)
    assert dashboard.trend[-1].sales_date == date(2026, 7, 14)
    assert len(dashboard.channel_contributions) == 1
    assert dashboard.channel_contributions[0].net_sales_share_pct == Decimal(
        "100.0000"
    )
    assert dashboard.sku_performance[0].sku_id == "SKU002"
    assert dashboard.sku_performance[0].net_sales == Decimal("200")
    sku001 = next(
        row for row in dashboard.sku_performance if row.sku_id == "SKU001"
    )
    assert sku001.inventory_cover_days == 7
    assert sku001.forecast_4w_p50 != Decimal("999")
    assert "sku_weighted_moving_average:v0.1" in dashboard.data_sources
