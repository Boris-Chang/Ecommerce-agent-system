from collections import defaultdict
from typing import Any

from integrations.shopify.service import (
    get_products_for_audit,
    get_recent_orders,
)


def _strip_html_roughly(html: str | None) -> str:
    """
    简单移除 HTML 标签，用于判断描述是否为空或过短。

    这不是严格 HTML parser，但足够支撑当前诊断逻辑。
    """
    if not html:
        return ""

    import re

    text = re.sub(r"<[^>]+>", "", html)
    return text.strip()


def _get_variants(product: dict[str, Any]) -> list[dict[str, Any]]:
    return [edge["node"] for edge in product.get("variants", {}).get("edges", [])]


def _analyze_product_page(product: dict[str, Any]) -> list[dict[str, Any]]:
    """分析单个商品页的内容问题。"""
    issues = []

    title = product.get("title") or ""
    description = _strip_html_roughly(product.get("descriptionHtml"))
    seo = product.get("seo") or {}
    product_type = product.get("productType") or ""
    variants = _get_variants(product)

    if len(title.strip()) < 8:
        issues.append(
            {
                "issue_type": "weak_title",
                "priority": "medium",
                "evidence": f"商品标题较短：{title}",
                "recommendation": "标题建议加入核心品类词、使用场景或关键卖点。",
            }
        )

    if len(description) < 80:
        issues.append(
            {
                "issue_type": "weak_description",
                "priority": "high",
                "evidence": "商品描述内容较少，可能不足以支撑转化。",
                "recommendation": "补充使用场景、核心卖点、适用人群、规格信息和 FAQ。",
            }
        )

    if not seo.get("title"):
        issues.append(
            {
                "issue_type": "missing_seo_title",
                "priority": "medium",
                "evidence": "SEO title 为空。",
                "recommendation": "补充包含品类关键词和核心卖点的 SEO title。",
            }
        )

    if not seo.get("description"):
        issues.append(
            {
                "issue_type": "missing_seo_description",
                "priority": "medium",
                "evidence": "SEO description 为空。",
                "recommendation": "补充简洁的 SEO description，突出购买理由。",
            }
        )

    if not product_type:
        issues.append(
            {
                "issue_type": "missing_product_type",
                "priority": "low",
                "evidence": "商品 productType 为空。",
                "recommendation": "补充 productType，方便分类、筛选和后续运营分析。",
            }
        )

    if not variants:
        issues.append(
            {
                "issue_type": "missing_variants",
                "priority": "high",
                "evidence": "商品没有变体信息。",
                "recommendation": "检查商品是否正确配置价格、SKU 和库存。",
            }
        )

    for variant in variants:
        if not variant.get("price"):
            issues.append(
                {
                    "issue_type": "missing_price",
                    "priority": "high",
                    "evidence": f"变体 {variant.get('title')} 缺少价格。",
                    "recommendation": "补充变体价格，否则商品无法正常销售。",
                }
            )

    return issues


def _analyze_inventory(
    product: dict[str, Any],
    low_inventory_threshold: int,
) -> list[dict[str, Any]]:
    """分析库存风险。"""
    issues = []

    total_inventory = product.get("totalInventory")

    if total_inventory is None:
        issues.append(
            {
                "issue_type": "unknown_inventory",
                "priority": "medium",
                "evidence": "商品总库存未知。",
                "recommendation": "检查库存追踪设置。",
            }
        )
        return issues

    if total_inventory <= 0:
        issues.append(
            {
                "issue_type": "out_of_stock",
                "priority": "high",
                "evidence": f"当前总库存为 {total_inventory}。",
                "recommendation": "如果商品仍准备销售，需要补货；如果不再销售，应检查商品状态或页面展示。",
            }
        )
    elif total_inventory <= low_inventory_threshold:
        issues.append(
            {
                "issue_type": "low_inventory",
                "priority": "medium",
                "evidence": f"当前总库存为 {total_inventory}，低于阈值 {low_inventory_threshold}。",
                "recommendation": "如果近期有销量，建议优先补货，避免推广期间断货。",
            }
        )

    return issues


def _summarize_recent_orders(orders: list[dict[str, Any]]) -> dict[str, Any]:
    """汇总最近订单中的商品销量和预估收入。"""
    product_sales = defaultdict(int)
    revenue = 0.0
    currency = None

    for order in orders:
        money = order.get("totalPriceSet", {}).get("shopMoney", {})

        amount = money.get("amount")
        currency = currency or money.get("currencyCode")

        if amount:
            try:
                revenue += float(amount)
            except ValueError:
                pass

        line_items = order.get("lineItems", {}).get("edges", [])

        for item_edge in line_items:
            item = item_edge["node"]
            title = item.get("title") or "Unknown Product"
            quantity = item.get("quantity") or 0
            product_sales[title] += quantity

    top_selling_products = sorted(
        [
            {
                "title": title,
                "quantity": quantity,
            }
            for title, quantity in product_sales.items()
        ],
        key=lambda x: x["quantity"],
        reverse=True,
    )

    return {
        "order_count": len(orders),
        "estimated_revenue": round(revenue, 2),
        "currency": currency,
        "top_selling_products": top_selling_products,
    }


