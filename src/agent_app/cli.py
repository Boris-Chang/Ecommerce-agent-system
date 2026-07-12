import sys
import traceback

from drafts.agent_structured_export import extract_validated_draft_from_agent_result
from drafts.export_runner import export_latest_product_page_draft
from drafts.product_page import extract_product_id, generate_product_page_draft
from agent_runtime.tools.publish_product_page_draft import (
    shopify_publish_product_page_draft,
)
from reports.session_store import save_latest_product_page_draft_in_memory


def configure_stdio() -> None:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def clean_text(value: str) -> str:
    return value.encode("utf-8", errors="replace").decode("utf-8", errors="replace")


def clean_for_model(value):
    if isinstance(value, str):
        return clean_text(value)
    if isinstance(value, list):
        return [clean_for_model(item) for item in value]
    if isinstance(value, dict):
        return {
            clean_for_model(key): clean_for_model(item)
            for key, item in value.items()
        }
    return value


def clean_messages_for_model(messages: list) -> list:
    cleaned_messages = []

    for message in messages:
        if isinstance(message, dict):
            cleaned_messages.append(clean_for_model(message))
            continue

        content = getattr(message, "content", None)
        if content is not None:
            message.content = clean_for_model(content)
        cleaned_messages.append(message)

    return cleaned_messages


def is_product_page_draft_request(user_input: str) -> bool:
    text = user_input.lower()
    keywords = [
        "商品优化",
        "优化商品",
        "商品页",
        "优化草稿",
        "标题",
        "描述",
        "卖点",
        "广告角度",
        "seo",
        "faq",
        "product page",
        "product draft",
    ]
    return any(keyword.lower() in text for keyword in keywords)


def format_agent_route_message(agent_name: str) -> str:
    return f"当前调用 Agent：{agent_name}"


def format_product_page_validation_message() -> str:
    return "结构化校验：ProductPageDraftOutput 通过；以下为 CLI 摘要渲染。"


def is_positive_export_reply(user_input: str) -> bool:
    positive_words = [
        "是",
        "生成",
        "导出",
        "都生成",
        "保存",
        "yes",
        "export",
    ]
    return user_input.strip().lower() in positive_words


def is_negative_export_reply(user_input: str) -> bool:
    negative_words = [
        "不用",
        "否",
        "不生成",
        "不导出",
        "no",
        "nope",
    ]
    return user_input.strip().lower() in negative_words


def is_publish_reply(user_input: str) -> bool:
    publish_words = [
        "发布",
        "同步",
        "推送",
        "n8n",
        "publish",
        "sync",
    ]
    text = user_input.strip().lower()
    return any(word.lower() in text for word in publish_words)


def parse_export_format(user_input: str) -> tuple[bool, bool]:
    text = user_input.lower()

    if "json" in text and "markdown" not in text and "md" not in text:
        return True, False

    if "markdown" in text or "md" in text:
        if "json" not in text:
            return False, True

    return True, True


def render_product_page_draft(draft: dict) -> str:
    lines = []

    snapshot = draft.get("current_product_snapshot", {})
    diagnosis = draft.get("diagnosis", {})
    seo = draft.get("seo", {})

    lines.append("商品页优化草稿已生成：\n")
    lines.append(f"当前商品：{snapshot.get('current_title')}")
    lines.append(f"Product ID：{snapshot.get('product_id')}")
    lines.append(f"库存：{snapshot.get('total_inventory')}")
    lines.append(f"价格区间：{snapshot.get('price_range')}")
    lines.append("")

    lines.append("一、整体诊断")
    lines.append(diagnosis.get("overall_assessment", ""))
    lines.append("")

    lines.append("二、主要问题")
    for issue in diagnosis.get("main_issues", []):
        lines.append(
            f"- [{issue.get('priority')}] {issue.get('issue_type')}: {issue.get('explanation')}"
        )
    lines.append("")

    lines.append("三、推荐标题")
    lines.append(draft.get("recommended_title", ""))
    lines.append("")

    lines.append("四、首屏卖点")
    for bullet in draft.get("hero_bullets", []):
        lines.append(f"- {bullet}")
    lines.append("")

    lines.append("五、SEO")
    lines.append(f"- SEO Title：{seo.get('seo_title')}")
    lines.append(f"- SEO Description：{seo.get('seo_description')}")
    lines.append("")

    lines.append("六、人工审核清单")
    for item in draft.get("manual_review_checklist", []):
        lines.append(f"- [ ] {item}")

    return "\n".join(lines)


def _load_store_ops_agent():
    from agent_runtime.agents.store_ops_agent import store_ops_agent

    return store_ops_agent


def _load_product_page_draft_agent():
    from agent_runtime.agents.product_page_draft_agent import product_page_draft_agent

    return product_page_draft_agent


