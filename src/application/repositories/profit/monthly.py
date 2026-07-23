from datetime import date
from typing import Protocol, Sequence

from application.dto.profit import ChannelProfitMonthly, SkuProfitMonthly


class ProfitRepository(Protocol):
    def list_sku_profit_monthly(
        self,
        *,
        start_month: date,
        end_month: date,
        limit: int = 1_000,
    ) -> Sequence[SkuProfitMonthly]: ...

    def list_channel_profit_monthly(
        self,
        *,
        start_month: date,
        end_month: date,
        limit: int = 1_000,
    ) -> Sequence[ChannelProfitMonthly]: ...
