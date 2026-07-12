import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = PROJECT_ROOT / "data" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def export_report_to_json(
    report: dict[str, Any],
    report_id: str,
    file_name: str | None = None,
) -> str:
    """将诊断报告导出为 JSON 文件。"""
    if file_name is None:
        file_name = f"{report_id}.json"

    file_path = EXPORT_DIR / file_name

    payload = {
        "report_id": report_id,
        "report": report,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return str(file_path)


def export_report_to_markdown(
    report: dict[str, Any],
    report_id: str,
    file_name: str | None = None,
) -> str:
    """将诊断报告导出为 Markdown 文件。"""
    if file_name is None:
        file_name = f"{report_id}.md"

    file_path = EXPORT_DIR / file_name

    summary = report.get("summary", {})
    top_selling_products = report.get("top_selling_products", [])
    action_items = report.get("action_items", [])
    product_reports = report.get("product_reports", [])

    lines = [
        "# Shopify 商品运营诊断报告",
        "",
        f"- Report ID：`{report_id}`",
        "",
        "## 一、总体概览",
        "",
        f"- 检查商品数：{summary.get('checked_product_count')}",
        f"- 最近订单数：{summary.get('recent_order_count')}",
        f"- 预估销售额：{summary.get('estimated_revenue')} {summary.get('currency')}",
        f"- 有问题商品数：{summary.get('products_with_issues_count')}",
        f"- 高优先级问题数：{summary.get('high_priority_issue_count')}",
        f"- 中优先级问题数：{summary.get('medium_priority_issue_count')}",
        f"- 低优先级问题数：{summary.get('low_priority_issue_count')}",
        "",
        "## 二、最近热卖商品",
        "",
    ]

    if top_selling_products:
        for item in top_selling_products:
            lines.append(f"- {item.get('title')}：{item.get('quantity')} 件")
    else:
        lines.append("- 暂无最近热卖商品数据")
    lines.append("")

    lines.extend(["## 三、行动清单", ""])
    if action_items:
        for item in action_items:
            lines.append(f"- {item}")
    else:
        lines.append("- 暂无行动建议")
    lines.append("")

    lines.extend(["## 四、商品问题详情", ""])
    for product in product_reports:
        issues = product.get("issues", [])
        if not issues:
            continue

        lines.append(f"### {product.get('title')}")
        lines.append(f"- 商品 ID：`{product.get('id')}`")
        lines.append(f"- Handle：`{product.get('handle')}`")
        lines.append(f"- 状态：{product.get('status')}")
        lines.append(f"- 商品类型：{product.get('product_type')}")
        lines.append(f"- 当前库存：{product.get('total_inventory')}")
        lines.append("")

        for issue in issues:
            lines.append(f"- **[{issue.get('priority')}] {issue.get('issue_type')}**")
            lines.append(f"  - 证据：{issue.get('evidence')}")
            lines.append(f"  - 建议：{issue.get('recommendation')}")
        lines.append("")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(file_path)


def export_action_tasks_to_json(
    action_tasks_payload: dict[str, Any],
    action_tasks_id: str,
    file_name: str | None = None,
) -> str:
    """将运营任务清单导出为 JSON 文件。"""
    if file_name is None:
        file_name = f"{action_tasks_id}.json"

    file_path = EXPORT_DIR / file_name

    payload = {
        "action_tasks_id": action_tasks_id,
        "data": action_tasks_payload,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return str(file_path)


def export_action_tasks_to_markdown(
    action_tasks_payload: dict[str, Any],
    action_tasks_id: str,
    file_name: str | None = None,
) -> str:
    """将运营任务清单导出为 Markdown 文件。"""
    if file_name is None:
        file_name = f"{action_tasks_id}.md"

    file_path = EXPORT_DIR / file_name

    summary = action_tasks_payload.get("summary", {})
    tasks = action_tasks_payload.get("tasks", [])
    source = action_tasks_payload.get("source", {})

    grouped_tasks: dict[str, list[dict[str, Any]]] = {
        "high": [],
        "medium": [],
        "low": [],
        "other": [],
    }

    for task in tasks:
        priority = task.get("priority")
        grouped_tasks.get(priority, grouped_tasks["other"]).append(task)

    lines = [
        "# Shopify 运营任务清单",
        "",
        f"- Action Tasks ID：`{action_tasks_id}`",
        "",
        "## 一、总体概览",
        "",
        f"- 检查商品数：{summary.get('checked_product_count')}",
        f"- 最近订单数：{summary.get('recent_order_count')}",
        f"- 有问题商品数：{summary.get('products_with_issues_count')}",
        f"- 高优先级问题数：{summary.get('high_priority_issue_count')}",
        f"- 中优先级问题数：{summary.get('medium_priority_issue_count')}",
        f"- 低优先级问题数：{summary.get('low_priority_issue_count')}",
        f"- 任务总数：{len(tasks)}",
        "",
        "## 二、分析参数",
        "",
        f"- 商品数量：{source.get('product_limit')}",
        f"- 最近订单数量：{source.get('order_limit')}",
        f"- 低库存阈值：{source.get('low_inventory_threshold')}",
        "",
    ]

    priority_titles = {
        "high": "三、高优先级任务",
        "medium": "四、中优先级任务",
        "low": "五、低优先级任务",
        "other": "六、其他任务",
    }

    for priority, title in priority_titles.items():
        priority_tasks = grouped_tasks.get(priority, [])

        lines.append(f"## {title}")
        lines.append("")

        if not priority_tasks:
            lines.append("- 暂无")
            lines.append("")
            continue

        for index, task in enumerate(priority_tasks, start=1):
            lines.append(f"### {index}. {task.get('product_title')}")
            lines.append(f"- 商品 ID：`{task.get('product_id')}`")
            lines.append(f"- Handle：`{task.get('handle')}`")
            lines.append(f"- 任务类型：{task.get('task_type')}")
            lines.append(f"- 问题类型：{task.get('issue_type')}")
            lines.append(f"- 优先级：{task.get('priority')}")
            lines.append(f"- 状态：{task.get('status')}")
            lines.append(f"- 证据：{task.get('evidence')}")
            lines.append(f"- 建议动作：{task.get('suggested_action')}")
            lines.append("")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(file_path)
