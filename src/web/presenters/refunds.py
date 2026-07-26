from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, timezone

from application.dto.sku import SkuDailyRefunds, SkuWeeklyRefunds
from web.presenters.common import format_money
from web.view_models.refunds import (
    RefundsPageViewModel,
    RefundTableRowViewModel,
)


class RefundsPresenter:
    @staticmethod
    def to_page(
        *,
        daily_rows: Sequence[SkuDailyRefunds],
        weekly_rows: Sequence[SkuWeeklyRefunds],
        channel_account_id: str,
        channel_account_ids: Sequence[str],
        start_date: date,
        end_date: date,
        generated_at: datetime | None = None,
    ) -> RefundsPageViewModel:
        resolved_generated_at = generated_at or datetime.now(timezone.utc)
        dates = sorted({row.refund_date for row in daily_rows})
        units_by_date: dict[date, int] = defaultdict(int)
        for row in daily_rows:
            units_by_date[row.refund_date] += row.refunded_units

        chart_options: dict[str, object] = {
            "animationDuration": 350,
            "tooltip": {"trigger": "axis"},
            "grid": {
                "left": 44,
                "right": 20,
                "top": 24,
                "bottom": 44,
                "containLabel": True,
            },
            "xAxis": {
                "type": "category",
                "data": [value.isoformat() for value in dates],
            },
            "yAxis": {
                "type": "value",
                "name": "退款件数",
                "minInterval": 1,
            },
            "series": [
                {
                    "name": "退款件数",
                    "type": "bar",
                    "data": [units_by_date[value] for value in dates],
                }
            ],
        }

        daily_view_rows = tuple(
            _to_refund_row(row.refund_date, row) for row in daily_rows
        )
        weekly_view_rows = tuple(
            _to_refund_row(row.week_start, row) for row in weekly_rows
        )
        currency_codes = tuple(
            sorted(
                {
                    row.currency_code
                    for row in [*daily_rows, *weekly_rows]
                    if row.currency_code
                }
            )
        )
        data_as_of = max(
            (row.refund_date for row in daily_rows),
            default=None,
        )
        return RefundsPageViewModel(
            channel_account_id=channel_account_id,
            channel_account_ids=tuple(channel_account_ids),
            start_date=start_date.isoformat(),
            end_date=end_date.isoformat(),
            generated_at=resolved_generated_at.astimezone().strftime(
                "%Y-%m-%d %H:%M"
            ),
            data_as_of=data_as_of.isoformat() if data_as_of else "暂无",
            daily_row_count=len(daily_view_rows),
            weekly_row_count=len(weekly_view_rows),
            currency_codes=currency_codes,
            has_multiple_currencies=len(currency_codes) > 1,
            empty=not daily_rows and not weekly_rows,
            chart_options=chart_options,
            daily_rows=daily_view_rows,
            weekly_rows=weekly_view_rows,
        )


def _to_refund_row(
    period_start: date,
    row: SkuDailyRefunds | SkuWeeklyRefunds,
) -> RefundTableRowViewModel:
    return RefundTableRowViewModel(
        period_start=period_start.isoformat(),
        sku_id=row.sku_id,
        refund_reason=row.refund_reason or "—",
        refund_status=row.refund_status or "—",
        refund_count=row.refund_count,
        refunded_order_count=row.refunded_order_count,
        refunded_units=row.refunded_units,
        item_refund_amount=format_money(row.item_refund_amount),
        tax_refund_amount=format_money(row.tax_refund_amount),
        shipping_refund_amount=format_money(row.shipping_refund_amount),
        currency_code=row.currency_code or "—",
    )
