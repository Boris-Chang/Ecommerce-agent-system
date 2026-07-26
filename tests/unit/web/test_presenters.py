from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

from application.agents.business_inspection import (
    BusinessInspectionFinding,
    BusinessInspectionOutput,
    InspectionEvidence,
)
from application.dto.channel import ChannelSalesShare
from application.dto.inventory import InventoryBalance, InventoryCover
from application.dto.sku import (
    SkuDashboard,
    SkuDashboardFilters,
    SkuDashboardKpis,
    SkuDashboardRow,
    SkuDailyRefunds,
    SkuDailySales,
    SkuDetailPoint,
    SkuWeeklyRefunds,
    SkuWeeklySales,
)
from web.presenters import (
    AgentAnalysisPresenter,
    ChannelSalesSharePresenter,
    InventoryPresenter,
    RefundsPresenter,
    SalesPresenter,
    SkuDashboardPresenter,
    WeeklySalesPresenter,
)


def test_sales_presenter_builds_chart_and_currency_warning() -> None:
    rows = [
        SkuDailySales(
            sales_date=date(2026, 7, 1),
            sku_id="SKU001",
            channel_account_id="CA_SHOPIFY_US",
            units_sold=3,
            net_sales=Decimal("30"),
            currency_code="USD",
        ),
        SkuDailySales(
            sales_date=date(2026, 7, 2),
            sku_id="SKU001",
            channel_account_id="CA_SHOPIFY_US",
            units_sold=4,
            net_sales=Decimal("40"),
            currency_code="SGD",
        ),
    ]

    page = SalesPresenter.to_page(
        rows=rows,
        channel_account_id="CA_SHOPIFY_US",
        channel_account_ids=("CA_SHOPIFY_US", "CA_AMAZON_US"),
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        generated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
    )

    assert page.row_count == 2
    assert page.data_as_of == "2026-07-02"
    assert page.currency_codes == ("SGD", "USD")
    assert page.has_multiple_currencies is True
    assert page.chart_options["series"][0]["data"] == [3, 4]


def test_inventory_presenter_marks_available_quantity_difference() -> None:
    balance = InventoryBalance(
        sku_id="SKU002",
        warehouse_id="WH_CN_FACTORY",
        on_hand_qty=85,
        reserved_qty=0,
        blocked_qty=0,
        available_qty=80,
        incoming_qty=0,
        updated_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
    )
    risk = InventoryCover(
        sku_id="SKU002",
        warehouse_id="WH_CN_FACTORY",
        available_qty=80,
        incoming_qty=0,
        inventory_cover_days=120,
        stock_status="overstock",
    )

    page = InventoryPresenter.to_page(
        balances=[balance],
        replenishment_risks=[],
        overstock_risks=[risk],
        generated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
    )

    assert page.balance_count == 1
    assert page.warning_count == 1
    assert page.balances[0].available_difference == 5
    assert page.balances[0].has_balance_warning is True
    assert page.overstock_count == 1


def test_weekly_sales_presenter_builds_weekly_chart() -> None:
    rows = [
        SkuWeeklySales(
            week_start=date(2026, 7, 6),
            sku_id="SKU004",
            channel_account_id="CA_SHOPIFY_US",
            units_sold=7,
            net_sales=Decimal("130"),
            currency_code="USD",
        )
    ]

    page = WeeklySalesPresenter.to_page(
        rows=rows,
        channel_account_id="CA_SHOPIFY_US",
        channel_account_ids=("CA_SHOPIFY_US", "CA_AMAZON_US"),
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        generated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
    )

    assert page.row_count == 1
    assert page.data_as_of == "2026-07-06"
    assert page.rows[0].net_sales == "130.00"
    assert page.chart_options["series"][0]["data"] == [7]


def test_refunds_presenter_keeps_daily_and_weekly_grains_separate() -> None:
    common = {
        "sku_id": "SKU005",
        "channel_account_id": "CA_SHOPIFY_US",
        "refund_reason": "damaged",
        "refund_status": "completed",
        "refund_count": 1,
        "refunded_order_count": 1,
        "refunded_units": 2,
        "item_refund_amount": Decimal("44"),
        "tax_refund_amount": Decimal("2"),
        "shipping_refund_amount": Decimal("3"),
        "currency_code": "USD",
    }
    daily = SkuDailyRefunds(refund_date=date(2026, 7, 12), **common)
    weekly = SkuWeeklyRefunds(week_start=date(2026, 7, 6), **common)

    page = RefundsPresenter.to_page(
        daily_rows=[daily],
        weekly_rows=[weekly],
        channel_account_id="CA_SHOPIFY_US",
        channel_account_ids=("CA_SHOPIFY_US", "CA_AMAZON_US"),
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        generated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
    )

    assert page.daily_row_count == 1
    assert page.weekly_row_count == 1
    assert page.daily_rows[0].period_start == "2026-07-12"
    assert page.weekly_rows[0].period_start == "2026-07-06"
    assert page.chart_options["series"][0]["data"] == [2]


