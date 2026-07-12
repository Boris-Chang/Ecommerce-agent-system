from agent_runtime.tools import publish_action_tasks
from reports import session_store
from reports.session_store import save_latest_action_tasks_in_memory


def _clear_latest_action_tasks() -> None:
    session_store._LATEST_ACTION_TASKS = None
    session_store._LATEST_ACTION_TASKS_ID = None


def test_publish_action_tasks_without_latest_tasks() -> None:
    _clear_latest_action_tasks()

    result = publish_action_tasks.shopify_publish_action_tasks.func("demo-store")

    assert result["success"] is False
    assert "请先生成运营任务清单" in result["error"]


def test_publish_action_tasks_uses_latest_action_tasks(monkeypatch) -> None:
    _clear_latest_action_tasks()

    save_latest_action_tasks_in_memory(
        {
            "tasks": [
                {
                    "product_id": "gid://shopify/Product/123",
                    "product_title": "Sample Product",
                    "priority": "high",
                }
            ]
        }
    )

    captured_payload = {}

    def fake_publish(payload: dict) -> dict:
        captured_payload.update(payload)
        return {"success": True, "status_code": 200, "response_text": "ok"}

    monkeypatch.setattr(publish_action_tasks, "_run_async_publish", fake_publish)

    result = publish_action_tasks.shopify_publish_action_tasks.func("demo-store")

    assert result["success"] is True
    assert result["task_count"] == 1
    assert result["n8n_result"]["status_code"] == 200
    assert captured_payload["event_type"] == "action_tasks.created"
    assert captured_payload["store_domain"] == "demo-store"
    assert captured_payload["data"]["tasks"][0]["product_title"] == "Sample Product"


def test_publish_action_tasks_cleans_invalid_unicode(monkeypatch) -> None:
    _clear_latest_action_tasks()

    save_latest_action_tasks_in_memory(
        {
            "tasks": [
                {
                    "product_id": "gid://shopify/Product/123",
                    "product_title": "Sample Product",
                    "priority": "high",
                }
            ]
        }
    )

    def fake_publish(payload: dict) -> dict:
        return {
            "success": True,
            "status_code": 200,
            "response_text": "ok\udc80",
        }

    monkeypatch.setattr(publish_action_tasks, "_run_async_publish", fake_publish)

    result = publish_action_tasks.shopify_publish_action_tasks.func("demo-store")

    assert result["success"] is True
    assert "\udc80" not in result["n8n_result"]["response_text"]


def test_publish_action_tasks_returns_failure_when_n8n_fails(monkeypatch) -> None:
    _clear_latest_action_tasks()

    save_latest_action_tasks_in_memory(
        {
            "tasks": [
                {
                    "product_id": "gid://shopify/Product/123",
                    "product_title": "Sample Product",
                    "priority": "high",
                }
            ]
        }
    )

    def fake_publish(payload: dict) -> dict:
        return {
            "success": False,
            "status_code": 404,
            "response_text": "webhook not registered",
        }

    monkeypatch.setattr(publish_action_tasks, "_run_async_publish", fake_publish)

    result = publish_action_tasks.shopify_publish_action_tasks.func("demo-store")

    assert result["success"] is False
    assert result["n8n_result"]["status_code"] == 404
    assert "发布到 n8n 失败" in result["message"]
