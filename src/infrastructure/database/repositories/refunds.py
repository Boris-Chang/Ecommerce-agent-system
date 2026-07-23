from datetime import date

from sqlalchemy.orm import Session

from application.dto.sku import SkuDailyRefunds, SkuWeeklyRefunds
from infrastructure.database.repositories.analytics import (
    _to_models,
    _validate_channel_account_id,
    _validate_date_range,
    _validate_limit,
)


class PostgresSkuRefundRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def list_sku_daily_refunds(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 1_000,
    ) -> list[SkuDailyRefunds]:
        _validate_date_range(start_date, end_date)
        return _to_models(
            self._session,
            """
            SELECT
                refunds.refunded_at::date AS refund_date,
                order_lines.sku_id,
                orders.channel_account_id,
                refunds.refund_reason,
                refunds.refund_status,
                COUNT(DISTINCT refunds.refund_id)::integer AS refund_count,
                COUNT(DISTINCT refunds.order_id)::integer
                    AS refunded_order_count,
                COALESCE(SUM(refund_lines.refund_quantity), 0)::integer
                    AS refunded_units,
                COALESCE(SUM(refund_lines.refund_amount), 0)
                    AS item_refund_amount,
                COALESCE(SUM(refund_lines.tax_refund_amount), 0)
                    AS tax_refund_amount,
                COALESCE(SUM(refund_lines.shipping_refund_amount), 0)
                    AS shipping_refund_amount,
                refunds.currency_code
            FROM sales.refunds AS refunds
            JOIN sales.refund_lines AS refund_lines
              ON refund_lines.refund_id = refunds.refund_id
            JOIN sales.order_lines AS order_lines
              ON order_lines.order_line_id = refund_lines.order_line_id
            JOIN sales.orders AS orders
              ON orders.order_id = refunds.order_id
            WHERE orders.channel_account_id = :channel_account_id
              AND refunds.refunded_at::date
                  BETWEEN :start_date AND :end_date
              AND order_lines.sku_id IS NOT NULL
            GROUP BY
                refund_date,
                order_lines.sku_id,
                orders.channel_account_id,
                refunds.refund_reason,
                refunds.refund_status,
                refunds.currency_code
            ORDER BY refund_date DESC, order_lines.sku_id,
                     refunds.refund_reason, refunds.refund_status,
                     refunds.currency_code
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
            SkuDailyRefunds,
        )

    def list_sku_weekly_refunds(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        limit: int = 10_000,
    ) -> list[SkuWeeklyRefunds]:
        _validate_date_range(start_date, end_date)
        return _to_models(
            self._session,
            """
            SELECT
                DATE_TRUNC('week', refunds.refunded_at)::date AS week_start,
                order_lines.sku_id,
                orders.channel_account_id,
                refunds.refund_reason,
                refunds.refund_status,
                COUNT(DISTINCT refunds.refund_id)::integer AS refund_count,
                COUNT(DISTINCT refunds.order_id)::integer
                    AS refunded_order_count,
                COALESCE(SUM(refund_lines.refund_quantity), 0)::integer
                    AS refunded_units,
                COALESCE(SUM(refund_lines.refund_amount), 0)
                    AS item_refund_amount,
                COALESCE(SUM(refund_lines.tax_refund_amount), 0)
                    AS tax_refund_amount,
                COALESCE(SUM(refund_lines.shipping_refund_amount), 0)
                    AS shipping_refund_amount,
                refunds.currency_code
            FROM sales.refunds AS refunds
            JOIN sales.refund_lines AS refund_lines
              ON refund_lines.refund_id = refunds.refund_id
            JOIN sales.order_lines AS order_lines
              ON order_lines.order_line_id = refund_lines.order_line_id
            JOIN sales.orders AS orders
              ON orders.order_id = refunds.order_id
            WHERE orders.channel_account_id = :channel_account_id
              AND refunds.refunded_at::date
                  BETWEEN :start_date AND :end_date
              AND order_lines.sku_id IS NOT NULL
            GROUP BY
                week_start,
                order_lines.sku_id,
                orders.channel_account_id,
                refunds.refund_reason,
                refunds.refund_status,
                refunds.currency_code
            ORDER BY week_start DESC, order_lines.sku_id,
                     refunds.refund_reason, refunds.refund_status,
                     refunds.currency_code
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
            SkuWeeklyRefunds,
        )
