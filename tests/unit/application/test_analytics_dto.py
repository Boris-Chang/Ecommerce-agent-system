from datetime import date
from decimal import Decimal

import pytest
from pydantic import ValidationError

from application.dto.analytics import SkuDailySales


def test_sku_daily_sales_coerces_database_values() -> None:
    dto = SkuDailySales.model_validate(
        {
            "sales_date": "2026-07-20",
            "sku_id": "sku-1",
            "channel_account_id": "shopify-1",
            "net_sales": "55.00",
        }
    )

    assert dto.sales_date == date(2026, 7, 20)
    assert dto.net_sales == Decimal("55.00")


def test_sku_daily_sales_requires_business_key() -> None:
    with pytest.raises(ValidationError):
        SkuDailySales.model_validate(
            {
                "sales_date": "2026-07-20",
                "sku_id": "sku-1",
            }
        )


def test_read_dto_is_immutable() -> None:
    dto = SkuDailySales(
        sales_date=date(2026, 7, 20),
        sku_id="sku-1",
        channel_account_id="shopify-1",
    )

    with pytest.raises(ValidationError):
        dto.net_sales = Decimal("10.00")