def generate_store_diagnosis_report(
    product_limit: int = 10,
    order_limit: int = 10,
    low_inventory_threshold: int = 5,
) -> dict[str, Any]:
    """生成 Shopify 店铺商品运营诊断报告。"""
    products = get_products_for_audit(product_limit)
    orders = get_recent_orders(order_limit)

    order_summary = _summarize_recent_orders(orders)

    sold_product_titles = {
        item["title"] for item in order_summary["top_selling_products"]
    }

    product_reports = []
    high_priority_count = 0
    medium_priority_count = 0
    low_priority_count = 0

    for product in products:
        page_issues = _analyze_product_page(product)
        inventory_issues = _analyze_inventory(product, low_inventory_threshold)

        issues = page_issues + inventory_issues

        title = product.get("title") or ""
        has_recent_sales = title in sold_product_titles

        if not has_recent_sales and (product.get("totalInventory") or 0) > 0:
            issues.append(
                {
                    "issue_type": "has_inventory_but_no_recent_sales",
                    "priority": "medium",
                    "evidence": f"该商品有库存，但最近 {order_limit} 个订单中未出现。",
                    "recommendation": "建议检查商品页吸引力、价格、广告入口，或评估是否适合做 bundle。",
                }
            )

        for issue in issues:
            if issue["priority"] == "high":
                high_priority_count += 1
            elif issue["priority"] == "medium":
                medium_priority_count += 1
            else:
                low_priority_count += 1

        product_reports.append(
            {
                "id": product.get("id"),
                "title": title,
                "handle": product.get("handle"),
                "status": product.get("status"),
                "product_type": product.get("productType"),
                "vendor": product.get("vendor"),
                "total_inventory": product.get("totalInventory"),
                "has_recent_sales": has_recent_sales,
                "issues": issues,
            }
        )

    products_with_issues = [
        product for product in product_reports if product["issues"]
    ]

    action_items = _build_action_items(
        product_reports=product_reports,
        order_summary=order_summary,
    )

    return {
        "report_meta": {
            "product_limit": product_limit,
            "order_limit": order_limit,
            "low_inventory_threshold": low_inventory_threshold,
        },
        "summary": {
            "checked_product_count": len(products),
            "recent_order_count": order_summary["order_count"],
            "estimated_revenue": order_summary["estimated_revenue"],
            "currency": order_summary["currency"],
            "products_with_issues_count": len(products_with_issues),
            "high_priority_issue_count": high_priority_count,
            "medium_priority_issue_count": medium_priority_count,
            "low_priority_issue_count": low_priority_count,
        },
        "top_selling_products": order_summary["top_selling_products"][:5],
        "product_reports": product_reports,
        "action_items": action_items,
    }


def _build_action_items(
    product_reports: list[dict[str, Any]],
    order_summary: dict[str, Any],
) -> list[str]:
    """根据诊断结果生成行动清单。"""
    action_items = []

    high_priority_products = []

    for product in product_reports:
        high_issues = [
            issue for issue in product["issues"] if issue["priority"] == "high"
        ]

        if high_issues:
            high_priority_products.append(product["title"])

    if high_priority_products:
        action_items.append(
            "优先处理高优先级问题商品："
            + "、".join(high_priority_products[:5])
        )

    if order_summary["top_selling_products"]:
        top = order_summary["top_selling_products"][0]
        action_items.append(
            f"最近订单中表现最好的是「{top['title']}」，销量 {top['quantity']} 件，建议检查库存并重点优化商品页或广告素材。"
        )

    low_inventory_products = [
        product["title"]
        for product in product_reports
        for issue in product["issues"]
        if issue["issue_type"] in ["low_inventory", "out_of_stock"]
    ]

    if low_inventory_products:
        action_items.append(
            "检查库存风险商品："
            + "、".join(list(dict.fromkeys(low_inventory_products))[:5])
        )

    weak_page_products = [
        product["title"]
        for product in product_reports
        for issue in product["issues"]
        if issue["issue_type"]
        in [
            "weak_description",
            "weak_title",
            "missing_seo_title",
            "missing_seo_description",
        ]
    ]

    if weak_page_products:
        action_items.append(
            "优化商品页内容："
            + "、".join(list(dict.fromkeys(weak_page_products))[:5])
        )

    if not action_items:
        action_items.append("当前未发现明显高优先级问题，可以继续观察订单和库存变化。")

    return action_items
