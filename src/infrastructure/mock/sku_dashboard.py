from application.dto.sku.dashboard import (
    SkuDashboardSupplement,
    SkuDashboardSupplementRequest,
)


class FixedSkuDashboardSupplementProvider:
    """Temporary catalog coverage until product listing metrics are served."""

    def get_supplement(
        self,
        request: SkuDashboardSupplementRequest,
    ) -> SkuDashboardSupplement:
        listed_skus = max(request.active_skus + 62, 246)
        return SkuDashboardSupplement(
            listed_skus=listed_skus,
            slow_moving_skus=max(0, listed_skus - request.active_skus),
            data_source="fixed_sku_catalog_metrics_v1",
        )
