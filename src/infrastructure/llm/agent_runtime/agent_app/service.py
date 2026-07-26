from collections.abc import Callable

from application.agents.business_inspection.ports import (
    BusinessInspectionRunner,
)
from application.agents.business_inspection.service import (
    BusinessInspectionService,
)
from infrastructure.llm.agent_runtime.agents.business_inspection_agent import (
    LangChainBusinessInspectionRunner,
)
from infrastructure.database.session import SessionFactory


RunnerFactory = Callable[[SessionFactory], BusinessInspectionRunner]


def create_business_inspection_service(
    session_factory: SessionFactory,
    *,
    runner_factory: RunnerFactory = LangChainBusinessInspectionRunner,
) -> BusinessInspectionService:
    """Composition root for Web, schedulers, workers and tests."""
    return BusinessInspectionService(runner_factory(session_factory))
