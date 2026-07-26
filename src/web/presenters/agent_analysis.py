from application.agents.business_inspection.models import (
    BusinessInspectionOutput,
    InspectionReviewSupplement,
)
from application.agents.business_inspection.semantics import (
    METRIC_SEMANTICS_BY_ID,
)
from web.presenters.common import format_timestamp
from web.view_models.agent_analysis import (
    AgentActionViewModel,
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
        review_supplement: InspectionReviewSupplement | None = None,
    ) -> AgentAnalysisPageViewModel:
        evidence = tuple(
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
        )
        evidence_by_id = {
            item.evidence_id: item for item in evidence
        }
        reviews_by_index = {
            item.finding_index: item
            for item in (
                review_supplement.findings
                if review_supplement is not None
                else ()
            )
        }
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
                    tab_id=f"finding-{index}",
                    title=item.title,
                    conclusion=item.conclusion,
                    reason=item.reason,
                    severity=item.severity,
                    severity_label=SEVERITY_LABELS[item.severity],
                    metric_semantics=_semantic_labels(
                        item.metric_semantic_ids
                    ),
                    evidence_ids=item.evidence_ids,
                    evidence=tuple(
                        evidence_by_id[evidence_id]
                        for evidence_id in item.evidence_ids
                        if evidence_id in evidence_by_id
                    ),
                    review_status=(
                        reviews_by_index[index].review_status
                        if index in reviews_by_index
                        else "待审核"
                    ),
                    actions=tuple(
                        AgentActionViewModel(
                            action=action.action,
                            quantity=action.quantity,
                            due_date=action.due_date,
                            status=action.status,
                        )
                        for action in (
                            reviews_by_index[index].actions
                            if index in reviews_by_index
                            else ()
                        )
                    ),
                )
                for index, item in enumerate(output.findings)
            ),
            evidence=evidence,
            caveats=output.caveats,
            human_review_required=output.human_review_required,
        )


def _semantic_labels(semantic_ids: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(
        f"{semantic_id} · {METRIC_SEMANTICS_BY_ID[semantic_id].name}"
        for semantic_id in semantic_ids
    )
