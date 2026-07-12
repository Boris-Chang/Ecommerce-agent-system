from uuid import uuid4
from datetime import datetime, timezone

from langchain_core.tools import tool

from agent_runtime.tools.publish_action_tasks import (
    _clean_for_model,
    _run_async_publish,
)
from reports.session_store import get_latest_product_page_draft_from_memory
from schemas.product_page_draft_schema import ProductPageDraftOutput


def _build_publish_payload(
    store_domain: str,
    draft_id: str,
    draft_payload: dict,
) -> dict:
    validated_draft = ProductPageDraftOutput.model_validate(draft_payload).model_dump(
        mode="json"
    )
    snapshot = validated_draft.get("current_product_snapshot", {})

    return {
        "event_type": "product_page_draft.created",
        "source": "shopify_agent",
        "version": "v1.4",
        "store_domain": store_domain,
        "run_id": str(uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "draft_id": draft_id,
        "product_id": snapshot.get("product_id"),
        "data": {
            "draft": validated_draft,
        },
        "meta": {
            "schema": "ProductPageDraftOutput",
            "target": "n8n",
        },
    }


@tool("shopify_publish_product_page_draft")
def shopify_publish_product_page_draft(store_domain: str = "unknown-store") -> dict:
    """
    将最近一次生成的商品页优化草稿 JSON schema 结果发布到 n8n。
    n8n 可根据 event_type=product_page_draft.created 写入 Google Sheets、飞书或后续审核流。
    """
    try:
        draft_id, draft_payload = get_latest_product_page_draft_from_memory()
    except FileNotFoundError:
        return {
            "success": False,
            "error": "当前没有可发布的商品页优化草稿，请先生成商品页优化草稿。",
        }

    payload = _build_publish_payload(
        store_domain=store_domain,
        draft_id=draft_id,
        draft_payload=draft_payload,
    )

    result = _run_async_publish(payload)

    if not result.get("success"):
        return _clean_for_model(
            {
                "success": False,
                "message": "商品页优化草稿发布到 n8n 失败。",
                "draft_id": draft_id,
                "product_id": payload.get("product_id"),
                "n8n_result": result,
            }
        )

    return _clean_for_model(
        {
            "success": True,
            "message": "商品页优化草稿已发送到 n8n。",
            "draft_id": draft_id,
            "product_id": payload.get("product_id"),
            "n8n_result": result,
        }
    )
