from datetime import date
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from application.dto.analytics import (
    ChannelProfitMonthly,
    CustomerLifetimeValue,
    InventoryCover,
    SkuDailySales,
    SkuProfitMonthly,
)


ReadModelT = TypeVar("ReadModelT", bound=BaseModel)
MAX_QUERY_LIMIT = 10_000


def _validate_limit(limit: int) -> int:
    if not 1 <= limit <= MAX_QUERY_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_QUERY_LIMIT}.")
    return limit


def _validate_date_range(start: date, end: date) -> None:
    if start > end:
        raise ValueError("start date must not be after end date.")


def _to_models(
    session: Session,
    statement: str,
    params: dict,
    model: type[ReadModelT],
) -> list[ReadModelT]:
    rows = session.execute(text(statement), params).mappings().all()
    return [model.model_validate(dict(row)) for row in rows]


class PostgresSalesAnalyticsRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_sku_daily_sales(
        self,
        *,
        start_date: date,
        end_date: date,
        limit: int = 1_000,
    ) -> list[SkuDailySales]:
        _validate_date_range(start_date, end_date)
        return _to_models(
            self._session,
            """
            SELECT *
            FROM analytics.v_sku_daily_sales
            WHERE sales_date BETWEEN :start_date AND :end_date
            ORDER BY sales_date DESC, sku_id, channel_account_id
            LIMIT :limit
            """,
            {
                "start_date": start_date,
                "end_date": end_date,
                "limit": _validate_limit(limit),
            },
            SkuDailySales,
        )


class PostgresInventoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_inventory_cover(
        self,
        *,
        stock_status: str | None = None,
        limit: int = 1_000,
    ) -> list[InventoryCover]:
        return _to_models(
            self._session,
            """
            SELECT *
            FROM analytics.v_inventory_cover
            WHERE (:stock_status IS NULL OR stock_status = :stock_status)
            ORDER BY inventory_cover_days NULLS FIRST, sku_id, warehouse_id
            LIMIT :limit
            """,
            {
                "stock_status": stock_status,
                "limit": _validate_limit(limit),
            },
            InventoryCover,
        )


class PostgresCustomerRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_customer_lifetime_value(
        self,
        *,
        ltv_segment: str | None = None,
        repeat_customer: bool | None = None,
        limit: int = 1_000,
    ) -> list[CustomerLifetimeValue]:
        return _to_models(
            self._session,
            """
            SELECT *
            FROM analytics.v_customer_ltv
            WHERE (:ltv_segment IS NULL OR ltv_segment = :ltv_segment)
              AND (:repeat_customer IS NULL OR repeat_customer = :repeat_customer)
            ORDER BY net_revenue DESC NULLS LAST, customer_id
            LIMIT :limit
            """,
            {
                "ltv_segment": ltv_segment,
                "repeat_customer": repeat_customer,
                "limit": _validate_limit(limit),
            },
            CustomerLifetimeValue,
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
        _validate_date_range(start_month, end_month)
        return _to_models(
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
                "limit": _validate_limit(limit),
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
        _validate_date_range(start_month, end_month)
        return _to_models(
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
                "limit": _validate_limit(limit),
            },
            ChannelProfitMonthly,
        )
