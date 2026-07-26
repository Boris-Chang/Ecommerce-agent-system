import logging
from time import monotonic
from uuid import uuid4

from application.agents.business_inspection.models import (
    BusinessInspectionOutput,
    BusinessInspectionRequest,
)
from application.agents.business_inspection.ports import BusinessInspectionRunner
from application.agents.business_inspection.semantics import (
    METRIC_SEMANTICS_BY_ID,
)


logger = logging.getLogger(__name__)


class BusinessInspectionService:
    """Run one stateless inspection and enforce traceability contracts."""

    def __init__(self, runner: BusinessInspectionRunner) -> None:
        self._runner = runner

    def run(
        self,
        request: BusinessInspectionRequest,
    ) -> BusinessInspectionOutput:
        run_id = str(uuid4())
        started_at = monotonic()
        logger.info(
            "business_inspection_started run_id=%s frequency=%s channel=%s "
            "start_date=%s end_date=%s",
            run_id,
            request.frequency,
            request.channel_account_id,
            request.start_date,
            request.end_date,
        )
        try:
            raw_output = self._runner.run(request, run_id=run_id)
            output = raw_output.model_copy(
                update={
                    "run_id": run_id,
                    "frequency": request.frequency,
                    "channel_account_id": request.channel_account_id,
                    "start_date": request.start_date,
                    "end_date": request.end_date,
                    "human_review_required": True,
                }
            )
            _validate_traceability(output)
        except Exception:
            logger.exception(
                "business_inspection_failed run_id=%s frequency=%s channel=%s",
                run_id,
                request.frequency,
                request.channel_account_id,
            )
            raise

        logger.info(
            "business_inspection_completed run_id=%s findings=%d evidence=%d "
            "duration_ms=%d",
            run_id,
            len(output.findings),
            len(output.evidence),
            round((monotonic() - started_at) * 1_000),
        )
        return output


def _validate_traceability(output: BusinessInspectionOutput) -> None:
    evidence_by_id = {
        item.evidence_id: item for item in output.evidence
    }
    if len(evidence_by_id) != len(output.evidence):
        raise ValueError("Agent evidence_id values must be unique.")

    known_semantics = set(METRIC_SEMANTICS_BY_ID)
    for evidence in output.evidence:
        unknown = set(evidence.metric_semantic_ids) - known_semantics
        if unknown:
            raise ValueError(
                f"Agent evidence references unknown metric semantics: "
                f"{sorted(unknown)}"
            )

    for finding in output.findings:
        missing_evidence = set(finding.evidence_ids) - set(evidence_by_id)
        if missing_evidence:
            raise ValueError(
                f"Agent finding references missing evidence: "
                f"{sorted(missing_evidence)}"
            )
        unknown_semantics = set(finding.metric_semantic_ids) - known_semantics
        if unknown_semantics:
            raise ValueError(
                f"Agent finding references unknown metric semantics: "
                f"{sorted(unknown_semantics)}"
            )
        cited_semantics = {
            semantic_id
            for evidence_id in finding.evidence_ids
            for semantic_id in evidence_by_id[
                evidence_id
            ].metric_semantic_ids
        }
        uncited_semantics = (
            set(finding.metric_semantic_ids) - cited_semantics
        )
        if uncited_semantics:
            raise ValueError(
                "Agent finding semantics must be supported by its evidence: "
                f"{sorted(uncited_semantics)}"
            )
