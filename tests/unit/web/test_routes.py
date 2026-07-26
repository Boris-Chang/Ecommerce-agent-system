from collections.abc import Iterator
from datetime import date, datetime, timezone
from decimal import Decimal
import logging
from types import SimpleNamespace

from fastapi.testclient import TestClient

from application.agents.business_inspection import (
    BusinessInspectionFinding,
    BusinessInspectionOutput,
    BusinessInspectionRequest,
    InspectionEvidence,
)
from application.dto.channel import ChannelSalesTotals
from application.dto.inventory import InventoryBalance, InventoryCover
from application.dto.sku import (
    SkuDailyRefunds,
    SkuDailySales,
    SkuWeeklyRefunds,
    SkuWeeklySales,
)
from core.settings import DatabaseSettings
from web.bootstrap import create_app
from web.dependencies import (
    get_business_inspection_service,
    get_read_uow,
)
from web.settings import WebSettings


class FakeSalesRepository:
    def __init__(self) -> None:
        self.daily_calls: list[dict] = []
        self.weekly_calls: list[dict] = []

    def list_sku_daily_sales(self, **kwargs) -> list[SkuDailySales]:
        self.daily_calls.append(kwargs)
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

    def list_sku_weekly_sales(self, **kwargs) -> list[SkuWeeklySales]:
        self.weekly_calls.append(kwargs)
        return [
            SkuWeeklySales(
                week_start=date(2026, 7, 6),
                sku_id="SKU004",
                channel_account_id=kwargs["channel_account_id"],
                orders_count=5,
                units_sold=7,
                gross_sales=Decimal("140"),
                discount_amount=Decimal("10"),
                net_sales=Decimal("130"),
                currency_code="USD",
            )
        ]


class FakeRefundRepository:
    def __init__(self) -> None:
        self.daily_calls: list[dict] = []
        self.weekly_calls: list[dict] = []

    def list_sku_daily_refunds(self, **kwargs) -> list[SkuDailyRefunds]:
        self.daily_calls.append(kwargs)
        return [
            SkuDailyRefunds(
                refund_date=date(2026, 7, 12),
                sku_id="SKU005",
                channel_account_id=kwargs["channel_account_id"],
                refund_reason="damaged",
                refund_status="completed",
                refund_count=1,
                refunded_order_count=1,
                refunded_units=2,
                item_refund_amount=Decimal("44"),
                tax_refund_amount=Decimal("2"),
                shipping_refund_amount=Decimal("3"),
                currency_code="USD",
            )
        ]

    def list_sku_weekly_refunds(self, **kwargs) -> list[SkuWeeklyRefunds]:
        self.weekly_calls.append(kwargs)
        return [
            SkuWeeklyRefunds(
                week_start=date(2026, 7, 6),
                sku_id="SKU005",
                channel_account_id=kwargs["channel_account_id"],
                refund_reason="damaged",
                refund_status="completed",
                refund_count=1,
                refunded_order_count=1,
                refunded_units=2,
                item_refund_amount=Decimal("44"),
                tax_refund_amount=Decimal("2"),
                shipping_refund_amount=Decimal("3"),
                currency_code="USD",
            )
        ]


