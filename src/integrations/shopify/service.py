from typing import Any

from integrations.shopify.client import ShopifyAdminClient
from integrations.shopify.queries import (
    GET_PRODUCT_DETAIL,
    GET_PRODUCTS,
    GET_PRODUCTS_FOR_AUDIT,
    GET_RECENT_ORDERS,
    GET_SHOP_INFO,
)


def get_shop_info() -> dict[str, Any]:
    client = ShopifyAdminClient()
    data = client.graphql(GET_SHOP_INFO)
    return data["shop"]


def get_products(first: int = 5) -> list[dict[str, Any]]:
    client = ShopifyAdminClient()
    data = client.graphql(GET_PRODUCTS, {"first": first})
    return [edge["node"] for edge in data["products"]["edges"]]


def get_product_detail(product_id: str) -> dict[str, Any] | None:
    client = ShopifyAdminClient()
    data = client.graphql(GET_PRODUCT_DETAIL, {"id": product_id})
    return data["product"]


def get_recent_orders(limit: int = 10) -> list[dict[str, Any]]:
    client = ShopifyAdminClient()
    data = client.graphql(GET_RECENT_ORDERS, {"first": limit})
    return [edge["node"] for edge in data["orders"]["edges"]]


def get_products_for_audit(limit: int = 10) -> list[dict[str, Any]]:
    """
    获取用于商品运营诊断的商品数据。
    包含商品标题、描述、SEO、库存、价格、变体等字段。
    """
    client = ShopifyAdminClient()
    data = client.graphql(GET_PRODUCTS_FOR_AUDIT, {"first": limit})
    return [edge["node"] for edge in data["products"]["edges"]]
