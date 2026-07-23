from datetime import date
from typing import Protocol, Sequence

from application.dto.channel import ChannelSalesTotals


class ChannelSalesRepository(Protocol):
    def list_channel_sales_totals(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> Sequence[ChannelSalesTotals]: ...