class FakeChannelSalesRepository:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def list_channel_sales_totals(
        self,
        **kwargs,
    ) -> list[ChannelSalesTotals]:
        self.calls.append(kwargs)
        return [
            ChannelSalesTotals(
                channel_account_id="CA_SHOPIFY_US",
                units_sold=75,
                gross_sales=Decimal("800"),
                discount_amount=Decimal("50"),
                net_sales=Decimal("750"),
                currency_code="USD",
            ),
            ChannelSalesTotals(
                channel_account_id="CA_AMAZON_US",
                units_sold=25,
                gross_sales=Decimal("260"),
                discount_amount=Decimal("10"),
                net_sales=Decimal("250"),
                currency_code="USD",
            ),
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
        if stock_status in {None, "replenish"}:
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


class FakeBusinessInspectionService:
    def __init__(self) -> None:
        self.calls: list[BusinessInspectionRequest] = []

    def run(
        self,
        request: BusinessInspectionRequest,
    ) -> BusinessInspectionOutput:
        self.calls.append(request)
        return BusinessInspectionOutput(
            run_id="run-web-123",
            frequency=request.frequency,
            channel_account_id=request.channel_account_id,
            start_date=request.start_date,
            end_date=request.end_date,
            generated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
            summary="销售与库存巡检完成。",
            findings=(
                BusinessInspectionFinding(
                    title="库存覆盖风险",
                    conclusion="SKU003 需要人工关注。",
                    reason=(
                        "采用 inventory_cover_risk 统一指标语义，"
                        "已有快照标记为 replenish。"
                    ),
                    severity="high",
                    metric_semantic_ids=("inventory_cover_risk",),
                    evidence_ids=("E1",),
                ),
            ),
            evidence=(
                InspectionEvidence(
                    evidence_id="E1",
                    tool_name="read_inventory_snapshot",
                    metric_semantic_ids=("inventory_cover_risk",),
                    reason="InventoryRiskService 返回 replenish 快照。",
                    facts=("SKU003 stock_status=replenish",),
                ),
            ),
            caveats=("库存是 SKU × 仓库范围，不按销售渠道拆分。",),
        )


def _build_client() -> tuple[TestClient, SimpleNamespace]:
    sales = FakeSalesRepository()
    refunds = FakeRefundRepository()
    channel_sales = FakeChannelSalesRepository()
    inventory = FakeInventoryRepository()
    inspection_service = FakeBusinessInspectionService()
    unit_of_work = SimpleNamespace(
        sales=sales,
        refunds=refunds,
        channel_sales=channel_sales,
        inventory=inventory,
        inspection_service=inspection_service,
    )

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
            WEB_CHANNEL_ACCOUNT_IDS="CA_SHOPIFY_US,CA_AMAZON_US",
            WEB_SALES_LOOKBACK_DAYS=30,
            WEB_QUERY_LIMIT=100,
            WEB_DEFAULT_END_DATE="2026-07-24",
        ),
    )
    app.dependency_overrides[get_read_uow] = override_uow
    app.dependency_overrides[get_business_inspection_service] = (
        lambda: inspection_service
    )
    return TestClient(app), unit_of_work


def test_sales_page_renders_application_data() -> None:
    client, repositories = _build_client()

    with client:
        response = client.get("/sales")

    assert response.status_code == 200
    assert "SKU 分析" in response.text
    assert "SKU001" in response.text
    assert "55.00" in response.text
    call = repositories.sales.daily_calls[0]
    assert call["channel_account_id"] == "CA_SHOPIFY_US"
    assert call["start_date"] == date(2026, 6, 25)
    assert call["end_date"] == date(2026, 7, 24)


def test_overview_page_combines_configured_channels() -> None:
    client, repositories = _build_client()

    with client:
        response = client.get("/overview")

    assert response.status_code == 200
    assert "经营总览" in response.text
    assert "净销售额趋势" in response.text
    assert "SKU001" in response.text
    assert "CA_SHOPIFY_US" in response.text
    assert "CA_AMAZON_US" in response.text
    assert len(repositories.sales.daily_calls) == 4
    assert len(repositories.refunds.daily_calls) == 4


def test_overview_page_rejects_unknown_channel() -> None:
    client, repositories = _build_client()

    with client:
        response = client.get(
            "/overview?channel_account_id=CA_UNKNOWN"
        )

    assert response.status_code == 400
    assert "Unsupported channel_account_id" in response.text
    assert repositories.sales.daily_calls == []


def test_weekly_sales_page_renders_application_data() -> None:
    client, repositories = _build_client()

    with client:
        response = client.get("/sales/weekly")

    assert response.status_code == 200
    assert "SKU 每周销售" in response.text
    assert "SKU004" in response.text
    assert "130.00" in response.text
    call = repositories.sales.weekly_calls[0]
    assert call["channel_account_id"] == "CA_SHOPIFY_US"
    assert call["start_date"] == date(2026, 6, 25)
    assert call["end_date"] == date(2026, 7, 24)


