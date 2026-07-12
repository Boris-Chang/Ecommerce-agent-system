from typing import Any

from langchain.tools import tool

from analytics.action_tasks import generate_action_tasks_from_report
from analytics.store_diagnosis import generate_store_diagnosis_report
from reports.exporters import (
    export_action_tasks_to_json,
    export_action_tasks_to_markdown,
    export_report_to_json,
    export_report_to_markdown,
)
from reports.session_store import (
    get_latest_action_tasks_from_memory,
    get_latest_report_from_memory,
    save_latest_action_tasks_in_memory,
    save_latest_report_in_memory,
)
from integrations.shopify.service import (
    get_product_detail,
    get_products,
    get_recent_orders,
    get_shop_info,
)


@tool
def shopify_generate_store_diagnosis_report(
    product_limit: int = 10,
    order_limit: int = 10,
    low_inventory_threshold: int = 5,
) -> dict[str, Any]:
    """
    生成 Shopify 店铺商品运营诊断报告。

    这个工具只生成报告，并将报告暂存在当前会话内存中；不会自动生成 JSON 或 Markdown 文件。

    Args:
        product_limit: 要诊断的商品数量，默认 10 个。
        order_limit: 要分析的最近订单数量，默认 10 个。
        low_inventory_threshold: 低库存阈值，默认 5。

    适用场景：
    - 用户要求诊断店铺
    - 用户要求生成运营报告
    - 用户要求分析商品运营问题
    - 用户要求检查库存和商品页问题
    - 用户要求综合分析商品、库存、订单表现
    """
    report = generate_store_diagnosis_report(
        product_limit=product_limit,
        order_limit=order_limit,
        low_inventory_threshold=low_inventory_threshold,
    )
    report_id = save_latest_report_in_memory(report)

    return {
        "success": True,
        "report_id": report_id,
        "report": report,
        "export_prompt": {
            "should_ask_user": True,
            "question": "是否需要将这份诊断报告导出为 JSON / Markdown 文档？回复“是”将默认同时生成 JSON 和 Markdown；也可以回复“只生成 JSON”或“只生成 Markdown”。",
        },
    }


@tool
def shopify_export_latest_diagnosis_report(
    export_json: bool = True,
    export_markdown: bool = True,
) -> dict[str, Any]:
    """
    将最近一次 Shopify 店铺诊断报告导出为 JSON 和/或 Markdown 文件。

    Args:
        export_json: 是否导出 JSON 文件。默认 True。
        export_markdown: 是否导出 Markdown 文件。默认 True。

    当用户在生成诊断报告后回复“是”“生成”“导出”“都生成”“只生成 JSON”“只生成 Markdown”时使用。
    如果用户没有明确指定格式，默认同时生成 JSON 和 Markdown。
    """
    report_id, report = get_latest_report_from_memory()

    exported_files = {}

    if export_json:
        exported_files["json"] = export_report_to_json(
            report=report,
            report_id=report_id,
        )

    if export_markdown:
        exported_files["markdown"] = export_report_to_markdown(
            report=report,
            report_id=report_id,
        )

    if not exported_files:
        return {
            "success": False,
            "message": "没有选择任何导出格式。",
        }

    return {
        "success": True,
        "report_id": report_id,
        "exported_files": exported_files,
        "message": "诊断报告已成功导出。",
    }


@tool
def shopify_get_shop_info() -> dict[str, Any]:
    """
    获取当前 Shopify 店铺的基础信息，包括店铺名称、myshopify 域名和主域名。

    当用户询问店铺连接是否正常、店铺名称、店铺域名时使用。
    """
    return get_shop_info()


@tool
def shopify_get_product_detail(product_id: str) -> dict[str, Any]:
    """
    获取单个 Shopify 商品的详细信息。

    Args:
        product_id: Shopify 商品 ID，格式通常类似 gid://shopify/Product/1234567890。

    当用户给出商品 GID，或想分析某个具体商品的标题、描述、SEO、价格、库存或变体信息时使用。
    """
    product = get_product_detail(product_id)

    if product is None:
        return {
            "found": False,
            "message": "没有找到这个商品。",
        }

    return {
        "found": True,
        "product": product,
    }


@tool
def shopify_get_products(limit: int = 10) -> dict[str, Any]:
    """
    获取 Shopify 店铺商品列表。

    Args:
        limit: 要获取的商品数量，默认 10 个。

    当用户想查看商品、诊断商品页、分析库存、分析商品标题、分析价格或做商品运营建议时使用。
    """
    products = get_products(limit)

    simplified_products = []

    for product in products:
        variants = product.get("variants", {}).get("edges", [])

        simplified_products.append(
            {
                "id": product.get("id"),
                "title": product.get("title"),
                "handle": product.get("handle"),
                "status": product.get("status"),
                "productType": product.get("productType"),
                "vendor": product.get("vendor"),
                "totalInventory": product.get("totalInventory"),
                "variants": [
                    {
                        "id": variant["node"].get("id"),
                        "title": variant["node"].get("title"),
                        "sku": variant["node"].get("sku"),
                        "price": variant["node"].get("price"),
                        "compareAtPrice": variant["node"].get("compareAtPrice"),
                        "inventoryQuantity": variant["node"].get("inventoryQuantity"),
                    }
                    for variant in variants
                ],
            }
        )

    return {
        "count": len(simplified_products),
        "products": simplified_products,
    }


