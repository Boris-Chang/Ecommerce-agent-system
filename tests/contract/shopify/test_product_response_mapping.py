import json
from pathlib import Path

import pytest

from integrations.shopify import service


pytestmark = pytest.mark.contract
FIXTURE_PATH = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "shopify"
    / "products_response.json"
)


def test_product_edges_are_mapped_to_product_nodes(monkeypatch) -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    class FakeClient:
        def __init__(self) -> None:
            self.variables = None

        def graphql(self, query: str, variables: dict | None = None) -> dict:
            self.variables = variables
            return payload["data"]

    client = FakeClient()
    monkeypatch.setattr(service, "ShopifyAdminClient", lambda: client)

    products = service.get_products(first=1)

    assert client.variables == {"first": 1}
    assert products == [payload["data"]["products"]["edges"][0]["node"]]
    assert products[0]["id"].startswith("gid://shopify/Product/")
    assert products[0]["totalInventory"] == 8
