from datetime import date, datetime, timezone

from application.agents.business_inspection import (
    BusinessInspectionFinding,
    BusinessInspectionOutput,
    BusinessInspectionRequest,
    InspectionEvidence,
)
from infrastructure.llm.agent_runtime.agents.business_inspection_agent import (
    LangChainBusinessInspectionRunner,
)
from langchain.agents.structured_output import ToolStrategy


class FakeAgent:
    def __init__(self, output: BusinessInspectionOutput) -> None:
        self.output = output
        self.calls: list[tuple[dict, dict]] = []

    def invoke(self, payload: dict, config: dict) -> dict:
        self.calls.append((payload, config))
        return {
            "messages": [
                {"role": "tool", "name": name}
                for name in (
                    "read_sku_sales_snapshot",
                    "read_sku_refund_snapshot",
                    "read_channel_sales_share",
                    "read_inventory_snapshot",
                )
            ],
            "structured_response": self.output,
        }


def test_runner_builds_stateless_four_tool_inspection() -> None:
    output = BusinessInspectionOutput(
        run_id="run-123",
        frequency="daily",
        channel_account_id="CA_SHOPIFY_US",
        start_date=date(2026, 7, 24),
        end_date=date(2026, 7, 24),
        generated_at=datetime(2026, 7, 24, tzinfo=timezone.utc),
        summary="完成。",
        findings=(
            BusinessInspectionFinding(
                title="销售事实",
                conclusion="存在销售记录。",
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
                reason="SkuSalesService 返回记录。",
                facts=("SKU001 units_sold=3",),
            ),
        ),
    )
    fake_agent = FakeAgent(output)
    captured: dict = {}

    def agent_factory(**kwargs):
        captured.update(kwargs)
        return fake_agent

    runner = LangChainBusinessInspectionRunner(
        lambda: None,
        model_factory=lambda: "fake-model",
        agent_factory=agent_factory,
    )
    request = BusinessInspectionRequest(
        frequency="daily",
        channel_account_id="CA_SHOPIFY_US",
        start_date=date(2026, 7, 24),
        end_date=date(2026, 7, 24),
    )

    result = runner.run(request, run_id="run-123")

    assert result == output
    assert captured["model"] == "fake-model"
    assert isinstance(captured["response_format"], ToolStrategy)
    assert captured["response_format"].schema is BusinessInspectionOutput
    assert [tool.name for tool in captured["tools"]] == [
        "read_sku_sales_snapshot",
        "read_sku_refund_snapshot",
        "read_channel_sales_share",
        "read_inventory_snapshot",
    ]
    task = fake_agent.calls[0][0]["messages"][0]["content"]
    assert "不进行对话" in task
    assert "必须依次调用全部四个工具" in task
    assert "run-123" in task
    assert fake_agent.calls[0][1] == {"recursion_limit": 20}
