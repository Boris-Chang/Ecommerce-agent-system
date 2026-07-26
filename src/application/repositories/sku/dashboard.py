from typing import Protocol

from application.dto.sku.dashboard import (
    SkuDashboardSupplement,
    SkuDashboardSupplementRequest,
)


class SkuDashboardSupplementProvider(Protocol):
    def get_supplement(
        self,
        request: SkuDashboardSupplementRequest,
    ) -> SkuDashboardSupplement: ...
