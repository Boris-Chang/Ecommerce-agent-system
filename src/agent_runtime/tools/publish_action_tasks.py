import asyncio
from uuid import uuid4
from datetime import datetime, timezone

import httpx
from langchain_core.tools import tool

from integrations.n8n.client import N8NClient
from reports.session_store import get_latest_action_tasks_from_memory


def _clean_text(value: str) -> str:
    return value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")


def _clean_for_model(value):
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, list):
        return [_clean_for_model(item) for item in value]
    if isinstance(value, dict):
        return {
            _clean_for_model(key): _clean_for_model(item)
            for key, item in value.items()
        }
    return value


def _run_async_publish(payload: dict) -> dict:
    try:
        return _clean_for_model(asyncio.run(N8NClient().publish_event(payload)))
    except httpx.HTTPStatusError as exc:
        response = exc.response
        return _clean_for_model(
            {
                "success": False,
                "status_code": response.status_code,
                "response_text": response.text,
                "error": "n8n webhook returned an HTTP error.",
            }
        )
    except Exception as exc:
        return _clean_for_model(
            {
                "success": False,
                "error": type(exc).__name__,
                "message": str(exc),
            }
        )


def _build_publish_payload(
    store_domain: str,
    action_tasks_id: str,
    action_tasks: list[dict],
) -> dict:
    return {
        "event_type": "action_tasks.created",
        "source": "shopify_agent",
        "version": "v1.4",
        "store_domain": store_domain,
        "run_id": str(uuid4()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "action_tasks_id": action_tasks_id,
        "data": {
            "tasks": action_tasks
        },
        "meta": {
            "target": "google_sheets"
        }
    }


@tool("shopify_publish_action_tasks")
def shopify_publish_action_tasks(store_domain: str = "unknown-store") -> dict:
    """
    将最近一次生成的运营任务清单发布到 n8n。
    n8n 会根据 event_type=action_tasks.created 写入 Google Sheets，也可以同步发送飞书。
    """
    try:
        action_tasks_id, action_tasks_payload = get_latest_action_tasks_from_memory()
    except FileNotFoundError:
        return {
            "success": False,
            "error": "当前没有可发布的运营任务清单，请先生成运营任务清单。",
        }

    action_tasks = action_tasks_payload.get("tasks", [])
    if not action_tasks:
        return {
            "success": False,
            "error": "当前没有可发布的运营任务清单，请先生成运营任务清单。",
        }

    payload = _build_publish_payload(
        store_domain=store_domain,
        action_tasks_id=action_tasks_id,
        action_tasks=action_tasks,
    )

    result = _run_async_publish(payload)

    if not result.get("success"):
        return _clean_for_model({
            "success": False,
            "message": "运营任务清单发布到 n8n 失败。",
            "task_count": len(action_tasks),
            "action_tasks_id": action_tasks_id,
            "n8n_result": result,
        })

    return _clean_for_model({
        "success": True,
        "message": "运营任务清单已发送到 n8n，n8n 将写入 Google Sheets。",
        "task_count": len(action_tasks),
        "action_tasks_id": action_tasks_id,
        "n8n_result": result,
    })
