from collections.abc import Callable
from contextlib import AbstractContextManager
from datetime import date, datetime
import logging
from time import monotonic
from typing import Any

from langchain_core.tools import BaseTool, StructuredTool

from application.agents.business_inspection.models import (
    BusinessInspectionRequest,
    MetricSemantic,
)
from application.agents.business_inspection.semantics import (
    METRIC_SEMANTICS_BY_ID,
)
from application.services.channel import ChannelSalesShareService
from application.services.inventory import (
    InventoryBalanceService,
    InventoryRiskService,
)
from application.services.sku import SkuRefundService, SkuSalesService
from infrastructure.database.session import SessionFactory
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork


logger = logging.getLogger(__name__)
UnitOfWorkFactory = Callable[[], AbstractContextManager[Any]]


class BusinessInspectionToolFactory:
    """Bind one inspection scope to read-only tools backed by existing Services."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        unit_of_work_factory: UnitOfWorkFactory | None = None,
    ) -> None:
        self._unit_of_work_factory = unit_of_work_factory or (
            lambda: ReadOnlyUnitOfWork(session_factory)
        )

    def build(
        self,
        request: BusinessInspectionRequest,
        *,
        run_id: str,
    ) -> list[BaseTool]:
        return [
            StructuredTool.from_function(
                func=lambda: self._sales_snapshot(request, run_id),
                name="read_sku_sales_snapshot",
                description=(
                    "读取本次巡检范围内的现有 SKU 每日或每周销售 Service "
                    "结果。无参数，范围已由巡检任务固定。"
                ),
            ),
            StructuredTool.from_function(
                func=lambda: self._refund_snapshot(request, run_id),
                name="read_sku_refund_snapshot",
                description=(
                    "读取本次巡检范围内的现有 SKU 每日或每周退款事实。"
                    "返回退款数量与金额，不返回退款率。"
                ),
            ),
            StructuredTool.from_function(
                func=lambda: self._channel_sales_share(request, run_id),
                name="read_channel_sales_share",
                description=(
                    "读取现有渠道销售占比 Service 结果；占比只在相同币种"
                    "内计算。"
                ),
            ),
            StructuredTool.from_function(
                func=lambda: self._inventory_snapshot(request, run_id),
                name="read_inventory_snapshot",
                description=(
                    "读取现有当前库存余额与库存覆盖风险 Service 结果。"
                    "库存是仓库维度，并非渠道库存。"
                ),
            ),
        ]

    def _sales_snapshot(
        self,
        request: BusinessInspectionRequest,
        run_id: str,
    ) -> dict[str, Any]:
        tool_name = "read_sku_sales_snapshot"

        def query() -> dict[str, Any]:
            with self._unit_of_work_factory() as unit_of_work:
                service = SkuSalesService(unit_of_work.sales)
                if request.frequency == "daily":
                    rows = service.list_daily_sales(
                        channel_account_id=request.channel_account_id,
                        start_date=request.start_date,
                        end_date=request.end_date,
                        limit=request.limit,
                    )
                    semantic_ids = ("sku_daily_sales",)
                    data_as_of = _latest_value(rows, "sales_date")
                else:
                    rows = service.list_weekly_sales(
                        channel_account_id=request.channel_account_id,
                        start_date=request.start_date,
                        end_date=request.end_date,
                        limit=request.limit,
                    )
                    semantic_ids = ("sku_weekly_sales",)
                    data_as_of = _latest_value(rows, "week_start")

            caveats = []
            if request.frequency == "weekly":
                caveats.append(
                    "自然周边界可能是不完整周；Service 未暴露聚合行的数据来源字段。"
                )
            return _payload(
                tool_name=tool_name,
                run_id=run_id,
                request=request,
                semantic_ids=semantic_ids,
                items=[row.model_dump(mode="json") for row in rows],
                data_as_of=data_as_of,
                data_origins=_data_origins(rows),
                caveats=caveats,
            )

        return self._logged_query(tool_name, run_id, query)

    def _refund_snapshot(
        self,
        request: BusinessInspectionRequest,
        run_id: str,
    ) -> dict[str, Any]:
        tool_name = "read_sku_refund_snapshot"

        def query() -> dict[str, Any]:
            with self._unit_of_work_factory() as unit_of_work:
                service = SkuRefundService(unit_of_work.refunds)
                if request.frequency == "daily":
                    rows = service.list_daily_refunds(
                        channel_account_id=request.channel_account_id,
                        start_date=request.start_date,
                        end_date=request.end_date,
                        limit=request.limit,
                    )
                    semantic_ids = ("sku_daily_refunds",)
                    data_as_of = _latest_value(rows, "refund_date")
                else:
                    rows = service.list_weekly_refunds(
                        channel_account_id=request.channel_account_id,
                        start_date=request.start_date,
                        end_date=request.end_date,
                        limit=request.limit,
                    )
                    semantic_ids = ("sku_weekly_refunds",)
                    data_as_of = _latest_value(rows, "week_start")

            return _payload(
                tool_name=tool_name,
                run_id=run_id,
                request=request,
                semantic_ids=semantic_ids,
                items=[row.model_dump(mode="json") for row in rows],
                data_as_of=data_as_of,
                data_origins=(),
                caveats=[
                    "该 Service 返回退款事实而不是退款率。",
                    "该 Service 的 DTO 未暴露数据来源字段。",
                ],
            )

        return self._logged_query(tool_name, run_id, query)

    def _channel_sales_share(
        self,
        request: BusinessInspectionRequest,
        run_id: str,
    ) -> dict[str, Any]:
        tool_name = "read_channel_sales_share"

        def query() -> dict[str, Any]:
            with self._unit_of_work_factory() as unit_of_work:
                rows = ChannelSalesShareService(
                    unit_of_work.channel_sales
                ).list_sales_shares(
                    start_date=request.start_date,
                    end_date=request.end_date,
                )

            return _payload(
                tool_name=tool_name,
                run_id=run_id,
                request=request,
                semantic_ids=("channel_sales_share",),
                items=[row.model_dump(mode="json") for row in rows],
                data_as_of=None,
                data_origins=(),
                caveats=[
                    "渠道占比只能在相同币种内比较。",
                    "该 Service 未暴露数据截至时间和数据来源字段。",
                ],
            )

        return self._logged_query(tool_name, run_id, query)

    def _inventory_snapshot(
        self,
        request: BusinessInspectionRequest,
        run_id: str,
    ) -> dict[str, Any]:
        tool_name = "read_inventory_snapshot"

        def query() -> dict[str, Any]:
            with self._unit_of_work_factory() as unit_of_work:
                balances = InventoryBalanceService(
                    unit_of_work.inventory
                ).list_current_inventory(limit=request.limit)
                risks = InventoryRiskService(
                    unit_of_work.inventory
                ).list_inventory_risks(limit=request.limit)

            balance_as_of = _latest_value(balances, "updated_at")
            risk_as_of = _latest_value(risks, "snapshot_at")
            values = [
                value for value in (balance_as_of, risk_as_of) if value
            ]
            return _payload(
                tool_name=tool_name,
                run_id=run_id,
                request=request,
                semantic_ids=(
                    "current_inventory_balance",
                    "inventory_cover_risk",
                ),
                items=[
                    {
                        "balances": [
                            row.model_dump(mode="json") for row in balances
                        ],
                        "risks": [
                            row.model_dump(mode="json") for row in risks
                        ],
                    }
                ],
                data_as_of=max(values) if values else None,
                data_origins=(
                    *_data_origins(balances),
                    *_data_origins(risks),
                ),
                caveats=[
                    "库存 Service 是 SKU × 仓库范围，不按销售渠道拆分。",
                    "覆盖天数与 stock_status 来自已有库存覆盖快照，"
                    "本工具没有重新预测或计算。",
                ],
            )

        return self._logged_query(tool_name, run_id, query)

    @staticmethod
    def _logged_query(
        tool_name: str,
        run_id: str,
        query: Callable[[], dict[str, Any]],
    ) -> dict[str, Any]:
        started_at = monotonic()
        logger.info(
            "business_inspection_tool_started run_id=%s tool=%s",
            run_id,
            tool_name,
        )
        try:
            payload = query()
        except Exception:
            logger.exception(
                "business_inspection_tool_failed run_id=%s tool=%s",
                run_id,
                tool_name,
            )
            raise
        logger.info(
            "business_inspection_tool_completed run_id=%s tool=%s "
            "row_count=%s duration_ms=%d",
            run_id,
            tool_name,
            payload["row_count"],
            round((monotonic() - started_at) * 1_000),
        )
        return payload


def _payload(
    *,
    tool_name: str,
    run_id: str,
    request: BusinessInspectionRequest,
    semantic_ids: tuple[str, ...],
    items: list[dict[str, Any]],
    data_as_of: str | None,
    data_origins: tuple[str, ...],
    caveats: list[str],
) -> dict[str, Any]:
    row_count = _item_count(items)
    return {
        "status": "ok" if row_count else "empty",
        "run_id": run_id,
        "tool_name": tool_name,
        "scope": {
            "frequency": request.frequency,
            "channel_account_id": request.channel_account_id,
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
        },
        "metric_semantics": [
            _semantic_payload(METRIC_SEMANTICS_BY_ID[semantic_id])
            for semantic_id in semantic_ids
        ],
        "data_as_of": data_as_of,
        "data_origins": sorted(set(data_origins)),
        "row_count": row_count,
        "truncated": None,
        "items": items,
        "caveats": [
            *caveats,
            (
                "现有 Service 使用行数上限，但不返回总行数；"
                "因此无法判断结果是否被截断。"
            ),
        ],
    }


def _semantic_payload(semantic: MetricSemantic) -> dict[str, str]:
    return semantic.model_dump(mode="json")


def _latest_value(rows: list[Any], field: str) -> str | None:
    values: list[date | datetime] = [
        value
        for row in rows
        if (value := getattr(row, field, None)) is not None
    ]
    if not values:
        return None
    return max(values).isoformat()


def _data_origins(rows: list[Any]) -> tuple[str, ...]:
    return tuple(
        origin
        for row in rows
        if (origin := getattr(row, "data_origin", None))
    )


def _item_count(items: list[dict[str, Any]]) -> int:
    if len(items) == 1 and set(items[0]) == {"balances", "risks"}:
        return len(items[0]["balances"]) + len(items[0]["risks"])
    return len(items)
