import json

import pytest
from pydantic import ValidationError

from agent_app.service import (
    build_product_page_draft_prompt,
    extract_product_page_draft,
    invoke_product_page_draft_agent,
    invoke_store_ops_agent,
    normalize_product_id,
    parse_json_object_from_text,
    validate_product_page_draft_output,
)


def _valid_draft() -> dict:
    return {
        "current_product_snapshot": {
            "product_id": "gid://shopify/Product/1234567890",
            "current_title": "Sample Product",
            "handle": "sample-product",
            "status": "ACTIVE",
            "total_inventory": 8,
            "price_range": "19.00",
        },
        "diagnosis": {"main_issues": [], "overall_assessment": "Needs better SEO."},
        "title_options": [
            {"title": "Sample Product by Brand", "rationale": "Adds brand context."}
        ],
        "recommended_title": "Sample Product by Brand",
        "hero_bullets": ["Clear first benefit"],
        "product_description_markdown": "### Sample Product\n\nDescription draft.",
        "seo": {
            "seo_title": "Sample SEO Title",
            "seo_description": "Sample SEO description.",
        },
        "faq": [{"question": "Is it giftable?", "answer": "Yes."}],
        "ad_angles": [
            {
                "angle": "Gift-ready",
                "hook": "A polished gift idea.",
                "reason": "Broadens purchase intent.",
            }
        ],
        "bundle_suggestions": [
            {"bundle_idea": "Pair with Product B", "reason": "Increases AOV."}
        ],
        "manual_review_checklist": ["Verify dimensions"],
    }


class FakeAgent:
    def __init__(self, result: dict) -> None:
        self.result = result
        self.payload = None

    def invoke(self, payload: dict) -> dict:
        self.payload = payload
        return self.result


def test_normalize_product_id_and_prompt() -> None:
    assert normalize_product_id("8453308383402") == (
        "gid://shopify/Product/8453308383402"
    )
    assert build_product_page_draft_prompt("8453308383402") == (
        "请基于这个 Shopify 商品生成商品页优化草稿："
        "gid://shopify/Product/8453308383402"
    )


def test_normalize_product_id_rejects_invalid_value() -> None:
    with pytest.raises(ValueError):
        normalize_product_id("not-a-product-id")


def test_parse_and_validate_structured_output() -> None:
    parsed = parse_json_object_from_text('```json\n{"ok": true}\n```')
    assert parsed == {"ok": True}

    validated = validate_product_page_draft_output(_valid_draft())
    assert validated["recommended_title"] == "Sample Product by Brand"

    invalid = _valid_draft()
    invalid["diagnosis"]["main_issues"] = [
        {"issue_type": "seo", "priority": "urgent", "explanation": "invalid"}
    ]
    with pytest.raises(ValidationError):
        validate_product_page_draft_output(invalid)


def test_extract_and_invoke_product_page_agent() -> None:
    draft = _valid_draft()
    fake_agent = FakeAgent(
        {"messages": [{"role": "assistant", "content": json.dumps(draft)}]}
    )

    result = invoke_product_page_draft_agent(
        "1234567890",
        user_prompt="优化商品页",
        agent=fake_agent,
    )

    assert result == draft
    assert fake_agent.payload == {
        "messages": [
            {
                "role": "user",
                "content": (
                    "优化商品页\n"
                    "Shopify product GID: gid://shopify/Product/1234567890"
                ),
            }
        ]
    }
    assert extract_product_page_draft(
        {"structured_response": draft}
    )["recommended_title"] == "Sample Product by Brand"


def test_invoke_store_ops_agent_passes_caller_owned_messages() -> None:
    expected = {"messages": [{"role": "assistant", "content": "ok"}]}
    fake_agent = FakeAgent(expected)
    messages = [{"role": "user", "content": "检查店铺"}]

    result = invoke_store_ops_agent(messages, agent=fake_agent)

    assert result == expected
    assert fake_agent.payload == {"messages": messages}
