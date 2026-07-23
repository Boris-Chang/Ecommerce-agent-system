from sqlalchemy.orm import Session

from application.dto.customer import CustomerLifetimeValue
from infrastructure.database.repositories._common import (
    to_models,
    validate_limit,
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
        return to_models(
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
                "limit": validate_limit(limit),
            },
            CustomerLifetimeValue,
        )
