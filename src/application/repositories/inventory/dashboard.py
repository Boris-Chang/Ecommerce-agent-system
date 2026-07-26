from typing import Protocol

from application.dto.inventory.dashboard import (
    InventoryDashboardSupplement,
    InventoryDashboardSupplementRequest,
)


class InventoryDashboardSupplementProvider(Protocol):
    def get_supplement(
        self,
        request: InventoryDashboardSupplementRequest,
    ) -> InventoryDashboardSupplement: ...
