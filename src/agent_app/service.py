from __future__ import annotations

import json
import re
from typing import Any, Iterable

from schemas.product_page_draft_schema import ProductPageDraftOutput


PRODUCT_ID_RE = re.compile(r"gid://shopify/Product/\d+")
NUMERIC_PRODUCT_ID_RE = re.compile(r"(?<!\d)(\d{8,})(?!\d)")


def create_store_ops_agent():
    """Create the store operations agent for an API, worker, or test adapter."""
    from agent_runtime.agents.store_ops_agent import build_agent

    return build_agent()


def create_product_page_draft_agent():
    """Create the product-page draft agent for an API, worker, or test adapter."""
    from agent_runtime.agents.product_page_draft_agent import build_agent

    return build_agent()


def invoke_store_ops_agent(
    messages: Iterable[dict[str, Any]],
    *,
    agent=None,
) -> dict[str, Any]:
    """Invoke the store operations agent with explicit caller-owned messages."""
    runtime_agent = agent or create_store_ops_agent()
    return runtime_agent.invoke({"messages": list(messages)})


def normalize_product_id(value: str) -> str:
    """Normalize a Shopify product GID or a numeric product ID to a GID."""
    gid_match = PRODUCT_ID_RE.search(value)
    if gid_match:
        return gid_match.group(0)

    numeric_match = NUMERIC_PRODUCT_ID_RE.search(value)
    if numeric_match:
        return f"gid://shopify/Product/{numeric_match.group(1)}"

    raise ValueError("product_id must be a Shopify product GID or numeric product ID.")


def build_product_page_draft_prompt(
    product_id: str,
    user_prompt: str | None = None,
) -> str:
    normalized_product_id = normalize_product_id(product_id)
    if not user_prompt:
        return f"请基于这个 Shopify 商品生成商品页优化草稿：{normalized_product_id}"
    if normalized_product_id in user_prompt:
        return user_prompt
    return f"{user_prompt}\nShopify product GID: {normalized_product_id}"


def parse_json_object_from_text(text: str) -> dict[str, Any]:
    """Parse a JSON object from a plain or fenced Agent response."""
    cleaned = text.strip()
    fenced_match = re.fullmatch(
        r"```(?:json)?\s*(?P<body>.*?)\s*```",
        cleaned,
        flags=re.DOTALL | re.IGNORECASE,
    )
    if fenced_match:
        cleaned = fenced_match.group("body").strip()

    if not cleaned.startswith("{"):
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start != -1 and end > start:
            cleaned = cleaned[start : end + 1]

    return json.loads(cleaned)


def validate_product_page_draft_output(raw_output: Any) -> dict[str, Any]:
    """Validate and normalize a product-page draft Agent response."""
    if isinstance(raw_output, str):
        raw_output = parse_json_object_from_text(raw_output)
    return ProductPageDraftOutput.model_validate(raw_output).model_dump(mode="json")


def _get_final_message_content(agent_result: dict[str, Any]) -> Any:
    messages = agent_result.get("messages") or []
    if not messages:
        raise ValueError("Product page draft agent returned no messages.")

    final_message = messages[-1]
    content = (
        final_message.get("content")
        if isinstance(final_message, dict)
        else getattr(final_message, "content", None)
    )

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "".join(
            item if isinstance(item, str) else item.get("text", "")
            for item in content
            if isinstance(item, str)
            or (isinstance(item, dict) and item.get("type") == "text")
        )
    raise TypeError("Product page draft agent final message content is not text.")


def extract_product_page_draft(agent_result: dict[str, Any]) -> dict[str, Any]:
    """Extract and validate the structured product-page draft from an Agent result."""
    structured_response = agent_result.get("structured_response")
    if structured_response is not None:
        return validate_product_page_draft_output(structured_response)
    return validate_product_page_draft_output(_get_final_message_content(agent_result))


def invoke_product_page_draft_agent(
    product_id: str,
    *,
    user_prompt: str | None = None,
    agent=None,
) -> dict[str, Any]:
    """Invoke the draft agent and return a validated, in-memory result."""
    runtime_agent = agent or create_product_page_draft_agent()
    prompt = build_product_page_draft_prompt(product_id, user_prompt)
    result = runtime_agent.invoke(
        {"messages": [{"role": "user", "content": prompt}]}
    )
    return extract_product_page_draft(result)
