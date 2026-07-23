from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, timezone

from application.dto.sku import SkuDailySales
from web.presenters.common import format_money
from web.view_models.sales import (
    SalesPageViewModel,
    SalesTableRowViewModel,
)


MAX_CHART_SKUS = 8


class SalesPresenter:
    @staticmethod
    def to_page(
        *,
        rows: Sequence[SkuDailySales],
        channel_account_id: str,
        start_date: date,
        end_date: date,
        generated_at: datetime | None = None,
    ) -> SalesPageViewModel:
        resolved_generated_at = generated_at or datetime.now(timezone.utc)
        dates = sorted({row.sales_date for row in rows})
        sku_ids = sorted({row.sku_id for row in rows})[:MAX_CHART_SKUS]
        units_by_sku_date: dict[tuple[str, date], int] = defaultdict(int)
        for row in rows:
            units_by_sku_date[(row.sku_id, row.sales_date)] += (
                row.units_sold or 0
            )

        chart_options: dict[str, object] = {
            "animationDuration": 350,
            "tooltip": {"trigger": "axis"},
            "legend": {"type": "scroll", "bottom": 0},
            "grid": {
                "left": 44,
                "right": 20,
                "top": 24,
                "bottom": 64,
                "containLabel": True,
            },
            "xAxis": {
                "type": "category",
                "boundaryGap": False,
                "data": [value.isoformat() for value in dates],
            },
            "yAxis": {
                "type": "value",
                "name": "销售件数",
                "minInterval": 1,
            },
            "series": [
                {
                    "name": sku_id,
                    "type": "line",
                    "smooth": True,
                    "showSymbol": False,
                    "data": [
                        units_by_sku_date[(sku_id, sales_date)]
                        for sales_date in dates
                    ],
                }
                for sku_id in sku_ids
            ],
        }

        table_rows = tuple(
            SalesTableRowViewModel(
                sales_date=row.sales_date.isoformat(),
                sku_id=row.sku_id,
                orders_count=row.orders_count or 0,
                units_sold=row.units_sold or 0,
                gross_sales=format_money(row.gross_sales),
                discount_amount=format_money(row.discount_amount),
                net_sales=format_money(row.net_sales),
                currency_code=row.currency_code or "—",
            )
            for row in rows
        )
        currency_codes = tuple(
            sorted({row.currency_code for row in rows if row.currency_code})
        )
        data_as_of = max(
            (row.sales_date for row in rows),
            default=None,
        )
        return SalesPageViewModel(
            channel_account_id=channel_account_id,
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            generated_at=resolved_generated_at.astimezone().strftime(
                "%Y-%m-%d %H:%M"
            ),
            data_as_of=data_as_of.isoformat() if data_as_of else "暂无",
            row_count=len(table_rows),
            currency_codes=currency_codes,
            has_multiple_currencies=len(currency_codes) > 1,
            empty=not rows,
            chart_options=chart_options,
            rows=table_rows,
        )
