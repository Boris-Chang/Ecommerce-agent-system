from datetime import date
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from application.dto import (
    ChannelProfitMonthly,
    CustomerLifetimeValue,
    InventoryBalance,
    InventoryCover,
    SkuDailySales,
    SkuProfitMonthly,
    SkuWeeklySales,
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


def _validate_channel_account_id(value: str) -> str:
    resolved = value.strip()
    if not resolved:
        raise ValueError("channel_account_id must not be blank.")
    return resolved


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
        channel_account_id: str,
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
            WHERE channel_account_id = :channel_account_id
              AND sales_date BETWEEN :start_date AND :end_date
            ORDER BY sales_date DESC, sku_id, channel_account_id
            LIMIT :limit
            """,
            {
                "channel_account_id": _validate_channel_account_id(
                    channel_account_id
                ),
                "start_date": start_date,
                "end_date": end_date,
                "limit": _validate_limit(limit),
            },
            SkuDailySales,
        )

    def list_sku_weekly_sales(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10_000,
    ) -> list[SkuWeeklySales]:
        _validate_date_range(start_date, end_date)
        return _to_models(
            self._session,
            """
            SELECT
                DATE_TRUNC('week', sales_date)::date AS week_start,
                sku_id,
                channel_account_id,
                SUM(COALESCE(orders_count, 0))::integer AS orders_count,
                SUM(COALESCE(units_sold, 0))::integer AS units_sold,
                SUM(COALESCE(gross_sales, 0)) AS gross_sales,
                SUM(COALESCE(discount_amount, 0)) AS discount_amount,
                SUM(COALESCE(net_sales, 0)) AS net_sales,
                currency_code
            FROM analytics.v_sku_daily_sales
            WHERE channel_account_id = :channel_account_id
              AND sales_date BETWEEN :start_date AND :end_date
            GROUP BY week_start, sku_id, channel_account_id, currency_code
            ORDER BY sku_id, week_start, currency_code
            LIMIT :limit
            """,
            {
                "channel_account_id": _validate_channel_account_id(
                    channel_account_id
                ),
                "start_date": start_date,
                "end_date": end_date,
                "limit": _validate_limit(limit),
            },
            SkuWeeklySales,
        )


class PostgresInventoryRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_inventory_balances(
        self,
        *,
        sku_id: str | None = None,
        warehouse_id: str | None = None,
        limit: int = 1_000,
    ) -> list[InventoryBalance]:
        return _to_models(
            self._session,
            """
            SELECT
                sku_id,
                warehouse_id,
                on_hand_qty,
                reserved_qty,
                blocked_qty,
                available_qty,
                incoming_qty,
                updated_at,
                data_origin
            FROM inventory.inventory_balances
            WHERE (
                CAST(:sku_id AS text) IS NULL
                OR sku_id = CAST(:sku_id AS text)
            )
              AND (
                CAST(:warehouse_id AS text) IS NULL
                OR warehouse_id = CAST(:warehouse_id AS text)
              )
            ORDER BY sku_id, warehouse_id
            LIMIT :limit
            """,
            {
                "sku_id": sku_id,
                "warehouse_id": warehouse_id,
                "limit": _validate_limit(limit),
            },
            InventoryBalance,
        )

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
