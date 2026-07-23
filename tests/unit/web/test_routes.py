from collections.abc import Iterator
from datetime import date, datetime, timezone
from decimal import Decimal
from types import SimpleNamespace

from fastapi.testclient import TestClient

from application.dto.inventory import InventoryBalance, InventoryCover
from application.dto.sku import SkuDailySales
from core.settings import DatabaseSettings
from web.bootstrap import create_app
from web.dependencies import get_read_uow
from web.settings import WebSettings


class FakeSalesRepository:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def list_sku_daily_sales(self, **kwargs) -> list[SkuDailySales]:
        self.calls.append(kwargs)
        return [
            SkuDailySales(
                sales_date=date(2026, 7, 12),
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
                orders_count=2,
                units_sold=3,
                gross_sales=Decimal("60"),
                discount_amount=Decimal("5"),
                net_sales=Decimal("55"),
                currency_code="USD",
            )
        ]


class FakeInventoryRepository:
    def list_inventory_balances(self, **kwargs) -> list[InventoryBalance]:
        return [
            InventoryBalance(
                sku_id="SKU002",
                warehouse_id="WH_US_3PL",
                on_hand_qty=20,
                reserved_qty=3,
                blocked_qty=2,
                available_qty=15,
                incoming_qty=8,
                updated_at=datetime(2026, 7, 20, tzinfo=timezone.utc),
            )
        ]

    def list_inventory_cover(
        self,
        *,
        stock_status: str | None = None,
        limit: int = 1_000,
    ) -> list[InventoryCover]:
        if stock_status == "replenish":
            return [
                InventoryCover(
                    sku_id="SKU003",
                    warehouse_id="WH_US_3PL",
                    available_qty=2,
                    incoming_qty=10,
                    inventory_cover_days=3,
                    stock_status="replenish",
                )
            ]
        return []


def _build_client() -> tuple[TestClient, FakeSalesRepository]:
    sales = FakeSalesRepository()
    inventory = FakeInventoryRepository()
    unit_of_work = SimpleNamespace(sales=sales, inventory=inventory)

    def override_uow() -> Iterator[SimpleNamespace]:
        yield unit_of_work

    app = create_app(
        database_settings=DatabaseSettings(
            DATABASE_URL=(
                "postgresql+psycopg://readonly:password@localhost/example"
            )
        ),
        web_settings=WebSettings(
            WEB_TITLE="Test Ecommerce BI",
            WEB_DEFAULT_CHANNEL_ACCOUNT_ID="CA_SHOPIFY_US",
            WEB_SALES_LOOKBACK_DAYS=30,
            WEB_QUERY_LIMIT=100,
            WEB_DEFAULT_END_DATE="2026-07-24",
        ),
    )
    app.dependency_overrides[get_read_uow] = override_uow
    return TestClient(app), sales


def test_sales_page_renders_application_data() -> None:
    client, sales = _build_client()

    with client:
        response = client.get("/sales")

    assert response.status_code == 200
    assert "销售分析" in response.text
    assert "SKU001" in response.text
    assert "55.00" in response.text
    assert sales.calls[0]["channel_account_id"] == "CA_SHOPIFY_US"
    assert sales.calls[0]["start_date"] == date(2026, 6, 25)
    assert sales.calls[0]["end_date"] == date(2026, 7, 24)


def test_inventory_page_renders_balances_and_risks() -> None:
    client, _ = _build_client()

    with client:
        response = client.get("/inventory")

    assert response.status_code == 200
    assert "库存分析" in response.text
    assert "SKU002" in response.text
    assert "SKU003" in response.text
    assert "补货风险" in response.text


def test_live_health_and_not_found_pages() -> None:
    client, _ = _build_client()

    with client:
        health_response = client.get("/health/live")
        missing_response = client.get("/not-a-page")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert missing_response.status_code == 404
    assert "找不到这个页面" in missing_response.text
