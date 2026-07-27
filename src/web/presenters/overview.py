from collections import defaultdict
from collections.abc import Sequence
from datetime import date
from decimal import Decimal

from application.dto.overview import OverviewDashboard, OverviewKpis
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
        return OverviewPageViewModel(
            filters=OverviewFilterViewModel(
                channel_account_id=dashboard.filters.channel_account_id,
                channel_account_ids=tuple(available_channel_account_ids),
                day=dashboard.filters.day.isoformat(),
                week_start=dashboard.filters.week_start.isoformat(),
                week_end=dashboard.filters.week_end.isoformat(),
                trend_start=dashboard.filters.trend_start.isoformat(),
                trend_end=dashboard.filters.trend_end.isoformat(),
                currency_code=dashboard.filters.currency_code,
            ),
            generated_at=format_timestamp(dashboard.generated_at),
            daily_kpis=_period_kpis(
                dashboard.daily_kpis,
                dashboard.filters.currency_code,
                period_label="当日",
            ),
            weekly_kpis=_period_kpis(
                dashboard.weekly_kpis,
                dashboard.filters.currency_code,
                period_label="本周",
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


def _period_kpis(
    kpis: OverviewKpis,
    currency_code: str,
    *,
    period_label: str,
) -> tuple[OverviewKpiViewModel, ...]:
    return (
        OverviewKpiViewModel(
            label="净销售额",
            value=_money(kpis.net_sales, currency_code),
            meta=f"{period_label}净销售额",
            accent="primary",
        ),
        OverviewKpiViewModel(
            label="销量",
            value=f"{kpis.units_sold:,}",
            meta=f"{period_label}销售件数",
            accent="primary",
        ),
        OverviewKpiViewModel(
            label="订单数",
            value=f"{kpis.orders_count:,}",
            meta="来自 sales.orders 的非取消订单",
            accent="neutral",
        ),
        OverviewKpiViewModel(
            label="客单价",
            value=_money(kpis.average_order_value, currency_code),
            meta="净销售额 ÷ 订单数",
            accent="neutral",
        ),
        OverviewKpiViewModel(
            label="件数退款率",
            value=format_percent(kpis.unit_refund_rate_pct),
            meta="退款件数 ÷ 销售件数",
            accent="danger",
        ),
    )


def _sales_chart(dashboard: OverviewDashboard) -> dict[str, object]:
    dates = sorted({item.sales_date for item in dashboard.trend})
    values: dict[tuple[str, date], Decimal] = defaultdict(Decimal)
    for item in dashboard.trend:
        values[(item.channel_account_id, item.sales_date)] += item.net_sales
    return {
        "animationDuration": 350,
        "color": ["#12a594", "#8fd9cf", "#377cf6", "#7b8ca5"],
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "line"}},
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
                "type": "line",
                "smooth": True,
                "showSymbol": False,
                "lineStyle": {"width": 3},
                "areaStyle": {"opacity": 0.08},
                "emphasis": {"focus": "series"},
                "data": [
                    float(values[(channel_id, sales_date)])
                    for sales_date in dates
                ],
            }
            for channel_id in (dashboard.filters.channel_account_id,)
        ],
    }


def _sku_row(row: object, currency_code: str) -> OverviewSkuRowViewModel:
    refund_rate = row.unit_refund_rate_pct
    cover_days = row.inventory_cover_days
    return OverviewSkuRowViewModel(
        sku_id=row.sku_id,
        units_sold=f"{row.units_sold:,}",
        net_sales=_money(row.net_sales, currency_code),
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
