from datetime import date, datetime, time, timezone

from application.agents.business_inspection import (
    BusinessInspectionFinding,
    BusinessInspectionOutput,
    InspectionEvidence,
    InspectionFindingReview,
    InspectionReviewAction,
    InspectionReviewSupplement,
)


class FixedInspectionReviewProvider:
    """Preview and review metadata until review persistence is implemented."""

    def get_preview(
        self,
        *,
        channel_account_id: str,
        generated_on: date,
    ) -> BusinessInspectionOutput:
        generated_at = datetime.combine(
            generated_on,
            time(hour=8, minute=40),
            tzinfo=timezone.utc,
        )
        return BusinessInspectionOutput(
            run_id=f"PREVIEW-{generated_on:%Y%m%d}",
            frequency="weekly",
            channel_account_id=channel_account_id,
            start_date=generated_on,
            end_date=generated_on,
            generated_at=generated_at,
            summary="当前共有 3 项经营风险需要按优先级进行人工复核。",
            findings=(
                BusinessInspectionFinding(
                    title="SKU 补货风险",
                    conclusion="CC-TEE-BLK-M 预计 9 天内断货。",
                    reason=(
                        "库存覆盖低于补货前置期，且当前没有足够在途库存。"
                    ),
                    severity="high",
                    metric_semantic_ids=("inventory_cover_risk",),
                    evidence_ids=("E1", "E2"),
                ),
                BusinessInspectionFinding(
                    title="SKU 退款异常",
                    conclusion="CC-HOOD-NVY-L 件数退款率升至 9.4%。",
                    reason="退款主要集中在尺码不符，应检查商品尺码信息。",
                    severity="medium",
                    metric_semantic_ids=("sku_daily_refunds",),
                    evidence_ids=("E3",),
                ),
                BusinessInspectionFinding(
                    title="库存呆滞风险",
                    conclusion="4 个 SKU 的库存覆盖天数超过 120 天。",
                    reason="高覆盖库存形成资金占压，需要进入清仓候选清单。",
                    severity="medium",
                    metric_semantic_ids=("inventory_cover_risk",),
                    evidence_ids=("E4",),
                ),
            ),
            evidence=(
                InspectionEvidence(
                    evidence_id="E1",
                    tool_name="read_inventory_snapshot",
                    metric_semantic_ids=("inventory_cover_risk",),
                    reason="读取库存覆盖和当前可售、在途数量。",
                    facts=("可售 632", "在途 0", "覆盖 9 天"),
                    data_as_of=generated_on.isoformat(),
                    data_origins=("analytics.v_inventory_cover",),
                ),
                InspectionEvidence(
                    evidence_id="E2",
                    tool_name="forecast_sku_weekly_demand",
                    metric_semantic_ids=("inventory_cover_risk",),
                    reason="读取 SKU 周需求预测。",
                    facts=("P50 周需求 490", "P90 周需求 620"),
                    data_as_of=generated_on.isoformat(),
                    data_origins=("sku_weighted_moving_average:v0.1",),
                ),
                InspectionEvidence(
                    evidence_id="E3",
                    tool_name="read_sku_refunds",
                    metric_semantic_ids=("sku_daily_refunds",),
                    reason="读取 SKU 退款件数与原因。",
                    facts=("件数退款率 9.4%", "主要原因：尺码不符"),
                    data_as_of=generated_on.isoformat(),
                    data_origins=("analytics.v_sku_daily_refunds",),
                ),
                InspectionEvidence(
                    evidence_id="E4",
                    tool_name="read_inventory_snapshot",
                    metric_semantic_ids=("inventory_cover_risk",),
                    reason="读取高覆盖库存快照。",
                    facts=("4 个 SKU 覆盖超过 120 天",),
                    data_as_of=generated_on.isoformat(),
                    data_origins=("analytics.v_inventory_cover",),
                ),
            ),
            caveats=("所有建议动作必须由人工在对应业务系统中执行。",),
        )

    def get_supplement(
        self,
        output: BusinessInspectionOutput,
    ) -> InspectionReviewSupplement:
        reviews = []
        for index, finding in enumerate(output.findings):
            reviews.append(
                InspectionFindingReview(
                    finding_index=index,
                    review_status=(
                        "待审核" if index < 2 else "已采纳"
                    ),
                    actions=_actions_for(finding, index),
                )
            )
        return InspectionReviewSupplement(
            findings=tuple(reviews),
            data_source="fixed_inspection_review_workflow_v1",
        )


def _actions_for(
    finding: BusinessInspectionFinding,
    index: int,
) -> tuple[InspectionReviewAction, ...]:
    if index == 0:
        return (
            InspectionReviewAction(
                action="向工厂提交补货单并人工确认交期",
                quantity="2,000",
                due_date="今天",
            ),
            InspectionReviewAction(
                action="检查并调整该 SKU 的广告投放",
                due_date="下一工作日",
            ),
        )
    if index == 1:
        return (
            InspectionReviewAction(
                action="复核主要退款原因并更新尺码说明",
                due_date="3 个工作日内",
            ),
        )
    return (
        InspectionReviewAction(
            action=f"将“{finding.title}”涉及 SKU 加入清理候选",
            due_date="本周",
        ),
    )
