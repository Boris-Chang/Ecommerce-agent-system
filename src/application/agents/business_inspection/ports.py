from typing import Protocol

from application.agents.business_inspection.models import (
    BusinessInspectionOutput,
    BusinessInspectionRequest,
)


class BusinessInspectionRunner(Protocol):
    """LLM runtime port used by the deterministic inspection use case."""

    def run(
        self,
        request: BusinessInspectionRequest,
        *,
        run_id: str,
    ) -> BusinessInspectionOutput: ...
