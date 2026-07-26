from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


InspectionFrequency = Literal["daily", "weekly"]
FindingSeverity = Literal["high", "medium", "low", "info"]


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class BusinessInspectionRequest(FrozenModel):
    """Caller-controlled scope for one stateless inspection run."""

    frequency: InspectionFrequency
    channel_account_id: str = Field(min_length=1)
    start_date: date
    end_date: date
    limit: int = Field(default=100, ge=1, le=500)

    def model_post_init(self, __context: object) -> None:
        if self.start_date > self.end_date:
            raise ValueError("start_date must not be after end_date.")


class MetricSemantic(FrozenModel):
    """Traceable description of an existing deterministic Application metric."""

    semantic_id: str
    name: str
    definition: str
    application_service: str


class InspectionEvidence(FrozenModel):
    evidence_id: str
    tool_name: str
    metric_semantic_ids: tuple[str, ...] = Field(min_length=1)
    reason: str = Field(min_length=1)
    facts: tuple[str, ...] = Field(min_length=1)
    data_as_of: str | None = None
    data_origins: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()


class BusinessInspectionFinding(FrozenModel):
    title: str
    conclusion: str
    reason: str
    severity: FindingSeverity
    metric_semantic_ids: tuple[str, ...] = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(min_length=1)


class BusinessInspectionOutput(FrozenModel):
    run_id: str
    frequency: InspectionFrequency
    channel_account_id: str
    start_date: date
    end_date: date
    generated_at: datetime
    summary: str
    findings: tuple[BusinessInspectionFinding, ...]
    evidence: tuple[InspectionEvidence, ...]
    caveats: tuple[str, ...] = ()
    human_review_required: bool = True


class InspectionReviewAction(FrozenModel):
    action: str
    quantity: str = "—"
    due_date: str = "待确认"
    status: str = "待人工执行"


class InspectionFindingReview(FrozenModel):
    finding_index: int = Field(ge=0)
    review_status: str
    actions: tuple[InspectionReviewAction, ...] = ()


class InspectionReviewSupplement(FrozenModel):
    findings: tuple[InspectionFindingReview, ...]
    data_source: str
