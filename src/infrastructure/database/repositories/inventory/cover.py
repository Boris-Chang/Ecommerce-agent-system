from sqlalchemy.orm import Session

from application.dto.inventory import InventoryBalance, InventoryCover
from infrastructure.database.repositories._common import (
    to_models,
    validate_limit,
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
        return to_models(
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
                "limit": validate_limit(limit),
            },
            InventoryBalance,
        )

    def list_inventory_cover(
        self,
        *,
        stock_status: str | None = None,
        limit: int = 1_000,
    ) -> list[InventoryCover]:
        return to_models(
            self._session,
            """
            SELECT *
            FROM analytics.v_inventory_cover
            WHERE (
                CAST(:stock_status AS text) IS NULL
                OR stock_status = CAST(:stock_status AS text)
            )
            ORDER BY inventory_cover_days NULLS FIRST, sku_id, warehouse_id
            LIMIT :limit
            """,
            {
                "stock_status": stock_status,
                "limit": validate_limit(limit),
            },
            InventoryCover,
        )
