from contextlib import AbstractContextManager
from datetime import date, datetime, timezone
from decimal import Decimal
import logging
from types import SimpleNamespace

from application.agents.business_inspection import BusinessInspectionRequest
from application.dto.channel import ChannelSalesTotals
from application.dto.inventory import InventoryBalance, InventoryCover
from application.dto.sku import SkuDailyRefunds, SkuDailySales
from infrastructure.llm.agent_runtime.tools.business_inspection import (
    BusinessInspectionToolFactory,
)


class SalesRepository:
    def list_sku_daily_sales(self, **kwargs) -> list[SkuDailySales]:
        return [
            SkuDailySales(
                sales_date=kwargs["start_date"],
                sku_id="SKU001",
                channel_account_id=kwargs["channel_account_id"],
                units_sold=3,
                net_sales=Decimal("55"),
                currency_code="USD",
                data_origin="derived_sample",
            )
        ]


class RefundRepository:
    def list_sku_daily_refunds(self, **kwargs) -> list[SkuDailyRefunds]:
        return [
            SkuDailyRefunds(
                refund_date=kwargs["start_date"],
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


class ChannelRepository:
    def list_channel_sales_totals(self, **kwargs) -> list[ChannelSalesTotals]:
        return [
            ChannelSalesTotals(
                channel_account_id="CA_SHOPIFY_US",
                units_sold=3,
                gross_sales=Decimal("60"),
                discount_amount=Decimal("5"),
                net_sales=Decimal("55"),
                currency_code="USD",
            )
        ]


class InventoryRepository:
    def list_inventory_balances(self, **kwargs) -> list[InventoryBalance]:
        return [
            InventoryBalance(
                sku_id="SKU001",
                warehouse_id="WH_US",
                on_hand_qty=10,
                reserved_qty=2,
                blocked_qty=1,
                available_qty=7,
                incoming_qty=4,
                updated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
                data_origin="simulated",
            )
        ]

    def list_inventory_cover(
        self,
        *,
        stock_status: str | None = None,
        limit: int = 1_000,
    ) -> list[InventoryCover]:
        if stock_status != "replenish":
            return []
        return [
            InventoryCover(
                sku_id="SKU001",
                warehouse_id="WH_US",
                available_qty=7,
                inventory_cover_days=3,
                stock_status="replenish",
                snapshot_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
                data_origin="derived_sample",
            )
        ]


class FakeContext(AbstractContextManager[SimpleNamespace]):
    def __init__(self, unit_of_work: SimpleNamespace, counter: list[int]) -> None:
        self._unit_of_work = unit_of_work
        self._counter = counter

    def __enter__(self) -> SimpleNamespace:
        self._counter.append(1)
        return self._unit_of_work

    def __exit__(self, *args) -> None:
        return None


def test_each_tool_uses_existing_services_and_its_own_uow(caplog) -> None:
    uow = SimpleNamespace(
        sales=SalesRepository(),
        refunds=RefundRepository(),
        channel_sales=ChannelRepository(),
        inventory=InventoryRepository(),
    )
    context_entries: list[int] = []
    factory = BusinessInspectionToolFactory(
        lambda: None,
        unit_of_work_factory=lambda: FakeContext(uow, context_entries),
    )
    request = BusinessInspectionRequest(
        frequency="daily",
        channel_account_id="CA_SHOPIFY_US",
        start_date=date(2026, 7, 24),
        end_date=date(2026, 7, 24),
        limit=100,
    )
    tools = factory.build(request, run_id="run-123")

    with caplog.at_level(logging.INFO):
        results = {tool.name: tool.invoke({}) for tool in tools}

    assert len(context_entries) == 4
    assert results["read_sku_sales_snapshot"]["items"][0]["units_sold"] == 3
    assert results["read_sku_sales_snapshot"]["metric_semantics"][0][
        "semantic_id"
    ] == "sku_daily_sales"
    assert results["read_sku_sales_snapshot"]["data_origins"] == [
        "derived_sample"
    ]
    assert results["read_sku_refund_snapshot"]["caveats"][0].endswith(
        "不是退款率。"
    )
    assert results["read_channel_sales_share"]["items"][0][
        "units_share_pct"
    ] == "100.0000"
    inventory = results["read_inventory_snapshot"]
    assert inventory["items"][0]["risks"][0]["stock_status"] == "replenish"
    assert inventory["data_origins"] == ["derived_sample", "simulated"]
    assert caplog.text.count("business_inspection_tool_started") == 4
    assert caplog.text.count("business_inspection_tool_completed") == 4
    assert "run_id=run-123" in caplog.text
