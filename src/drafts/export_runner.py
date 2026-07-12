from typing import Any

from drafts.exporters import (
    export_product_page_draft_to_json,
    export_product_page_draft_to_markdown,
)
from reports.session_store import get_latest_product_page_draft_from_memory


def export_latest_product_page_draft(
    export_json: bool = True,
    export_markdown: bool = True,
) -> dict[str, Any]:
    draft_id, draft_payload = get_latest_product_page_draft_from_memory()

    exported_files = {}

    if export_json:
        exported_files["json"] = export_product_page_draft_to_json(
            draft_payload=draft_payload,
            draft_id=draft_id,
        )

    if export_markdown:
        exported_files["markdown"] = export_product_page_draft_to_markdown(
            draft_payload=draft_payload,
            draft_id=draft_id,
        )

    if not exported_files:
        return {
            "success": False,
            "message": "没有选择任何导出格式。",
        }

    return {
        "success": True,
        "draft_id": draft_id,
        "exported_files": exported_files,
        "message": "商品页优化草稿已成功导出。",
    }
