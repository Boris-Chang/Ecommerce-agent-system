from typing import Protocol

from application.dto.overview import (
    OverviewSupplement,
    OverviewSupplementRequest,
)


class OverviewSupplementProvider(Protocol):
    """Supply overview fields whose durable business services are not ready."""

    def get_supplement(
        self,
        request: OverviewSupplementRequest,
    ) -> OverviewSupplement: ...