@tool
def shopify_get_recent_orders(limit: int = 10) -> dict[str, Any]:
    """
    获取 Shopify 店铺最近订单。

    Args:
        limit: 要获取的订单数量，默认 10 个。

    当用户想分析最近销量、热卖商品、订单趋势、订单金额或商品销售表现时使用。
    """
    orders = get_recent_orders(limit)

    simplified_orders = []

    for order in orders:
        line_items = order.get("lineItems", {}).get("edges", [])

        simplified_orders.append(
            {
                "id": order.get("id"),
                "name": order.get("name"),
                "createdAt": order.get("createdAt"),
                "financialStatus": order.get("displayFinancialStatus"),
                "fulfillmentStatus": order.get("displayFulfillmentStatus"),
                "totalPrice": order.get("totalPriceSet", {})
                .get("shopMoney", {})
                .get("amount"),
                "currency": order.get("totalPriceSet", {})
                .get("shopMoney", {})
                .get("currencyCode"),
                "items": [
                    {
                        "title": item["node"].get("title"),
                        "quantity": item["node"].get("quantity"),
                        "unitPrice": item["node"]
                        .get("originalUnitPriceSet", {})
                        .get("shopMoney", {})
                        .get("amount"),
                    }
                    for item in line_items
                ],
            }
        )

    return {
        "count": len(simplified_orders),
        "orders": simplified_orders,
    }


@tool
def shopify_generate_action_tasks(
    product_limit: int = 10,
    order_limit: int = 10,
    low_inventory_threshold: int = 5,
) -> dict[str, Any]:
    """
    根据 Shopify 商品和订单数据，生成可执行的运营任务清单。

    适用场景：
    - 用户要求生成任务清单
    - 用户询问下一步该做什么
    - 用户要求把诊断结果整理成待办事项
    - 用户要求按优先级排序运营动作
    - 用户询问今天应该优先处理哪些商品
    """
    report = generate_store_diagnosis_report(
        product_limit=product_limit,
        order_limit=order_limit,
        low_inventory_threshold=low_inventory_threshold,
    )

    tasks = generate_action_tasks_from_report(report)

    payload = {
        "summary": report.get("summary", {}),
        "task_count": len(tasks),
        "tasks": tasks,
        "source": {
            "product_limit": product_limit,
            "order_limit": order_limit,
            "low_inventory_threshold": low_inventory_threshold,
        },
    }

    action_tasks_id = save_latest_action_tasks_in_memory(payload)

    return {
        "success": True,
        "action_tasks_id": action_tasks_id,
        "summary": payload["summary"],
        "task_count": payload["task_count"],
        "tasks": payload["tasks"],
        "export_prompt": {
            "should_ask_user": True,
            "question": "是否需要将这份运营任务清单导出为 JSON / Markdown 文档？回复“是”将默认同时生成 JSON 和 Markdown；也可以回复“只生成 JSON”或“只生成 Markdown”。",
        },
    }


@tool
def shopify_export_latest_action_tasks(
    export_json: bool = True,
    export_markdown: bool = True,
) -> dict[str, Any]:
    """
    将最近一次 Shopify 运营任务清单导出为 JSON 和/或 Markdown 文件。

    Args:
        export_json: 是否导出 JSON 文件。默认 True。
        export_markdown: 是否导出 Markdown 文件。默认 True。

    当用户在生成运营任务清单后回复“是”“生成”“导出”“都生成”“只生成 JSON”“只生成 Markdown”时使用。
    """
    action_tasks_id, action_tasks_payload = get_latest_action_tasks_from_memory()

    exported_files = {}

    if export_json:
        exported_files["json"] = export_action_tasks_to_json(
            action_tasks_payload=action_tasks_payload,
            action_tasks_id=action_tasks_id,
        )

    if export_markdown:
        exported_files["markdown"] = export_action_tasks_to_markdown(
            action_tasks_payload=action_tasks_payload,
            action_tasks_id=action_tasks_id,
        )

    if not exported_files:
        return {
            "success": False,
            "message": "没有选择任何导出格式。",
        }

    return {
        "success": True,
        "action_tasks_id": action_tasks_id,
        "exported_files": exported_files,
        "message": "运营任务清单已成功导出。",
    }
