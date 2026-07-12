from agent_runtime.tools import publish_product_page_draft
from reports import session_store
from reports.session_store import save_latest_product_page_draft_in_memory


def _clear_latest_product_page_draft() -> None:
    session_store._LATEST_PRODUCT_PAGE_DRAFT = None
    session_store._LATEST_PRODUCT_PAGE_DRAFT_ID = None


def _draft_payload() -> dict:
    return {
        "current_product_snapshot": {
            "product_id": "gid://shopify/Product/123",
            "current_title": "Sample Product",
            "handle": "sample-product",
            "status": "ACTIVE",
            "total_inventory": 8,
            "price_range": "19.00",
        },
        "diagnosis": {
            "main_issues": [
                {
                    "issue_type": "missing_seo_title",
                    "priority": "medium",
                    "explanation": "SEO title is empty.",
                }
            ],
            "overall_assessment": "Needs better SEO.",
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


def test_publish_product_page_draft_without_latest_draft() -> None:
    _clear_latest_product_page_draft()

    result = publish_product_page_draft.shopify_publish_product_page_draft.func(
        "demo-store"
    )

    assert result["success"] is False
    assert "请先生成商品页优化草稿" in result["error"]


def test_publish_product_page_draft_uses_latest_draft(monkeypatch) -> None:
    _clear_latest_product_page_draft()
    save_latest_product_page_draft_in_memory(_draft_payload())

    captured_payload = {}

    def fake_publish(payload: dict) -> dict:
        captured_payload.update(payload)
        return {"success": True, "status_code": 200, "response_text": "ok"}

    monkeypatch.setattr(publish_product_page_draft, "_run_async_publish", fake_publish)

    result = publish_product_page_draft.shopify_publish_product_page_draft.func(
        "demo-store"
    )

    assert result["success"] is True
    assert result["product_id"] == "gid://shopify/Product/123"
    assert captured_payload["event_type"] == "product_page_draft.created"
    assert captured_payload["store_domain"] == "demo-store"
    assert captured_payload["product_id"] == "gid://shopify/Product/123"
    assert captured_payload["meta"]["schema"] == "ProductPageDraftOutput"
    assert captured_payload["data"]["draft"]["recommended_title"] == (
        "Sample Product by Brand"
    )


def test_publish_product_page_draft_returns_failure_when_n8n_fails(monkeypatch) -> None:
    _clear_latest_product_page_draft()
    save_latest_product_page_draft_in_memory(_draft_payload())

    def fake_publish(payload: dict) -> dict:
        return {
            "success": False,
            "status_code": 404,
            "response_text": "webhook not registered",
        }

    monkeypatch.setattr(publish_product_page_draft, "_run_async_publish", fake_publish)

    result = publish_product_page_draft.shopify_publish_product_page_draft.func(
        "demo-store"
    )

    assert result["success"] is False
    assert result["n8n_result"]["status_code"] == 404
    assert "发布到 n8n 失败" in result["message"]
