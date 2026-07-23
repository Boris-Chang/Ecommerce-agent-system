from typing import Protocol, Sequence

from application.dto.customer import CustomerLifetimeValue


class CustomerRepository(Protocol):
    def list_customer_lifetime_value(
        self,
        *,
        ltv_segment: str | None = None,
        repeat_customer: bool | None = None,
        limit: int = 1_000,
    ) -> Sequence[CustomerLifetimeValue]: ...
