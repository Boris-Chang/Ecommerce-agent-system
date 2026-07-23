from datetime import date, datetime, timezone
from decimal import Decimal

from application.dto.inventory import InventoryBalance, InventoryCover
from application.dto.sku import SkuDailySales
from web.presenters import InventoryPresenter, SalesPresenter


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
