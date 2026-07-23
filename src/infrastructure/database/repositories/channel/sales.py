from datetime import date

from sqlalchemy.orm import Session

from application.dto.channel import ChannelSalesTotals
from infrastructure.database.repositories._common import (
    to_models,
    validate_date_range,
)


class PostgresChannelSalesRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_channel_sales_totals(
        self,
        *,
        start_date: date,
        end_date: date,
    ) -> list[ChannelSalesTotals]:
        validate_date_range(start_date, end_date)
        return to_models(
            self._session,
            """
            SELECT
                channel_account_id,
                SUM(COALESCE(units_sold, 0))::integer AS units_sold,
                SUM(COALESCE(gross_sales, 0)) AS gross_sales,
                SUM(COALESCE(discount_amount, 0)) AS discount_amount,
                SUM(COALESCE(net_sales, 0)) AS net_sales,
                currency_code
            FROM analytics.v_sku_daily_sales
            WHERE sales_date BETWEEN :start_date AND :end_date
            GROUP BY channel_account_id, currency_code
            ORDER BY currency_code, net_sales DESC, channel_account_id
            """,
            {
                "start_date": start_date,
                "end_date": end_date,
            },
            ChannelSalesTotals,
        )