def build_product_page_draft_agent_prompt(user_input: str) -> str:
    product_id = extract_product_id(user_input)
    if product_id and product_id not in user_input:
        return f"{user_input}\nShopify product GID: {product_id}"
    return user_input


def generate_product_page_draft_via_agent(
    user_input: str,
    product_page_draft_agent=None,
) -> dict:
    agent = product_page_draft_agent or _load_product_page_draft_agent()
    prompt = build_product_page_draft_agent_prompt(user_input)
    result = agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        }
    )

    return clean_for_model(extract_validated_draft_from_agent_result(result))


def main() -> None:
    configure_stdio()

    print("Shopify Store Ops Assistant")
    print("输入 exit 退出\n")

    store_ops_messages = []
    last_context = None
    store_ops_agent = None
    product_page_draft_agent = None

    while True:
        user_input = clean_text(input("你想让 Shopify Agent 做什么？\n> "))

        if user_input.lower() in ["exit", "quit"]:
            break

        if last_context == "product_page_draft_export_pending":
            if is_negative_export_reply(user_input):
                print("\n好的，本次不生成商品页优化草稿文档。\n")
                last_context = None
                continue

            if is_publish_reply(user_input):
                result = shopify_publish_product_page_draft.func()

                print("\n同步结果：\n")
                print(result)
                print("\n" + "-" * 80 + "\n")

                last_context = None
                continue

            if (
                is_positive_export_reply(user_input)
                or "json" in user_input.lower()
                or "markdown" in user_input.lower()
                or "md" in user_input.lower()
            ):
                export_json, export_markdown = parse_export_format(user_input)
                result = export_latest_product_page_draft(
                    export_json=export_json,
                    export_markdown=export_markdown,
                )

                print("\n导出结果：\n")
                print(result)
                print("\n" + "-" * 80 + "\n")

                last_context = None
                continue

        if is_product_page_draft_request(user_input):
            if not extract_product_id(user_input):
                print("\n无法生成商品页优化草稿：请在请求中提供 Shopify 商品 GID，例如 gid://shopify/Product/1234567890。\n")
                print("\n" + "-" * 80 + "\n")
                continue

            print("")
            print(format_agent_route_message("product_page_draft_agent"))

            try:
                if product_page_draft_agent is None:
                    product_page_draft_agent = _load_product_page_draft_agent()

                draft_dict = generate_product_page_draft_via_agent(
                    user_input,
                    product_page_draft_agent=product_page_draft_agent,
                )
            except Exception as exc:
                print("\n商品页优化 Agent 执行失败，尝试使用本地模板生成草稿：")
                print(f"{type(exc).__name__}: {exc}\n")
                try:
                    draft_dict = generate_product_page_draft(user_input)
                except ValueError as fallback_exc:
                    print(f"\n无法生成商品页优化草稿：{fallback_exc}\n")
                    print("\n" + "-" * 80 + "\n")
                    continue

            draft_id = save_latest_product_page_draft_in_memory(draft_dict)

            print("")
            print(format_product_page_validation_message())
            print("\nAgent 输出摘要：\n")
            print(render_product_page_draft(draft_dict))
            print("")
            print(f"Draft ID：{draft_id}")
            print("")
            print("CLI 后续提示：")
            print("是否需要将这份商品页优化草稿导出为 JSON / Markdown 文档？")
            print("回复“是”将默认同时生成 JSON 和 Markdown；也可以回复“只生成 JSON”或“只生成 Markdown”。")
            print("也可以回复“同步”或“发布到 n8n”，将这份商品页优化草稿 JSON schema 结果同步到 n8n。")
            print("\n" + "-" * 80 + "\n")

            last_context = "product_page_draft_export_pending"
            continue

        store_ops_messages.append(
            {
                "role": "user",
                "content": user_input,
            }
        )

        if store_ops_agent is None:
            store_ops_agent = _load_store_ops_agent()

        try:
            print("")
            print(format_agent_route_message("store_ops_agent"))
            store_ops_messages = clean_messages_for_model(store_ops_messages)
            result = store_ops_agent.invoke({"messages": store_ops_messages})
        except Exception as exc:
            store_ops_messages.pop()
            print("\nAgent 执行失败：\n")
            print(f"{type(exc).__name__}: {exc}")
            print("\n详细错误：")
            traceback.print_exc()
            print("\n程序未退出，你可以调整问题后继续输入。")
            print("\n" + "-" * 80 + "\n")
            continue

        store_ops_messages = result["messages"]
        store_ops_messages = clean_messages_for_model(store_ops_messages)
        final_message = store_ops_messages[-1]

        print("\nAgent 输出：\n")
        print(final_message.content)
        print("\n" + "-" * 80 + "\n")
