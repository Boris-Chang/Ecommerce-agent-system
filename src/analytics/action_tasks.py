def generate_action_tasks_from_report(report: dict) -> list[dict]:
    """将诊断报告转成可执行运营任务清单。"""
    tasks = []

    for product in report.get("product_reports", []):
        product_title = product.get("title")
        product_id = product.get("id")
        handle = product.get("handle")

        for issue in product.get("issues", []):
            issue_type = issue.get("issue_type")
            priority = issue.get("priority")

            if issue_type in [
                "weak_description",
                "weak_title",
                "missing_seo_title",
                "missing_seo_description",
            ]:
                task_type = "product_page_optimization"
            elif issue_type in [
                "low_inventory",
                "out_of_stock",
                "unknown_inventory",
            ]:
                task_type = "inventory_check"
            elif issue_type == "has_inventory_but_no_recent_sales":
                task_type = "conversion_review"
            else:
                task_type = "general_review"

            tasks.append(
                {
                    "product_id": product_id,
                    "product_title": product_title,
                    "handle": handle,
                    "task_type": task_type,
                    "priority": priority,
                    "issue_type": issue_type,
                    "evidence": issue.get("evidence"),
                    "suggested_action": issue.get("recommendation"),
                    "status": "pending",
                }
            )

    priority_order = {
        "high": 0,
        "medium": 1,
        "low": 2,
    }

    tasks.sort(key=lambda task: priority_order.get(task["priority"], 99))

    return tasks
