import pytest

from integrations.shopify import client as client_module


pytestmark = pytest.mark.contract


class FakeResponse:
    def __init__(self, *, status_code: int, payload: dict, text: str = "") -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text

    def json(self) -> dict:
        return self._payload


def _client_without_oauth() -> client_module.ShopifyAdminClient:
    client = object.__new__(client_module.ShopifyAdminClient)
    client.shop = "example.myshopify.com"
    client.api_version = "2026-04"
    client.access_token = "test-token"
    return client


def test_graphql_errors_are_exposed_as_integration_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        client_module.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(
            status_code=200,
            payload={"errors": [{"message": "Invalid query"}]},
        ),
    )

    with pytest.raises(RuntimeError, match="Shopify GraphQL Error"):
        _client_without_oauth().graphql("query { shop { name } }")


def test_http_errors_are_exposed_as_integration_errors(monkeypatch) -> None:
    monkeypatch.setattr(
        client_module.requests,
        "post",
        lambda *args, **kwargs: FakeResponse(
            status_code=429,
            payload={},
            text="rate limited",
        ),
    )

    with pytest.raises(RuntimeError, match="HTTP Error: 429"):
        _client_without_oauth().graphql("query { shop { name } }")
