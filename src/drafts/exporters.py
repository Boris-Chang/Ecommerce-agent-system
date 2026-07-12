import json
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = PROJECT_ROOT / "data" / "exports"
EXPORT_DIR.mkdir(parents=True, exist_ok=True)


def export_product_page_draft_to_json(
    draft_payload: dict[str, Any],
    draft_id: str,
    file_name: str | None = None,
) -> str:
    """将商品页优化草稿导出为 JSON 文件。"""
    if file_name is None:
        file_name = f"{draft_id}.json"

    file_path = EXPORT_DIR / file_name

    payload = {
        "draft_id": draft_id,
        "data": draft_payload,
    }

    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    return str(file_path)


def export_product_page_draft_to_markdown(
    draft_payload: dict[str, Any],
    draft_id: str,
    file_name: str | None = None,
) -> str:
    """将商品页优化草稿导出为 Markdown 文件。"""
    if file_name is None:
        file_name = f"{draft_id}.md"

    file_path = EXPORT_DIR / file_name

    snapshot = draft_payload.get("current_product_snapshot", {})
    diagnosis = draft_payload.get("diagnosis", {})
    seo = draft_payload.get("seo", {})

    lines = [
        "# Shopify 商品页优化草稿",
        "",
        f"- Draft ID：`{draft_id}`",
        f"- Product ID：`{snapshot.get('product_id')}`",
        f"- 当前商品标题：{snapshot.get('current_title')}",
        f"- Handle：`{snapshot.get('handle')}`",
        "",
        "## 一、当前商品概览",
        "",
        f"- 状态：{snapshot.get('status')}",
        f"- 库存：{snapshot.get('total_inventory')}",
        f"- 价格区间：{snapshot.get('price_range')}",
        "",
        "## 二、商品页诊断",
        "",
        diagnosis.get("overall_assessment", ""),
        "",
    ]

    main_issues = diagnosis.get("main_issues", [])
    if main_issues:
        lines.append("### 主要问题")
        lines.append("")
        for issue in main_issues:
            lines.append(
                f"- **[{issue.get('priority')}] {issue.get('issue_type')}**：{issue.get('explanation')}"
            )
        lines.append("")

    lines.extend(["## 三、标题建议", ""])
    for index, item in enumerate(draft_payload.get("title_options", []), start=1):
        lines.append(f"### 方案 {index}")
        lines.append(f"- 标题：{item.get('title')}")
        lines.append(f"- 理由：{item.get('rationale')}")
        lines.append("")

    lines.extend([
        "### 推荐标题",
        "",
        draft_payload.get("recommended_title", ""),
        "",
        "## 四、首屏卖点 Bullets",
        "",
    ])
    for bullet in draft_payload.get("hero_bullets", []):
        lines.append(f"- {bullet}")
    lines.append("")

    lines.extend([
        "## 五、商品描述草稿",
        "",
        draft_payload.get("product_description_markdown", ""),
        "",
        "## 六、SEO 草稿",
        "",
        f"- SEO Title：{seo.get('seo_title')}",
        f"- SEO Description：{seo.get('seo_description')}",
        "",
    ])

    faq = draft_payload.get("faq", [])
    if faq:
        lines.extend(["## 七、FAQ", ""])
        for item in faq:
            lines.append(f"### Q: {item.get('question')}")
            lines.append(f"A: {item.get('answer')}")
            lines.append("")

    ad_angles = draft_payload.get("ad_angles", [])
    if ad_angles:
        lines.extend(["## 八、广告角度", ""])
        for item in ad_angles:
            lines.append(f"### {item.get('angle')}")
            lines.append(f"- Hook：{item.get('hook')}")
            lines.append(f"- Reason：{item.get('reason')}")
            lines.append("")

    bundle_suggestions = draft_payload.get("bundle_suggestions", [])
    if bundle_suggestions:
        lines.extend(["## 九、Bundle 建议", ""])
        for item in bundle_suggestions:
            lines.append(f"- {item.get('bundle_idea')}：{item.get('reason')}")
        lines.append("")

    checklist = draft_payload.get("manual_review_checklist", [])
    if checklist:
        lines.extend(["## 十、人工审核清单", ""])
        for item in checklist:
            lines.append(f"- [ ] {item}")
        lines.append("")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return str(file_path)
