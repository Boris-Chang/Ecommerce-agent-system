from collections import defaultdict
from datetime import date
from decimal import Decimal, ROUND_HALF_UP

from application.dto.channel import ChannelSalesShare
from application.repositories.channel import ChannelSalesRepository


PERCENT = Decimal("100")
PERCENT_PRECISION = Decimal("0.0001")


class ChannelSalesShareService:
    """Calculate each channel's share within the same currency."""

    def __init__(self, repository: ChannelSalesRepository) -> None:
        self._repository = repository

    def list_sales_shares(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[ChannelSalesShare]:
        if start_date > end_date:
            raise ValueError("start_date must not be after end_date.")

        rows = list(
            self._repository.list_channel_sales_totals(
                start_date=start_date,
                end_date=end_date,
            )
        )
        currency_totals: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {"units": Decimal("0"), "net_sales": Decimal("0")}
        )
        for row in rows:
            currency_totals[row.currency_code]["units"] += Decimal(
                row.units_sold
            )
            currency_totals[row.currency_code]["net_sales"] += row.net_sales

        return [
            ChannelSalesShare(
                **row.model_dump(),
                units_share_pct=_percentage(
                    Decimal(row.units_sold),
                    currency_totals[row.currency_code]["units"],
                ),
                net_sales_share_pct=_percentage(
                    row.net_sales,
                    currency_totals[row.currency_code]["net_sales"],
                ),
            )
            for row in rows
        ]


def _percentage(value: Decimal, total: Decimal) -> Decimal:
    if total == 0:
        return Decimal("0")
    return ((value / total) * PERCENT).quantize(
        PERCENT_PRECISION,
        rounding=ROUND_HALF_UP,
    )
