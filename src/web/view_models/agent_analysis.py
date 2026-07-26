from dataclasses import dataclass


@dataclass(frozen=True)
class AgentFindingViewModel:
    title: str
    conclusion: str
    reason: str
    severity: str
    severity_label: str
    metric_semantics: tuple[str, ...]
    evidence_ids: tuple[str, ...]


@dataclass(frozen=True)
class AgentEvidenceViewModel:
    evidence_id: str
    tool_name: str
    reason: str
    metric_semantics: tuple[str, ...]
    facts: tuple[str, ...]
    data_as_of: str
    data_origins: tuple[str, ...]
    caveats: tuple[str, ...]


@dataclass(frozen=True)
class AgentAnalysisPageViewModel:
    has_result: bool
    frequency: str
    frequency_label: str
    channel_account_id: str
    channel_account_ids: tuple[str, ...]
    period: str
    run_id: str
    generated_at: str
    summary: str
    findings: tuple[AgentFindingViewModel, ...]
    evidence: tuple[AgentEvidenceViewModel, ...]
    caveats: tuple[str, ...]
    human_review_required: bool
