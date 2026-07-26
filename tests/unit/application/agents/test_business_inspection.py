from datetime import date, datetime, timezone
import logging

import pytest

from application.agents.business_inspection import (
    BusinessInspectionFinding,
    BusinessInspectionOutput,
    BusinessInspectionRequest,
    BusinessInspectionService,
    InspectionEvidence,
)


def _request() -> BusinessInspectionRequest:
    return BusinessInspectionRequest(
        frequency="daily",
        channel_account_id="CA_SHOPIFY_US",
        start_date=date(2026, 7, 24),
        end_date=date(2026, 7, 24),
    )


def _output(
    *,
    semantic_id: str = "sku_daily_sales",
    evidence_ids: tuple[str, ...] = ("E1",),
) -> BusinessInspectionOutput:
    return BusinessInspectionOutput(
        run_id="model-supplied-id",
        frequency="weekly",
        channel_account_id="wrong-channel",
        start_date=date(2020, 1, 1),
        end_date=date(2020, 1, 2),
        generated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
        summary="销售巡检完成。",
        findings=(
            BusinessInspectionFinding(
                title="SKU 销售事实",
                conclusion="SKU001 有销售记录。",
                reason="采用 sku_daily_sales 语义并引用 E1。",
                severity="info",
                metric_semantic_ids=(semantic_id,),
                evidence_ids=evidence_ids,
            ),
        ),
        evidence=(
            InspectionEvidence(
                evidence_id="E1",
                tool_name="read_sku_sales_snapshot",
                metric_semantic_ids=("sku_daily_sales",),
                reason="现有 SkuSalesService 返回一条记录。",
                facts=("SKU001 units_sold=3",),
            ),
        ),
        human_review_required=False,
    )


class FakeRunner:
    def __init__(self, output: BusinessInspectionOutput) -> None:
        self.output = output
        self.calls: list[tuple[BusinessInspectionRequest, str]] = []

    def run(
        self,
        request: BusinessInspectionRequest,
        *,
        run_id: str,
    ) -> BusinessInspectionOutput:
        self.calls.append((request, run_id))
        return self.output


def test_service_owns_scope_run_id_and_trace_log(caplog) -> None:
    runner = FakeRunner(_output())
    service = BusinessInspectionService(runner)

    with caplog.at_level(logging.INFO):
        result = service.run(_request())

    assert result.run_id != "model-supplied-id"
    assert result.frequency == "daily"
    assert result.channel_account_id == "CA_SHOPIFY_US"
    assert result.start_date == date(2026, 7, 24)
    assert result.human_review_required is True
    assert runner.calls[0][1] == result.run_id
    assert "business_inspection_started" in caplog.text
    assert "business_inspection_completed" in caplog.text
    assert result.run_id in caplog.text


def test_service_rejects_missing_evidence_reference() -> None:
    service = BusinessInspectionService(
        FakeRunner(_output(evidence_ids=("E404",)))
    )

    with pytest.raises(ValueError, match="missing evidence"):
        service.run(_request())


def test_service_rejects_unknown_metric_semantic() -> None:
    service = BusinessInspectionService(
        FakeRunner(_output(semantic_id="model_invented_metric"))
    )

    with pytest.raises(ValueError, match="unknown metric semantics"):
        service.run(_request())
