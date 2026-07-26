from collections import defaultdict
from datetime import date
from decimal import Decimal

from application.dto.sku import SkuDashboard, SkuDashboardRow
from web.presenters.common import (
    format_money,
    format_percent,
    format_timestamp,
)
from web.view_models.sku_dashboard import (
    SkuDashboardFilterViewModel,
    SkuDashboardKpiViewModel,
    SkuDashboardPageViewModel,
    SkuDashboardRowViewModel,
    SkuRefundReasonViewModel,
)


class SkuDashboardPresenter:
    @staticmethod
    def to_page(
        dashboard: SkuDashboard,
        *,
        channel_account_ids: tuple[str, ...],
    ) -> SkuDashboardPageViewModel:
        kpis = dashboard.kpis
        return SkuDashboardPageViewModel(
            filters=SkuDashboardFilterViewModel(
                channel_account_id=dashboard.filters.channel_account_id,
                channel_account_ids=channel_account_ids,
                start_date=dashboard.filters.start_date.isoformat(),
                end_date=dashboard.filters.end_date.isoformat(),
                currency_code=dashboard.filters.currency_code,
                grain=dashboard.filters.grain,
                search=dashboard.filters.search or "",
            ),
            generated_at=format_timestamp(dashboard.generated_at),
            grain_label=(
                "日粒度"
                if dashboard.filters.grain == "daily"
                else "周粒度"
            ),
            kpis=(
                SkuDashboardKpiViewModel(
                    label="动销 SKU",
                    value=f"{kpis.active_skus:,}",
                    meta=f"共 {kpis.listed_skus:,} 个在售 SKU",
                    accent="primary",
                ),
                SkuDashboardKpiViewModel(
                    label="Top 10 集中度",
                    value=format_percent(kpis.top_10_concentration_pct),
                    meta="按区间净销售额计算",
                    accent="primary",
                ),
                SkuDashboardKpiViewModel(
                    label="整体件数退款率",
                    value=format_percent(kpis.unit_refund_rate_pct),
                    meta="退款件数 ÷ 销售件数",
                    accent="danger",
                ),
                SkuDashboardKpiViewModel(
                    label="滞销 SKU",
                    value=f"{kpis.slow_moving_skus:,}",
                    meta="产品目录销售覆盖待接入",
                    accent="warning",
                ),
            ),
            trend_chart_options=_trend_chart(dashboard),
            rows=tuple(
                _to_row(
                    row,
                    dashboard.filters.currency_code,
                    index,
                )
                for index, row in enumerate(dashboard.rows)
            ),
            empty=not dashboard.rows,
        )


def _trend_chart(dashboard: SkuDashboard) -> dict[str, object]:
    periods = sorted({item.period_start for item in dashboard.trend})
    sku_ids = tuple(
        dict.fromkeys(item.sku_id for item in dashboard.trend)
    )
    values: dict[tuple[str, date], int] = defaultdict(int)
    for item in dashboard.trend:
        values[(item.sku_id, item.period_start)] += item.units_sold
    return {
        "animationDuration": 350,
        "tooltip": {"trigger": "axis"},
        "legend": {"type": "scroll", "bottom": 0},
        "grid": {
            "left": 35,
            "right": 20,
            "top": 22,
            "bottom": 62,
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "data": [value.isoformat() for value in periods],
        },
        "yAxis": {"type": "value", "name": "销售件数", "minInterval": 1},
        "series": [
            {
                "name": sku_id,
                "type": "line",
                "smooth": True,
                "showSymbol": False,
                "data": [values[(sku_id, period)] for period in periods],
            }
            for sku_id in sku_ids
        ],
    }


def _to_row(
    row: SkuDashboardRow,
    currency_code: str,
    index: int,
) -> SkuDashboardRowViewModel:
    refund_rate = row.unit_refund_rate_pct
    cover_days = row.inventory_cover_days
    prefix = "$" if currency_code == "USD" else f"{currency_code} "
    return SkuDashboardRowViewModel(
        sku_id=row.sku_id,
        collapse_id=f"sku-detail-{index}",
        units_sold=f"{row.units_sold:,}",
        net_sales=f"{prefix}{format_money(row.net_sales)}",
        sales_change=_format_change(row.sales_change_pct),
        sales_change_tone=_tone(row.sales_change_pct),
        unit_refund_rate=format_percent(refund_rate),
        refund_tone="negative" if refund_rate >= Decimal("8") else "neutral",
        primary_refund_reason=row.primary_refund_reason,
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
        detail_chart_options=_detail_chart(row),
        refund_reasons=tuple(
            SkuRefundReasonViewModel(
                reason=item.reason,
                share_pct=format_percent(item.share_pct),
                bar_width=f"{float(item.share_pct):.2f}%",
            )
            for item in row.refund_reasons[:5]
        ),
    )


def _detail_chart(row: SkuDashboardRow) -> dict[str, object]:
    points = sorted(
        row.detail_points,
        key=lambda item: item.sales_date,
    )
    point_count = len(points)
    has_data_zoom = point_count > 30
    options: dict[str, object] = {
        "animationDuration": 250,
        "tooltip": {"trigger": "axis"},
        "legend": {"bottom": 34 if has_data_zoom else 0},
        "grid": {
            "left": 28,
            "right": 18,
            "top": 18,
            "bottom": 82 if has_data_zoom else 48,
            "containLabel": True,
        },
        "xAxis": {
            "type": "category",
            "boundaryGap": True,
            "axisLabel": {
                "interval": "auto",
                "hideOverlap": True,
            },
            "data": [item.sales_date.isoformat() for item in points],
        },
        "yAxis": {"type": "value", "minInterval": 1},
        "series": [
            {
                "name": "销售件数",
                "type": "line",
                "smooth": True,
                "showSymbol": False,
                "lineStyle": {"width": 2},
                "areaStyle": {"opacity": 0.08},
                "data": [item.units_sold for item in points],
                "itemStyle": {"color": "#12a594"},
            },
            {
                "name": "退款件数",
                "type": "bar",
                "barMaxWidth": 8,
                "data": [item.refunded_units for item in points],
                "itemStyle": {"color": "#dc5b62"},
            },
        ],
    }
    if has_data_zoom:
        options["dataZoom"] = [
            {
                "type": "inside",
                "startValue": point_count - 30,
                "endValue": point_count - 1,
            },
            {
                "type": "slider",
                "startValue": point_count - 30,
                "endValue": point_count - 1,
                "height": 18,
                "bottom": 4,
                "brushSelect": False,
            },
        ]
    return options


def _format_change(value: Decimal | None) -> str:
    if value is None:
        return "无基准"
    symbol = "▲" if value > 0 else "▼" if value < 0 else "—"
    return f"{symbol} {abs(value):.1f}%"


def _tone(value: Decimal | None) -> str:
    if value is None or value == 0:
        return "neutral"
    return "positive" if value > 0 else "negative"
