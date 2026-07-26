from collections.abc import Callable
from datetime import datetime, timezone
import json
import logging
from typing import Any

from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy

from application.agents.business_inspection.models import (
    BusinessInspectionOutput,
    BusinessInspectionRequest,
)
from application.agents.business_inspection.semantics import METRIC_SEMANTICS
from infrastructure.llm.agent_runtime.tools.business_inspection import (
    BusinessInspectionToolFactory,
)
from infrastructure.database.session import SessionFactory
from infrastructure.llm.models.llm_provider import build_llm


logger = logging.getLogger(__name__)
AgentFactory = Callable[..., Any]
ModelFactory = Callable[[], Any]


SYSTEM_PROMPT = """
你是电商经营数据巡检 Agent，不是对话助手。

业务边界：
1. 你只执行一次固定范围的销售、退款、渠道占比和库存巡检。
2. 必须调用提供的四个只读工具，不能跳过工具，不能请求用户补充问题。
3. 只能使用工具返回的现有 Application Service 数据和指标语义。
4. 不得创造新指标、阈值、比率、趋势算法或预测规则。
5. 不得计算退款率、利润、LTV、跨币种合计或库存与渠道的归属关系。
6. 库存风险结论只能引用已有 inventory_cover_risk 的 stock_status 和覆盖快照。
7. 每项 finding 必须写明具体理由，引用 evidence_id 和 metric_semantic_id。
8. evidence.facts 必须是工具结果中的具体事实，不得编造数据。
9. evidence 必须原样保留工具返回的 data_as_of、data_origins 和 caveats。
10. 数据不足时写入 caveats，不得用常识补齐。
11. 所有建议仅供人工复核，不执行任何写操作。

输出要求：
- 返回 BusinessInspectionOutput 结构化结果。
- evidence_id 使用 E1、E2 等稳定编号。
- metric_semantic_ids 只能使用工具返回的 semantic_id。
- finding.reason 明确说明采用了哪个统一指标语义，以及该事实为什么支持结论。
- human_review_required 必须为 true。
"""


class LangChainBusinessInspectionRunner:
    """Stateless LangChain adapter for one scheduled/manual inspection."""

    def __init__(
        self,
        session_factory: SessionFactory,
        *,
        model_factory: ModelFactory = build_llm,
        agent_factory: AgentFactory = create_agent,
    ) -> None:
        self._tool_factory = BusinessInspectionToolFactory(session_factory)
        self._model_factory = model_factory
        self._agent_factory = agent_factory

    def run(
        self,
        request: BusinessInspectionRequest,
        *,
        run_id: str,
    ) -> BusinessInspectionOutput:
        tools = self._tool_factory.build(request, run_id=run_id)
        logger.info(
            "business_inspection_runner_started run_id=%s tools=%s",
            run_id,
            ",".join(tool.name for tool in tools),
        )
        agent = self._agent_factory(
            model=self._model_factory(),
            tools=tools,
            system_prompt=SYSTEM_PROMPT,
            response_format=ToolStrategy(BusinessInspectionOutput),
            name="business_inspection_agent",
        )
        result = agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": _inspection_task(request, run_id),
                    }
                ]
            },
            config={"recursion_limit": 20},
        )
        called_tools = _called_tool_names(result)
        required_tools = {tool.name for tool in tools}
        missing_tools = required_tools - called_tools
        if missing_tools:
            raise ValueError(
                "Business inspection Agent skipped required tools: "
                f"{sorted(missing_tools)}"
            )
        structured = result.get("structured_response")
        if structured is None:
            raise ValueError(
                "Business inspection Agent returned no structured_response."
            )
        output = BusinessInspectionOutput.model_validate(structured)
        unknown_evidence_tools = {
            evidence.tool_name for evidence in output.evidence
        } - called_tools
        if unknown_evidence_tools:
            raise ValueError(
                "Business inspection evidence references tools that were "
                f"not called: {sorted(unknown_evidence_tools)}"
            )
        logger.info(
            "business_inspection_runner_completed run_id=%s called_tools=%s",
            run_id,
            ",".join(sorted(called_tools)),
        )
        return output


def _inspection_task(
    request: BusinessInspectionRequest,
    run_id: str,
) -> str:
    semantics = [
        item.model_dump(mode="json") for item in METRIC_SEMANTICS
    ]
    return (
        "执行一次固定巡检，不进行对话。\n"
        f"run_id: {run_id}\n"
        f"frequency: {request.frequency}\n"
        f"channel_account_id: {request.channel_account_id}\n"
        f"start_date: {request.start_date.isoformat()}\n"
        f"end_date: {request.end_date.isoformat()}\n"
        "必须依次调用全部四个工具，并基于返回数据生成结构化结论。\n"
        "允许引用的统一指标语义目录：\n"
        f"{json.dumps(semantics, ensure_ascii=False)}\n"
        f"generated_at: {datetime.now(timezone.utc).isoformat()}"
    )


def _called_tool_names(result: dict[str, Any]) -> set[str]:
    names: set[str] = set()
    for message in result.get("messages") or ():
        if isinstance(message, dict):
            if message.get("role") == "tool" and message.get("name"):
                names.add(str(message["name"]))
            continue
        if getattr(message, "type", None) == "tool":
            name = getattr(message, "name", None)
            if name:
                names.add(str(name))
    return names
