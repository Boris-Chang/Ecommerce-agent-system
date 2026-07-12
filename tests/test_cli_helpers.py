import json

from agent_app.cli import (
    build_product_page_draft_agent_prompt,
    format_agent_route_message,
    format_product_page_validation_message,
    generate_product_page_draft_via_agent,
    is_negative_export_reply,
    is_positive_export_reply,
    is_publish_reply,
    is_product_page_draft_request,
    parse_export_format,
    render_product_page_draft,
)


def test_product_page_draft_request_detection() -> None:
    assert is_product_page_draft_request("帮我生成商品页优化草稿")
    assert is_product_page_draft_request("帮我做商品优化 gid://shopify/Product/123")
    assert is_product_page_draft_request("优化商品，8453308383402")
    assert is_product_page_draft_request("Create a product page draft")
    assert not is_product_page_draft_request("检查店铺连接")


def test_format_agent_route_message() -> None:
    assert format_agent_route_message("store_ops_agent") == (
        "当前调用 Agent：store_ops_agent"
    )


def test_format_product_page_validation_message() -> None:
    assert format_product_page_validation_message() == (
        "结构化校验：ProductPageDraftOutput 通过；以下为 CLI 摘要渲染。"
    )


def test_build_product_page_draft_agent_prompt_appends_gid_for_numeric_id() -> None:
    assert build_product_page_draft_agent_prompt("优化商品，8453308383402") == (
        "优化商品，8453308383402\n"
        "Shopify product GID: gid://shopify/Product/8453308383402"
    )


def test_export_reply_detection() -> None:
    assert is_positive_export_reply("是")
    assert is_positive_export_reply("export")
    assert is_negative_export_reply("不用")
    assert is_negative_export_reply("nope")
    assert is_publish_reply("同步到 n8n")
    assert is_publish_reply("发布")
    assert is_publish_reply("sync")


def test_parse_export_format() -> None:
    assert parse_export_format("只生成 JSON") == (True, False)
    assert parse_export_format("只生成 Markdown") == (False, True)
    assert parse_export_format("都生成") == (True, True)
    assert parse_export_format("json and markdown") == (True, True)


def test_render_product_page_draft() -> None:
    draft = {
        "current_product_snapshot": {
            "current_title": "Sample Product",
            "product_id": "gid://shopify/Product/123",
            "total_inventory": 8,
            "price_range": "19.00 - 29.00",
        },
        "diagnosis": {
            "overall_assessment": "Needs better SEO.",
            "main_issues": [
                {
                    "priority": "medium",
                    "issue_type": "missing_seo_title",
                    "explanation": "SEO title is empty.",
                }
            ],
        },
        "recommended_title": "Sample Product by Brand",
        "hero_bullets": ["Clear first benefit"],
        "seo": {
            "seo_title": "Sample SEO Title",
            "seo_description": "Sample SEO description.",
        },
        "manual_review_checklist": ["Verify dimensions"],
    }

    rendered = render_product_page_draft(draft)

    assert "Sample Product" in rendered
    assert "missing_seo_title" in rendered
    assert "Sample SEO Title" in rendered
    assert "Verify dimensions" in rendered


def test_generate_product_page_draft_via_agent_validates_final_json_message() -> None:
    draft = {
        "current_product_snapshot": {
            "current_title": "Sample Product",
            "product_id": "gid://shopify/Product/123",
            "handle": "sample-product",
            "status": "ACTIVE",
            "total_inventory": 8,
            "price_range": "19.00",
        },
        "diagnosis": {
            "overall_assessment": "Needs better SEO.",
            "main_issues": [],
        },
        "title_options": [
            {
                "title": "Sample Product by Brand",
                "rationale": "Adds brand context.",
            }
        ],
        "recommended_title": "Sample Product by Brand",
        "hero_bullets": ["Clear first benefit"],
        "product_description_markdown": "### Sample Product\n\nDescription draft.",
        "seo": {
            "seo_title": "Sample SEO Title",
            "seo_description": "Sample SEO description.",
        },
        "faq": [
            {
                "question": "Is it giftable?",
                "answer": "Yes.",
            }
        ],
        "ad_angles": [
            {
                "angle": "Gift-ready",
                "hook": "A polished gift idea.",
                "reason": "Broadens purchase intent.",
            }
        ],
        "bundle_suggestions": [
            {
                "bundle_idea": "Pair with Product B",
                "reason": "Increases AOV.",
            }
        ],
        "manual_review_checklist": ["Verify dimensions"],
    }

    class FakeAgent:
        def __init__(self) -> None:
            self.messages = None

        def invoke(self, payload: dict) -> dict:
            self.messages = payload["messages"]
            return {
                "messages": [
                    {
                        "role": "assistant",
                        "content": json.dumps(draft),
                    }
                ]
            }

    fake_agent = FakeAgent()

    result = generate_product_page_draft_via_agent(
        "帮我优化 1234567890",
        product_page_draft_agent=fake_agent,
    )

    assert result == draft
    assert fake_agent.messages == [
        {
            "role": "user",
            "content": (
                "帮我优化 1234567890\n"
                "Shopify product GID: gid://shopify/Product/1234567890"
            ),
        }
    ]
