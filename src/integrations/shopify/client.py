import os
import requests
from dotenv import load_dotenv

load_dotenv()


class ShopifyAdminClient:
    def __init__(self):
        self.shop = os.getenv("SHOPIFY_SHOP")
        self.client_id = os.getenv("SHOPIFY_CLIENT_ID")
        self.client_secret = os.getenv("SHOPIFY_CLIENT_SECRET")
        self.api_version = os.getenv("SHOPIFY_API_VERSION", "2026-04")

        if not self.shop:
            raise ValueError("Missing SHOPIFY_SHOP")

        if not self.client_id:
            raise ValueError("Missing SHOPIFY_CLIENT_ID")

        if not self.client_secret:
            raise ValueError("Missing SHOPIFY_CLIENT_SECRET")

        self.access_token = self.get_access_token()

    def get_access_token(self) -> str:
        url = f"https://{self.shop}/admin/oauth/access_token"

        response = requests.post(
            url,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
            },
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Failed to get access token: {response.status_code} {response.text}"
            )

        data = response.json()
        return data["access_token"]

    def graphql(self, query: str, variables: dict | None = None) -> dict:
        url = f"https://{self.shop}/admin/api/{self.api_version}/graphql.json"

        response = requests.post(
            url,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": self.access_token,
            },
            json={
                "query": query,
                "variables": variables or {},
            },
            timeout=30,
        )

        if response.status_code != 200:
            raise RuntimeError(
                f"Shopify GraphQL HTTP Error: {response.status_code} {response.text}"
            )

        result = response.json()

        if "errors" in result:
            raise RuntimeError(f"Shopify GraphQL Error: {result['errors']}")

        return result["data"]