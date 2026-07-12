import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from drafts.agent_structured_export import (
    build_agent_prompt,
    extract_validated_draft_from_agent_result,
    export_failed_draft_attempt_to_json,
    export_validated_draft_to_json,
    parse_json_object_from_text,
    validate_product_page_draft_output,
)


def _valid_draft() -> dict:
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


def test_validate_product_page_draft_output_accepts_valid_schema() -> None:
    validated = validate_product_page_draft_output(_valid_draft())

    assert validated["current_product_snapshot"]["product_id"] == (
        "gid://shopify/Product/123"
    )
    assert validated["diagnosis"]["main_issues"][0]["priority"] == "medium"


def test_validate_product_page_draft_output_rejects_invalid_schema() -> None:
    draft = _valid_draft()
    draft["diagnosis"]["main_issues"][0]["priority"] = "urgent"

    with pytest.raises(ValidationError):
        validate_product_page_draft_output(draft)


def test_parse_json_object_from_text_accepts_fenced_json() -> None:
    parsed = parse_json_object_from_text(
        '```json\n{"product_id": "gid://shopify/Product/123"}\n```'
    )

    assert parsed == {"product_id": "gid://shopify/Product/123"}


def test_build_agent_prompt_normalizes_numeric_product_id() -> None:
    assert build_agent_prompt("8453308383402") == (
        "请基于这个 Shopify 商品生成商品页优化草稿："
        "gid://shopify/Product/8453308383402"
    )


def test_extract_validated_draft_from_agent_result_uses_final_message_json() -> None:
    draft = _valid_draft()
    result = extract_validated_draft_from_agent_result(
        {
            "messages": [
                {
                    "role": "assistant",
                    "content": json.dumps(draft),
                }
            ]
        }
    )

    assert result["recommended_title"] == "Sample Product by Brand"


def test_export_validated_draft_to_json(tmp_path: Path) -> None:
    validated = validate_product_page_draft_output(_valid_draft())
    output_path = tmp_path / "validated_draft.json"

    result_path = export_validated_draft_to_json(
        product_id="gid://shopify/Product/123",
        prompt="请生成商品页优化草稿",
        validated_draft=validated,
        output_path=output_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))

    assert payload["validated_by"] == "ProductPageDraftOutput"
    assert payload["product_id"] == "gid://shopify/Product/123"
    assert payload["data"]["recommended_title"] == "Sample Product by Brand"


def test_export_failed_draft_attempt_to_json_includes_raw_output_and_error(
    tmp_path: Path,
) -> None:
    draft = _valid_draft()
    draft["diagnosis"]["main_issues"][0]["priority"] = "urgent"
    raw_output = json.dumps(draft)

    with pytest.raises(ValidationError) as error_info:
        validate_product_page_draft_output(raw_output)

    output_path = tmp_path / "failed_attempt.json"
    result_path = export_failed_draft_attempt_to_json(
        product_id="gid://shopify/Product/123",
        prompt="请生成商品页优化草稿",
        error=error_info.value,
        agent_result={
            "messages": [
                {
                    "role": "assistant",
                    "content": raw_output,
                }
            ]
        },
        raw_output=raw_output,
        output_path=output_path,
    )

    payload = json.loads(result_path.read_text(encoding="utf-8"))

    assert payload["export_type"] == "product_page_draft_agent_failed_attempt"
    assert payload["product_id"] == "gid://shopify/Product/123"
    assert payload["error"]["type"] == "ValidationError"
    assert payload["error"]["details"]
    assert payload["raw_output"] == raw_output
    assert payload["final_message_content"] == raw_output
