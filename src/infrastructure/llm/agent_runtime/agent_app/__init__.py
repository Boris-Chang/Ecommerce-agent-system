"""Composition facade for the business inspection Agent."""

from infrastructure.llm.agent_runtime.agent_app.service import (
    create_business_inspection_service,
)

__all__ = ["create_business_inspection_service"]
