from types import TracebackType

from sqlalchemy import text

from infrastructure.database.repositories import (
    PostgresChannelSalesRepository,
    PostgresCustomerRepository,
    PostgresInventoryRepository,
    PostgresOrderSummaryRepository,
    PostgresProfitRepository,
    PostgresSalesAnalyticsRepository,
    PostgresSkuRefundRepository,
)
from infrastructure.database.session import SessionFactory


class ReadOnlyUnitOfWork:
    """Own a short read-only transaction and the Repositories bound to it."""

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory = session_factory

    def __enter__(self) -> "ReadOnlyUnitOfWork":
        self.session = self._session_factory()
        self.session.execute(text("SET TRANSACTION READ ONLY"))
        self.sales = PostgresSalesAnalyticsRepository(self.session)
        self.channel_sales = PostgresChannelSalesRepository(self.session)
        self.refunds = PostgresSkuRefundRepository(self.session)
        self.inventory = PostgresInventoryRepository(self.session)
        self.orders = PostgresOrderSummaryRepository(self.session)
        self.customers = PostgresCustomerRepository(self.session)
        self.profit = PostgresProfitRepository(self.session)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.session.rollback()
        self.session.close()
