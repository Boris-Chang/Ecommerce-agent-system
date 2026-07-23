from datetime import date

import pytest

from infrastructure.database.session import create_session_factory
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork


pytestmark = pytest.mark.integration


def test_read_repositories_execute_against_postgresql(database_test_engine) -> None:
    session_factory = create_session_factory(database_test_engine)

    with ReadOnlyUnitOfWork(session_factory) as unit_of_work:
        sales = unit_of_work.sales.list_sku_daily_sales(
            start_date=date(1900, 1, 1),
            end_date=date(2100, 12, 31),
            limit=1,
        )
        inventory = unit_of_work.inventory.list_inventory_cover(limit=1)
        customers = unit_of_work.customers.list_customer_lifetime_value(limit=1)
        sku_profit = unit_of_work.profit.list_sku_profit_monthly(
            start_month=date(1900, 1, 1),
            end_month=date(2100, 12, 31),
            limit=1,
        )
        channel_profit = unit_of_work.profit.list_channel_profit_monthly(
            start_month=date(1900, 1, 1),
            end_month=date(2100, 12, 31),
            limit=1,
        )

    assert len(sales) <= 1
    assert len(inventory) <= 1
    assert len(customers) <= 1
    assert len(sku_profit) <= 1
    assert len(channel_profit) <= 1
