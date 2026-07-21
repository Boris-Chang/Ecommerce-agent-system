from agent_runtime.tools import shopify_tools


def test_diagnosis_tool_returns_result_without_latest_state(monkeypatch) -> None:
    report = {"summary": {"checked_product_count": 1}}
    monkeypatch.setattr(
        shopify_tools,
        "generate_store_diagnosis_report",
        lambda **kwargs: report,
    )

    result = shopify_tools.shopify_generate_store_diagnosis_report.func()

    assert result == {"success": True, "report": report}
    assert "report_id" not in result
    assert "export_prompt" not in result


def test_action_tasks_tool_returns_result_without_latest_state(monkeypatch) -> None:
    report = {"summary": {"checked_product_count": 1}}
    tasks = [{"task_type": "inventory_check", "priority": "high"}]
    monkeypatch.setattr(
        shopify_tools,
        "generate_store_diagnosis_report",
        lambda **kwargs: report,
    )
    monkeypatch.setattr(
        shopify_tools,
        "generate_action_tasks_from_report",
        lambda value: tasks,
    )

    result = shopify_tools.shopify_generate_action_tasks.func()

    assert result == {
        "success": True,
        "summary": report["summary"],
        "task_count": 1,
        "tasks": tasks,
    }
    assert "action_tasks_id" not in result
    assert "export_prompt" not in result
