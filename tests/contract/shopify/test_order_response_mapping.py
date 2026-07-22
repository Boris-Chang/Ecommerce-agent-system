import json
from pathlib import Path

import pytest

from integrations.shopify import service


pytestmark = pytest.mark.contract
FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "shopify"
    / "recent_orders_response.json"
)


def test_order_edges_are_mapped_to_order_nodes(monkeypatch) -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    class FakeClient:
        def __init__(self) -> None:
            self.variables = None

        def graphql(self, query: str, variables: dict | None = None) -> dict:
            self.variables = variables
            return payload["data"]

    client = FakeClient()
    monkeypatch.setattr(service, "ShopifyAdminClient", lambda: client)

    orders = service.get_recent_orders(limit=1)

    assert client.variables == {"first": 1}
    assert orders == [payload["data"]["orders"]["edges"][0]["node"]]
    assert orders[0]["totalPriceSet"]["shopMoney"] == {
        "amount": "29.90",
        "currencyCode": "USD",
    }
