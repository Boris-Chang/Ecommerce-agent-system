from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from application.dto.overview import OverviewDashboard
from web.presenters.common import (
    format_money,
    format_percent,
    format_timestamp,
)
from web.view_models.overview import (
    OverviewChannelViewModel,
    OverviewFilterViewModel,
    OverviewInsightViewModel,
    OverviewKpiViewModel,
    OverviewPageViewModel,
    OverviewSkuRowViewModel,
)


SEVERITY_LABELS = {
    "high": "高",
    "medium": "中",
    "low": "低",
    "info": "提示",
}


class OverviewPresenter:
    @staticmethod
    def to_page(
        dashboard: OverviewDashboard,
        *,
        available_channel_account_ids: Sequence[str],
    ) -> OverviewPageViewModel:
        kpis = dashboard.kpis
        return OverviewPageViewModel(
            filters=OverviewFilterViewModel(
                channel_account_ids=dashboard.filters.channel_account_ids,
                available_channel_account_ids=tuple(
                    available_channel_account_ids
                ),
                start_date=dashboard.filters.start_date.isoformat(),
                end_date=dashboard.filters.end_date.isoformat(),
                currency_code=dashboard.filters.currency_code,
            ),
            generated_at=format_timestamp(dashboard.generated_at),
            kpis=(
                _kpi(
                    "净销售额",
                    _money(kpis.net_sales, dashboard.filters.currency_code),
                    kpis.net_sales_change_pct,
                    "对比上一周期",
                    "primary",
                ),
                _kpi(
                    "销量",
                    f"{kpis.units_sold:,}",
                    kpis.units_change_pct,
                    "销售件数",
                    "primary",
                ),
                _kpi(
                    "订单数",
                    f"{kpis.orders_count:,}",
                    kpis.orders_change_pct,
                    "统一订单指标待接入",
                    "neutral",
                ),
                _kpi(
                    "客单价",
                    _money(
                        kpis.average_order_value,
                        dashboard.filters.currency_code,
                    ),
                    kpis.average_order_value_change_pct,
                    "净销售额 ÷ 订单数",
                    "neutral",
                ),
                OverviewKpiViewModel(
                    label="件数退款率",
                    value=format_percent(kpis.unit_refund_rate_pct),
                    change=_format_points(
                        kpis.unit_refund_rate_change_points
                    ),
                    change_tone=_inverse_tone(
                        kpis.unit_refund_rate_change_points
                    ),
                    meta="退款件数 ÷ 销售件数",
                    accent="danger",
                ),
                OverviewKpiViewModel(
                    label="缺货风险 SKU",
                    value=f"{kpis.stockout_risk_skus:,}",
                    change="查看库存风险",
                    change_tone=(
                        "negative"
                        if kpis.stockout_risk_skus
                        else "neutral"
                    ),
                    meta="库存快照状态 replenish",
                    accent="warning",
                ),
            ),
            sales_chart_options=_sales_chart(dashboard),
            channels=tuple(
                OverviewChannelViewModel(
                    channel_account_id=row.channel_account_id,
                    net_sales=_money(
                        row.net_sales,
                        dashboard.filters.currency_code,
                    ),
                    net_sales_share_pct=format_percent(
                        row.net_sales_share_pct
                    ),
                    units_share_pct=format_percent(row.units_share_pct),
                    gross_profit_share_pct=format_percent(
                        row.gross_profit_share_pct
                    ),
                    bar_width=f"{float(row.net_sales_share_pct):.2f}%",
                )
                for row in dashboard.channel_contributions
            ),
            sku_rows=tuple(
                _sku_row(row, dashboard.filters.currency_code)
                for row in dashboard.sku_performance
            ),
            insights=tuple(
                OverviewInsightViewModel(
                    category=item.category,
                    severity_label=SEVERITY_LABELS[item.severity],
                    severity=item.severity,
                    title=item.title,
                    detail=item.detail,
                    href=item.href,
                )
                for item in dashboard.insights
            ),
            empty=not dashboard.trend,
        )


def _kpi(
    label: str,
    value: str,
    change_value: Decimal | None,
    meta: str,
    accent: str,
) -> OverviewKpiViewModel:
    return OverviewKpiViewModel(
        label=label,
        value=value,
        change=_format_change(change_value),
        change_tone=_tone(change_value),
        meta=meta,
        accent=accent,
    )


def _sales_chart(dashboard: OverviewDashboard) -> dict[str, object]:
    dates = sorted({item.sales_date for item in dashboard.trend})
    values: dict[tuple[str, date], Decimal] = defaultdict(Decimal)
    for item in dashboard.trend:
        values[(item.channel_account_id, item.sales_date)] += item.net_sales
    return {
        "animationDuration": 350,
        "color": ["#12a594", "#8fd9cf", "#377cf6", "#7b8ca5"],
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"bottom": 0},
        "grid": {
            "left": 28,
            "right": 20,
            "top": 20,
            "bottom": 56,
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": [value.isoformat() for value in dates],
            "axisLabel": {"hideOverlap": True},
        },
        "yAxis": {
            "type": "value",
            "name": f"净销售额 {dashboard.filters.currency_code}",
        },
        "series": [
            {
                "name": channel_id,
                "type": "bar",
                "stack": "net-sales",
                "barMaxWidth": 28,
                "emphasis": {"focus": "series"},
                "data": [
                    float(values[(channel_id, sales_date)])
                    for sales_date in dates
                ],
            }
            for channel_id in dashboard.filters.channel_account_ids
        ],
    }


def _sku_row(row: object, currency_code: str) -> OverviewSkuRowViewModel:
    refund_rate = row.unit_refund_rate_pct
    cover_days = row.inventory_cover_days
    return OverviewSkuRowViewModel(
        sku_id=row.sku_id,
        units_sold=f"{row.units_sold:,}",
        net_sales=_money(row.net_sales, currency_code),
        sales_change=_format_change(row.sales_change_pct),
        sales_change_tone=_tone(row.sales_change_pct),
        unit_refund_rate=format_percent(refund_rate),
        refund_tone="negative" if refund_rate >= Decimal("8") else "neutral",
        inventory_cover_days=(
            f"{cover_days} 天" if cover_days is not None else "—"
        ),
        inventory_tone=(
            "negative"
            if cover_days is not None and cover_days < 14
            else "warning"
            if cover_days is not None and cover_days > 120
            else "neutral"
        ),
        forecast_4w_p50=f"{row.forecast_4w_p50:,.0f}",
    )


def _money(value: Decimal, currency_code: str) -> str:
    prefix = "$" if currency_code == "USD" else f"{currency_code} "
    return f"{prefix}{format_money(value)}"


def _format_change(value: Decimal | None) -> str:
    if value is None:
        return "无可比基准"
    symbol = "▲" if value > 0 else "▼" if value < 0 else "—"
    return f"{symbol} {abs(value):.1f}%"


def _format_points(value: Decimal | None) -> str:
    if value is None:
        return "无可比基准"
    symbol = "▲" if value > 0 else "▼" if value < 0 else "—"
    return f"{symbol} {abs(value):.1f}pt"


def _tone(value: Decimal | None) -> str:
    if value is None or value == 0:
        return "neutral"
    return "positive" if value > 0 else "negative"


def _inverse_tone(value: Decimal | None) -> str:
    if value is None or value == 0:
        return "neutral"
    return "negative" if value > 0 else "positive"
