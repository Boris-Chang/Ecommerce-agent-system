import json
from pathlib import Path

from drafts import exporters as draft_exporter
from reports import exporters as report_exporter


def test_export_report_to_json_and_markdown(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(report_exporter, "EXPORT_DIR", tmp_path)
    report = {
        "summary": {
            "checked_product_count": 1,
            "recent_order_count": 2,
            "estimated_revenue": 35.5,
            "currency": "USD",
            "products_with_issues_count": 1,
            "high_priority_issue_count": 1,
            "medium_priority_issue_count": 0,
            "low_priority_issue_count": 0,
        },
        "top_selling_products": [{"title": "Product A", "quantity": 3}],
        "action_items": ["Rewrite Product A page"],
        "product_reports": [
            {
                "id": "gid://shopify/Product/123",
                "title": "Product A",
                "handle": "product-a",
                "status": "ACTIVE",
                "product_type": "Accessory",
                "total_inventory": 5,
                "issues": [
                    {
                        "priority": "high",
                        "issue_type": "weak_description",
                        "evidence": "Description is short.",
                        "recommendation": "Add richer copy.",
                    }
                ],
            }
        ],
    }

    json_path = Path(report_exporter.export_report_to_json(report, "report-1"))
    markdown_path = Path(report_exporter.export_report_to_markdown(report, "report-1"))

    assert json_path.exists()
    assert markdown_path.exists()
    assert json.loads(json_path.read_text(encoding="utf-8"))["report_id"] == "report-1"
    assert "Shopify 商品运营诊断报告" in markdown_path.read_text(encoding="utf-8")
    assert "Product A" in markdown_path.read_text(encoding="utf-8")


def test_export_product_page_draft_to_markdown(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(draft_exporter, "EXPORT_DIR", tmp_path)
    draft = {
        "current_product_snapshot": {
            "product_id": "gid://shopify/Product/123",
            "current_title": "Product A",
            "handle": "product-a",
            "status": "ACTIVE",
            "total_inventory": 5,
            "price_range": "19.00",
        },
        "diagnosis": {
            "overall_assessment": "Needs stronger copy.",
            "main_issues": [
                {
                    "priority": "high",
                    "issue_type": "thin_description",
                    "explanation": "Description is short.",
                }
            ],
        },
        "title_options": [
            {"title": "Product A by Brand", "rationale": "Adds brand context."}
        ],
        "recommended_title": "Product A by Brand",
        "hero_bullets": ["Benefit one"],
        "product_description_markdown": "### Product A\n\nDescription draft.",
        "seo": {
            "seo_title": "Product A SEO",
            "seo_description": "Product A SEO description.",
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

    markdown_path = Path(
        draft_exporter.export_product_page_draft_to_markdown(draft, "draft-1")
    )

    text = markdown_path.read_text(encoding="utf-8")
    assert "Shopify 商品页优化草稿" in text
    assert "Product A by Brand" in text
    assert "Verify dimensions" in text