def test_sales_pages_accept_configured_amazon_channel() -> None:
    client, repositories = _build_client()

    with client:
        daily_response = client.get(
            "/sales?channel_account_id=CA_AMAZON_US"
        )
        weekly_response = client.get(
            "/sales/weekly?channel_account_id=CA_AMAZON_US"
        )
        refunds_response = client.get(
            "/sales/refunds?channel_account_id=CA_AMAZON_US"
        )

    assert daily_response.status_code == 200
    assert weekly_response.status_code == 200
    assert refunds_response.status_code == 200
    assert 'name="channel_account_id"' in daily_response.text
    assert "<select" in daily_response.text
    assert "CA_AMAZON_US" in daily_response.text
    assert "channel-switcher" not in daily_response.text
    assert repositories.sales.daily_calls[-1]["channel_account_id"] == (
        "CA_AMAZON_US"
    )
    assert repositories.sales.weekly_calls[-1]["channel_account_id"] == (
        "CA_AMAZON_US"
    )
    assert repositories.refunds.daily_calls[-1]["channel_account_id"] == (
        "CA_AMAZON_US"
    )
    assert repositories.refunds.weekly_calls[-1]["channel_account_id"] == (
        "CA_AMAZON_US"
    )


def test_sales_page_rejects_unconfigured_channel() -> None:
    client, repositories = _build_client()

    with client:
        response = client.get("/sales?channel_account_id=CA_UNKNOWN")

    assert response.status_code == 400
    assert "Unsupported channel_account_id" in response.text
    assert repositories.sales.daily_calls == []


def test_refunds_page_renders_daily_and_weekly_data() -> None:
    client, repositories = _build_client()

    with client:
        response = client.get("/sales/refunds")

    assert response.status_code == 200
    assert "SKU 退款分析" in response.text
    assert "SKU005" in response.text
    assert "44.00" in response.text
    assert repositories.refunds.daily_calls[0]["channel_account_id"] == (
        "CA_SHOPIFY_US"
    )
    assert repositories.refunds.weekly_calls[0]["end_date"] == date(
        2026,
        7,
        24,
    )


def test_channel_sales_page_renders_same_currency_shares() -> None:
    client, repositories = _build_client()

    with client:
        response = client.get("/sales/channels")

    assert response.status_code == 200
    assert "渠道销售占比" in response.text
    assert "CA_SHOPIFY_US" in response.text
    assert "75.00%" in response.text
    assert repositories.channel_sales.calls[0] == {
        "start_date": date(2026, 6, 25),
        "end_date": date(2026, 7, 24),
    }


def test_inventory_page_renders_balances_and_risks() -> None:
    client, _ = _build_client()

    with client:
        response = client.get("/inventory")

    assert response.status_code == 200
    assert "库存决策" in response.text
    assert "SKU003" in response.text
    assert "补货建议" in response.text


def test_agent_analysis_page_is_not_a_conversation() -> None:
    client, _ = _build_client()

    with client:
        response = client.get("/agent-analysis")

    assert response.status_code == 200
    assert "Agent 诊断" in response.text
    assert "运行并刷新结论" in response.text
    assert "结论 → 证据 → 建议动作 → 人工审核" in response.text
    assert 'name="question"' not in response.text


def test_web_bootstrap_enables_inspection_info_logs() -> None:
    client, _ = _build_client()

    with client:
        assert logging.getLogger(
            "application.agents.business_inspection"
        ).getEffectiveLevel() == logging.INFO
        assert logging.getLogger(
            "infrastructure.llm"
        ).getEffectiveLevel() == logging.INFO


def test_weekly_agent_refresh_renders_traceable_result() -> None:
    client, dependencies = _build_client()

    with client:
        response = client.post(
            "/agent-analysis/refresh",
            data={
                "frequency": "weekly",
                "channel_account_id": "CA_AMAZON_US",
            },
        )

    assert response.status_code == 200
    assert "每周巡检" in response.text
    assert "销售与库存巡检完成" in response.text
    assert "inventory_cover_risk" in response.text
    assert "read_inventory_snapshot" in response.text
    assert "run-web-123" in response.text
    call = dependencies.inspection_service.calls[0]
    assert call.frequency == "weekly"
    assert call.channel_account_id == "CA_AMAZON_US"
    assert call.start_date == date(2026, 7, 18)
    assert call.end_date == date(2026, 7, 24)


def test_live_health_and_not_found_pages() -> None:
    client, _ = _build_client()

    with client:
        health_response = client.get("/health/live")
        missing_response = client.get("/not-a-page")

    assert health_response.status_code == 200
    assert health_response.json() == {"status": "ok"}
    assert missing_response.status_code == 404
    assert "找不到这个页面" in missing_response.text
