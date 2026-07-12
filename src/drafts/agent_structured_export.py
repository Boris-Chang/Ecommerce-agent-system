from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from drafts.product_page import extract_product_id
from schemas.product_page_draft_schema import ProductPageDraftOutput


PROJECT_ROOT = Path(__file__).resolve().parents[2]
EXPORT_DIR = PROJECT_ROOT / "data" / "exports"


def parse_json_object_from_text(text: str) -> dict[str, Any]:
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
        if start != -1 and end != -1 and end > start:
            cleaned = cleaned[start : end + 1]

    return json.loads(cleaned)


def validate_product_page_draft_output(raw_output: Any) -> dict[str, Any]:
    """Validate Agent structured output with ProductPageDraftOutput."""
    if isinstance(raw_output, str):
        raw_output = parse_json_object_from_text(raw_output)

    validated = ProductPageDraftOutput.model_validate(raw_output)
    return validated.model_dump(mode="json")


def get_final_message_content(agent_result: dict[str, Any]) -> str:
    messages = agent_result.get("messages") or []
    if not messages:
        raise ValueError("Product page draft agent returned no messages.")

    final_message = messages[-1]
    if isinstance(final_message, dict):
        content = final_message.get("content")
    else:
        content = getattr(final_message, "content", None)

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        text_parts = []
        for item in content:
            if isinstance(item, str):
                text_parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                text_parts.append(item.get("text", ""))
        return "".join(text_parts)

    raise TypeError("Product page draft agent final message content is not text.")


def extract_validated_draft_from_agent_result(
    agent_result: dict[str, Any],
) -> dict[str, Any]:
    structured_response = agent_result.get("structured_response")
    if structured_response is not None:
        return validate_product_page_draft_output(structured_response)

    return validate_product_page_draft_output(
        get_final_message_content(agent_result)
    )


def build_agent_prompt(product_id: str, user_prompt: str | None = None) -> str:
    product_id = extract_product_id(product_id) or product_id
    if user_prompt:
        if product_id not in user_prompt:
            return f"{user_prompt}\nShopify product GID: {product_id}"
        return user_prompt
    return f"请基于这个 Shopify 商品生成商品页优化草稿：{product_id}"


def invoke_product_page_draft_agent(prompt: str) -> dict[str, Any]:
    from agent_runtime.agents.product_page_draft_agent import product_page_draft_agent

    result = product_page_draft_agent.invoke(
        {
            "messages": [
                {
                    "role": "user",
                    "content": prompt,
                }
            ]
        }
    )

    return extract_validated_draft_from_agent_result(result)


def export_failed_draft_attempt_to_json(
    *,
    product_id: str,
    prompt: str,
    error: Exception,
    agent_result: dict[str, Any] | None = None,
    raw_output: Any = None,
    output_path: str | Path | None = None,
) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output_path) if output_path else (
        EXPORT_DIR / f"product_page_draft_agent_failed_{timestamp}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)

    payload: dict[str, Any] = {
        "export_type": "product_page_draft_agent_failed_attempt",
        "validated_by": "ProductPageDraftOutput",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "product_id": product_id,
        "prompt": prompt,
        "error": {
            "type": type(error).__name__,
            "message": str(error),
        },
        "raw_output": raw_output,
    }

    if isinstance(error, ValidationError):
        payload["error"]["details"] = error.errors()

    if agent_result is not None:
        try:
            payload["final_message_content"] = get_final_message_content(agent_result)
        except Exception as final_message_error:
            payload["final_message_error"] = {
                "type": type(final_message_error).__name__,
                "message": str(final_message_error),
            }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2, default=str)

    return path


def invoke_product_page_draft_agent_with_failure_export(
    *,
    product_id: str,
    prompt: str,
) -> dict[str, Any]:
    from agent_runtime.agents.product_page_draft_agent import product_page_draft_agent

    agent_result = None
    raw_output = None

    try:
        agent_result = product_page_draft_agent.invoke(
            {
                "messages": [
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ]
            }
        )
        raw_output = get_final_message_content(agent_result)
        return extract_validated_draft_from_agent_result(agent_result)
    except Exception as exc:
        failure_path = export_failed_draft_attempt_to_json(
            product_id=product_id,
            prompt=prompt,
            error=exc,
            agent_result=agent_result,
            raw_output=raw_output,
        )
        raise RuntimeError(
            f"Product page draft structured validation failed. "
            f"Failure details exported to: {failure_path}"
        ) from exc


def export_validated_draft_to_json(
    *,
    product_id: str,
    prompt: str,
    validated_draft: dict[str, Any],
    output_path: str | Path | None = None,
) -> Path:
    EXPORT_DIR.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = Path(output_path) if output_path else (
        EXPORT_DIR / f"product_page_draft_agent_structured_{timestamp}.json"
    )
    path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "export_type": "product_page_draft_agent_structured_response",
        "validated_by": "ProductPageDraftOutput",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "product_id": product_id,
        "prompt": prompt,
        "data": validated_draft,
    }

    with open(path, "w", encoding="utf-8") as file:
        json.dump(payload, file, ensure_ascii=False, indent=2)

    return path


def run_agent_structured_export(
    *,
    product_id: str,
    user_prompt: str | None = None,
    output_path: str | Path | None = None,
) -> Path:
    normalized_product_id = extract_product_id(product_id)
    if not normalized_product_id:
        raise ValueError(
            "product_id must be a Shopify product GID or numeric product ID."
        )

    prompt = build_agent_prompt(normalized_product_id, user_prompt)
    validated_draft = invoke_product_page_draft_agent_with_failure_export(
        product_id=normalized_product_id,
        prompt=prompt,
    )
    return export_validated_draft_to_json(
        product_id=normalized_product_id,
        prompt=prompt,
        validated_draft=validated_draft,
        output_path=output_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Call product_page_draft_agent, validate structured_response with "
            "ProductPageDraftOutput, and export the validated result to JSON."
        )
    )
    parser.add_argument(
        "product_id",
        help="Shopify product GID, for example gid://shopify/Product/1234567890.",
    )
    parser.add_argument(
        "--prompt",
        help="Optional full prompt. If omitted, a default product page draft prompt is used.",
    )
    parser.add_argument(
        "--output",
        help="Optional JSON output path. Defaults to data/exports/.",
    )

    args = parser.parse_args()

    if not extract_product_id(args.product_id):
        raise SystemExit(
            "product_id must be a Shopify product GID or numeric product ID like 1234567890."
        )

    output_path = run_agent_structured_export(
        product_id=args.product_id,
        user_prompt=args.prompt,
        output_path=args.output,
    )

    print(f"Validated ProductPageDraftOutput JSON exported: {output_path}")


if __name__ == "__main__":
    main()
