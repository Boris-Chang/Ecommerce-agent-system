from application.agents.business_inspection.models import (
    BusinessInspectionOutput,
)
from application.agents.business_inspection.semantics import (
    METRIC_SEMANTICS_BY_ID,
)
from web.presenters.common import format_timestamp
from web.view_models.agent_analysis import (
    AgentAnalysisPageViewModel,
    AgentEvidenceViewModel,
    AgentFindingViewModel,
)


FREQUENCY_LABELS = {"daily": "每日巡检", "weekly": "每周巡检"}
SEVERITY_LABELS = {
    "high": "高优先级",
    "medium": "中优先级",
    "low": "低优先级",
    "info": "提示",
}


class AgentAnalysisPresenter:
    @staticmethod
    def empty_page(
        *,
        frequency: str,
        channel_account_id: str,
        channel_account_ids: tuple[str, ...],
    ) -> AgentAnalysisPageViewModel:
        return AgentAnalysisPageViewModel(
            has_result=False,
            frequency=frequency,
            frequency_label=FREQUENCY_LABELS[frequency],
            channel_account_id=channel_account_id,
            channel_account_ids=channel_account_ids,
            period="—",
            run_id="—",
            generated_at="—",
            summary="",
            findings=(),
            evidence=(),
            caveats=(),
            human_review_required=True,
        )

    @staticmethod
    def to_page(
        output: BusinessInspectionOutput,
        *,
        channel_account_ids: tuple[str, ...],
    ) -> AgentAnalysisPageViewModel:
        return AgentAnalysisPageViewModel(
            has_result=True,
            frequency=output.frequency,
            frequency_label=FREQUENCY_LABELS[output.frequency],
            channel_account_id=output.channel_account_id,
            channel_account_ids=channel_account_ids,
            period=(
                f"{output.start_date.isoformat()} 至 "
                f"{output.end_date.isoformat()}"
            ),
            run_id=output.run_id,
            generated_at=format_timestamp(output.generated_at),
            summary=output.summary,
            findings=tuple(
                AgentFindingViewModel(
                    title=item.title,
                    conclusion=item.conclusion,
                    reason=item.reason,
                    severity=item.severity,
                    severity_label=SEVERITY_LABELS[item.severity],
                    metric_semantics=_semantic_labels(
                        item.metric_semantic_ids
                    ),
                    evidence_ids=item.evidence_ids,
                )
                for item in output.findings
            ),
            evidence=tuple(
                AgentEvidenceViewModel(
                    evidence_id=item.evidence_id,
                    tool_name=item.tool_name,
                    reason=item.reason,
                    metric_semantics=_semantic_labels(
                        item.metric_semantic_ids
                    ),
                    facts=item.facts,
                    data_as_of=item.data_as_of or "未由 Service 暴露",
                    data_origins=item.data_origins,
                    caveats=item.caveats,
                )
                for item in output.evidence
            ),
            caveats=output.caveats,
            human_review_required=output.human_review_required,
        )


def _semantic_labels(semantic_ids: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        f"{semantic_id} · {METRIC_SEMANTICS_BY_ID[semantic_id].name}"
        for semantic_id in semantic_ids
    )
