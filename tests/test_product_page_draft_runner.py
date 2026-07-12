import pytest

from drafts import product_page as runner


def _product(
    *,
    title: str = "Silver Necklace",
    description_html: str = "<p>Short</p>",
    seo: dict | None = None,
    tags: list[str] | None = None,
    inventory: int = 4,
) -> dict:
    return {
        "id": "gid://shopify/Product/123",
        "title": title,
        "handle": "silver-necklace",
        "descriptionHtml": description_html,
        "status": "ACTIVE",
        "productType": "Necklace",
        "vendor": "Demo Brand",
        "tags": tags if tags is not None else [],
        "totalInventory": inventory,
        "seo": seo if seo is not None else {"title": None, "description": None},
        "variants": {
            "edges": [
                {"node": {"id": "v1", "title": "Default", "price": "19.00"}},
                {"node": {"id": "v2", "title": "Premium", "price": "29.00"}},
            ]
        },
    }


def test_extract_product_id() -> None:
    assert (
        runner.extract_product_id("优化 gid://shopify/Product/1234567890")
        == "gid://shopify/Product/1234567890"
    )
    assert (
        runner.extract_product_id("优化商品，8453308383402")
        == "gid://shopify/Product/8453308383402"
    )
    assert runner.extract_product_id("没有商品 ID") is None


def test_price_range() -> None:
    assert runner._price_range([{"price": "19"}, {"price": "29.5"}]) == "19.00 - 29.50"
    assert runner._price_range([{"price": "19"}, {"price": "bad"}]) == "19.00"
    assert runner._price_range([{"price": None}]) is None


def test_build_issues_detects_page_gaps() -> None:
    issues = runner._build_issues(_product(title="Ring"), "Short")
    issue_types = {issue["issue_type"] for issue in issues}

    assert "weak_title" in issue_types
    assert "thin_description" in issue_types
    assert "missing_seo_title" in issue_types
    assert "missing_seo_description" in issue_types
    assert "missing_tags" in issue_types


def test_generate_product_page_draft_uses_shopify_snapshot(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(runner, "get_product_detail", lambda product_id: _product())

    draft = runner.generate_product_page_draft(
        "帮我优化 gid://shopify/Product/123"
    )

    assert draft["current_product_snapshot"]["product_id"] == "gid://shopify/Product/123"
    assert draft["current_product_snapshot"]["current_title"] == "Silver Necklace"
    assert draft["current_product_snapshot"]["price_range"] == "19.00 - 29.00"
    assert draft["recommended_title"] == "Silver Necklace | Necklace by Demo Brand"


def test_generate_product_page_draft_requires_gid() -> None:
    with pytest.raises(ValueError, match="No Shopify product GID"):
        runner.generate_product_page_draft("帮我优化这个商品")
