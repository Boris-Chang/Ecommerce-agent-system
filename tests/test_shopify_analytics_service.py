from analytics import action_tasks
from analytics import store_diagnosis as analytics


def _variant(
    title: str = "Default",
    price: str | None = "19.00",
    inventory_quantity: int = 5,
) -> dict:
    return {
        "node": {
            "id": f"gid://shopify/ProductVariant/{title}",
            "title": title,
            "sku": title.upper(),
            "price": price,
            "compareAtPrice": None,
            "inventoryQuantity": inventory_quantity,
        }
    }


def _product(
    *,
    title: str = "Sample Product",
    description_html: str = "<p>Short</p>",
    total_inventory: int | None = 10,
    product_type: str = "",
    seo: dict | None = None,
    variants: list[dict] | None = None,
) -> dict:
    return {
        "id": "gid://shopify/Product/123",
        "title": title,
        "handle": "sample-product",
        "status": "ACTIVE",
        "productType": product_type,
        "vendor": "Demo Brand",
        "descriptionHtml": description_html,
        "totalInventory": total_inventory,
        "seo": seo if seo is not None else {"title": None, "description": None},
        "variants": {"edges": variants if variants is not None else [_variant()]},
    }


def test_analyze_product_page_detects_content_and_seo_issues() -> None:
    issues = analytics._analyze_product_page(_product(title="Short"))
    issue_types = {issue["issue_type"] for issue in issues}

    assert "weak_title" in issue_types
    assert "weak_description" in issue_types
    assert "missing_seo_title" in issue_types
    assert "missing_seo_description" in issue_types
    assert "missing_product_type" in issue_types


def test_analyze_inventory_priorities() -> None:
    out_of_stock = analytics._analyze_inventory(_product(total_inventory=0), 5)
    low_inventory = analytics._analyze_inventory(_product(total_inventory=3), 5)
    unknown = analytics._analyze_inventory(_product(total_inventory=None), 5)

    assert out_of_stock[0]["issue_type"] == "out_of_stock"
    assert out_of_stock[0]["priority"] == "high"
    assert low_inventory[0]["issue_type"] == "low_inventory"
    assert low_inventory[0]["priority"] == "medium"
    assert unknown[0]["issue_type"] == "unknown_inventory"


def test_summarize_recent_orders() -> None:
    orders = [
        {
            "totalPriceSet": {"shopMoney": {"amount": "25.50", "currencyCode": "USD"}},
            "lineItems": {
                "edges": [
                    {"node": {"title": "Product A", "quantity": 2}},
                    {"node": {"title": "Product B", "quantity": 1}},
                ]
            },
        },
        {
            "totalPriceSet": {"shopMoney": {"amount": "10", "currencyCode": "USD"}},
            "lineItems": {"edges": [{"node": {"title": "Product A", "quantity": 1}}]},
        },
    ]

    summary = analytics._summarize_recent_orders(orders)

    assert summary["order_count"] == 2
    assert summary["estimated_revenue"] == 35.5
    assert summary["currency"] == "USD"
    assert summary["top_selling_products"][0] == {"title": "Product A", "quantity": 3}


def test_generate_action_tasks_from_report_sorts_by_priority() -> None:
    report = {
        "product_reports": [
            {
                "id": "p1",
                "title": "Product One",
                "handle": "product-one",
                "issues": [
                    {
                        "issue_type": "low_inventory",
                        "priority": "medium",
                        "evidence": "Only 3 left.",
                        "recommendation": "Check replenishment.",
                    },
                    {
                        "issue_type": "weak_description",
                        "priority": "high",
                        "evidence": "Description is short.",
                        "recommendation": "Rewrite product copy.",
                    },
                ],
            }
        ]
    }

    tasks = action_tasks.generate_action_tasks_from_report(report)

    assert [task["priority"] for task in tasks] == ["high", "medium"]
    assert tasks[0]["task_type"] == "product_page_optimization"
    assert tasks[1]["task_type"] == "inventory_check"