def test_channel_sales_presenter_displays_precomputed_shares() -> None:
    rows = [
        ChannelSalesShare(
            channel_account_id="CA_SHOPIFY_US",
            units_sold=75,
            gross_sales=Decimal("800"),
            discount_amount=Decimal("50"),
            net_sales=Decimal("750"),
            currency_code="USD",
            units_share_pct=Decimal("75"),
            net_sales_share_pct=Decimal("75"),
        )
    ]

    page = ChannelSalesSharePresenter.to_page(
        rows=rows,
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
        generated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
    )

    assert page.channel_count == 1
    assert page.rows[0].units_share_pct == "75.00%"
    assert page.rows[0].net_sales == "750.00"
    assert page.chart_options["series"][1]["data"] == [75.0]


def test_sku_detail_chart_focuses_long_period_on_latest_30_days() -> None:
    start_date = date(2026, 6, 1)
    detail_points = tuple(
        SkuDetailPoint(
            sales_date=start_date + timedelta(days=index),
            units_sold=index + 1,
            refunded_units=index % 3,
        )
        for index in range(45)
    )
    dashboard = SkuDashboard(
        filters=SkuDashboardFilters(
            channel_account_id="CA_SHOPIFY_US",
            start_date=start_date,
            end_date=start_date + timedelta(days=44),
            currency_code="USD",
            grain="daily",
        ),
        generated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
        kpis=SkuDashboardKpis(
            active_skus=1,
            listed_skus=1,
            top_10_concentration_pct=Decimal("100"),
            unit_refund_rate_pct=Decimal("2"),
            slow_moving_skus=0,
        ),
        trend=(),
        rows=(
            SkuDashboardRow(
                sku_id="SKU001",
                units_sold=45,
                net_sales=Decimal("450"),
                unit_refund_rate_pct=Decimal("2"),
                primary_refund_reason="damaged",
                inventory_cover_days=30,
                detail_points=detail_points,
                refund_reasons=(),
            ),
        ),
        data_sources=("postgresql",),
    )

    page = SkuDashboardPresenter.to_page(
        dashboard,
        channel_account_ids=("CA_SHOPIFY_US", "CA_AMAZON_US"),
    )
    chart = page.rows[0].detail_chart_options

    assert [series["type"] for series in chart["series"]] == ["line", "bar"]
    assert chart["series"][1]["barMaxWidth"] == 8
    assert chart["dataZoom"][0]["startValue"] == 15
    assert chart["dataZoom"][0]["endValue"] == 44
    assert chart["xAxis"]["axisLabel"]["hideOverlap"] is True


def test_agent_presenter_keeps_reason_semantics_and_evidence_trace() -> None:
    output = BusinessInspectionOutput(
        run_id="run-123",
        frequency="daily",
        channel_account_id="CA_SHOPIFY_US",
        start_date=date(2026, 7, 24),
        end_date=date(2026, 7, 24),
        generated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
        summary="巡检完成。",
        findings=(
            BusinessInspectionFinding(
                title="销售事实",
                conclusion="SKU001 有销售记录。",
                reason="采用 sku_daily_sales 并引用 E1。",
                severity="info",
                metric_semantic_ids=("sku_daily_sales",),
                evidence_ids=("E1",),
            ),
        ),
        evidence=(
            InspectionEvidence(
                evidence_id="E1",
                tool_name="read_sku_sales_snapshot",
                metric_semantic_ids=("sku_daily_sales",),
                reason="SkuSalesService 返回数据。",
                facts=("SKU001 units_sold=3",),
            ),
        ),
    )

    page = AgentAnalysisPresenter.to_page(
        output,
        channel_account_ids=("CA_SHOPIFY_US", "CA_AMAZON_US"),
    )

    assert page.has_result is True
    assert page.findings[0].reason.endswith("引用 E1。")
    assert page.findings[0].metric_semantics == (
        "sku_daily_sales · SKU 每日销售",
    )
    assert page.evidence[0].tool_name == "read_sku_sales_snapshot"
