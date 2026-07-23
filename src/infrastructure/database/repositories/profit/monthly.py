from datetime import date

from sqlalchemy.orm import Session

from application.dto.profit import ChannelProfitMonthly, SkuProfitMonthly
from infrastructure.database.repositories._common import (
    to_models,
    validate_date_range,
    validate_limit,
)


class PostgresProfitRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_sku_profit_monthly(
        self,
        *,
        start_month: date,
        end_month: date,
        limit: int = 1_000,
    ) -> list[SkuProfitMonthly]:
        validate_date_range(start_month, end_month)
        return to_models(
            self._session,
            """
            SELECT *
            FROM analytics.v_sku_pnl_monthly
            WHERE month BETWEEN :start_month AND :end_month
            ORDER BY month DESC, contribution_profit DESC NULLS LAST, sku_id
            LIMIT :limit
            """,
            {
                "start_month": start_month,
                "end_month": end_month,
                "limit": validate_limit(limit),
            },
            SkuProfitMonthly,
        )

    def list_channel_profit_monthly(
        self,
        *,
        start_month: date,
        end_month: date,
        limit: int = 1_000,
    ) -> list[ChannelProfitMonthly]:
        validate_date_range(start_month, end_month)
        return to_models(
            self._session,
            """
            SELECT *
            FROM analytics.v_channel_pnl_monthly
            WHERE month BETWEEN :start_month AND :end_month
            ORDER BY month DESC, contribution_profit DESC NULLS LAST,
                     channel_account_id
            LIMIT :limit
            """,
            {
                "start_month": start_month,
                "end_month": end_month,
                "limit": validate_limit(limit),
            },
            ChannelProfitMonthly,
        )
