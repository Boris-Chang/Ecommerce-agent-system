from application.agents.business_inspection.models import MetricSemantic


METRIC_SEMANTICS = (
    MetricSemantic(
        semantic_id="sku_daily_sales",
        name="SKU 每日销售",
        definition=(
            "SkuSalesService 按渠道、销售日和 SKU 返回订单量、销售数量、"
            "销售额、折扣额与净销售额；数据值来自现有销售分析读模型。"
        ),
        application_service="application.services.sku.SkuSalesService",
    ),
    MetricSemantic(
        semantic_id="sku_weekly_sales",
        name="SKU 每周销售",
        definition=(
            "SkuSalesService 返回按自然周、渠道和 SKU 汇总的订单量、"
            "销售数量、销售额、折扣额与净销售额；边界周可能不是完整周。"
        ),
        application_service="application.services.sku.SkuSalesService",
    ),
    MetricSemantic(
        semantic_id="sku_daily_refunds",
        name="SKU 每日退款事实",
        definition=(
            "SkuRefundService 按渠道、退款日和 SKU 返回退款笔数、"
            "退款订单数、退款件数及退款金额；它不是退款率。"
        ),
        application_service="application.services.sku.SkuRefundService",
    ),
    MetricSemantic(
        semantic_id="sku_weekly_refunds",
        name="SKU 每周退款事实",
        definition=(
            "SkuRefundService 按自然周、渠道和 SKU 返回退款笔数、"
            "退款订单数、退款件数及退款金额；它不是退款率。"
        ),
        application_service="application.services.sku.SkuRefundService",
    ),
    MetricSemantic(
        semantic_id="channel_sales_share",
        name="渠道销售占比",
        definition=(
            "ChannelSalesShareService 只在相同币种内计算渠道销售件数占比"
            "和净销售额占比：渠道值 ÷ 同币种全部渠道合计 × 100%。"
        ),
        application_service=(
            "application.services.channel.ChannelSalesShareService"
        ),
    ),
    MetricSemantic(
        semantic_id="current_inventory_balance",
        name="当前库存余额",
        definition=(
            "InventoryBalanceService 按 SKU 和仓库返回数据库中的在库、"
            "预占、冻结、可售与在途数量；服务不重新计算这些字段。"
        ),
        application_service=(
            "application.services.inventory.InventoryBalanceService"
        ),
    ),
    MetricSemantic(
        semantic_id="inventory_cover_risk",
        name="库存覆盖风险",
        definition=(
            "InventoryRiskService 读取已有库存覆盖快照，并按快照中"
            "stock_status=replenish 或 overstock 返回补货与积压风险；"
            "服务不重新预测或重算覆盖天数。"
        ),
        application_service=(
            "application.services.inventory.InventoryRiskService"
        ),
    ),
)

METRIC_SEMANTICS_BY_ID = {
    item.semantic_id: item for item in METRIC_SEMANTICS
}
