from collections.abc import Sequence
from datetime import date, datetime, timezone

from application.dto.channel import ChannelSalesShare
from web.presenters.common import format_money, format_percent
from web.view_models.channel_sales import (
    ChannelSalesSharePageViewModel,
    ChannelSalesShareRowViewModel,
)


class ChannelSalesSharePresenter:
    @staticmethod
    def to_page(
        *,
        rows: Sequence[ChannelSalesShare],
        start_date: date,
        end_date: date,
        generated_at: datetime | None = None,
    ) -> ChannelSalesSharePageViewModel:
        resolved_generated_at = generated_at or datetime.now(timezone.utc)
        labels = [
            f"{row.channel_account_id} · {row.currency_code}" for row in rows
        ]
        chart_options: dict[str, object] = {
            "animationDuration": 350,
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "legend": {"bottom": 0},
            "grid": {
                "left": 44,
                "right": 20,
                "top": 24,
                "bottom": 72,
                "containLabel": True,
            },
            "xAxis": {
                "type": "category",
                "data": labels,
                "axisLabel": {"rotate": 24},
            },
            "yAxis": {
                "type": "value",
                "name": "渠道占比 %",
                "max": 100,
            },
            "series": [
                {
                    "name": "销量占比",
                    "type": "bar",
                    "data": [float(row.units_share_pct) for row in rows],
                },
                {
                    "name": "净销售额占比",
                    "type": "bar",
                    "data": [float(row.net_sales_share_pct) for row in rows],
                },
            ],
        }
        table_rows = tuple(
            ChannelSalesShareRowViewModel(
                channel_account_id=row.channel_account_id,
                units_sold=row.units_sold,
                gross_sales=format_money(row.gross_sales),
                discount_amount=format_money(row.discount_amount),
                net_sales=format_money(row.net_sales),
                units_share_pct=format_percent(row.units_share_pct),
                net_sales_share_pct=format_percent(
                    row.net_sales_share_pct
                ),
                currency_code=row.currency_code,
            )
            for row in rows
        )
        currency_codes = tuple(sorted({row.currency_code for row in rows}))
        return ChannelSalesSharePageViewModel(
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            generated_at=resolved_generated_at.astimezone().strftime(
                "%Y-%m-%d %H:%M"
            ),
            channel_count=len({row.channel_account_id for row in rows}),
            row_count=len(table_rows),
            currency_codes=currency_codes,
            has_multiple_currencies=len(currency_codes) > 1,
            empty=not rows,
            chart_options=chart_options,
            rows=table_rows,
        )
