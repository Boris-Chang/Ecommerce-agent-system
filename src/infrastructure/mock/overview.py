from decimal import Decimal, ROUND_HALF_UP

from application.dto.overview import (
    OverviewInsight,
    OverviewSupplement,
    OverviewSupplementRequest,
)


TWO_PLACES = Decimal("0.01")
FOUR_PLACES = Decimal("0.0001")
CHANNEL_MARGIN_WEIGHTS = {
    "CA_SHOPIFY_US": Decimal("0.62"),
    "CA_AMAZON_US": Decimal("0.44"),
}


class FixedOverviewSupplementProvider:
    """Deterministic development adapter for not-yet-served overview fields."""

    def get_supplement(
        self,
        request: OverviewSupplementRequest,
    ) -> OverviewSupplement:
        profit_share = _profit_shares(request)
        forecasts = {
            sku_id: (Decimal(units) * Decimal("4.20")).quantize(
                TWO_PLACES,
                rounding=ROUND_HALF_UP,
            )
            for sku_id, units in request.top_sku_units
        }
        return OverviewSupplement(
            gross_profit_share_pct=profit_share,
            forecast_4w_p50=forecasts,
            insights=_build_insights(request),
            data_source="fixed_overview_supplement_v1",
        )

def _profit_shares(
    request: OverviewSupplementRequest,
) -> dict[str, Decimal]:
    weights = {
        request.channel_account_id: CHANNEL_MARGIN_WEIGHTS.get(
            request.channel_account_id,
            Decimal("0.50"),
        )
    }
    total = sum(weights.values(), Decimal("0"))
    if total == 0:
        return {channel_id: Decimal("0") for channel_id in weights}
    return {
        channel_id: ((weight / total) * Decimal("100")).quantize(
            FOUR_PLACES,
            rounding=ROUND_HALF_UP,
        )
        for channel_id, weight in weights.items()
    }


def _build_insights(
    request: OverviewSupplementRequest,
) -> tuple[OverviewInsight, ...]:
    insights: list[OverviewInsight] = []
    if request.replenishment_skus:
        sku_id = request.replenishment_skus[0]
        insights.append(
            OverviewInsight(
                category="补货",
                severity="high",
                title=f"{sku_id} 进入补货关注清单",
                detail=(
                    f"当前共有 {len(request.replenishment_skus)} 个 SKU "
                    "被库存快照标记为 replenish，请结合在途数量人工确认。"
                ),
                href="/inventory",
            )
        )
    if request.top_sku_units:
        sku_id, units = request.top_sku_units[0]
        insights.append(
            OverviewInsight(
                category="销售",
                severity="medium",
                title=f"{sku_id} 是当前销量最高的 SKU",
                detail=(
                    f"所选周期销量为 {units} 件，建议结合退款率与库存覆盖"
                    "继续检查销售质量。"
                ),
                href="/sales",
            )
        )
    if request.overstock_skus:
        insights.append(
            OverviewInsight(
                category="呆滞",
                severity="medium",
                title=f"{len(request.overstock_skus)} 个 SKU 存在积压风险",
                detail="库存覆盖偏高，建议进入库存优化候选清单。",
                href="/inventory",
            )
        )
    if not insights:
        insights.append(
            OverviewInsight(
                category="巡检",
                severity="info",
                title="当前没有聚合出高优先级风险",
                detail="可进入 Agent 分析页运行一次最新业务巡检。",
                href="/agent-analysis",
            )
        )
    return tuple(insights[:3])
