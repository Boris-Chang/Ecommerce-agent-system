from datetime import date
from typing import Protocol

from application.agents.business_inspection.models import (
    BusinessInspectionOutput,
    BusinessInspectionRequest,
    InspectionReviewSupplement,
)


class BusinessInspectionRunner(Protocol):
    """LLM runtime port used by the deterministic inspection use case."""

    def run(
        self,
        request: BusinessInspectionRequest,
        *,
        run_id: str,
    ) -> BusinessInspectionOutput: ...


class InspectionReviewProvider(Protocol):
    def get_preview(
        self,
        *,
        channel_account_id: str,
        generated_on: date,
    ) -> BusinessInspectionOutput: ...

    def get_supplement(
        self,
        output: BusinessInspectionOutput,
    ) -> InspectionReviewSupplement: ...
