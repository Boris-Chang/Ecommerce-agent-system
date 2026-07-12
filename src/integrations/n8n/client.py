import os

import httpx
from dotenv import load_dotenv


async def publish_to_n8n(payload: dict) -> dict:
    load_dotenv()
    webhook_url = os.getenv("N8N_SHOPIFY_AGENT_WEBHOOK_URL")
    secret = os.getenv("N8N_AGENT_SECRET")

    if not webhook_url:
        raise ValueError("Missing N8N_SHOPIFY_AGENT_WEBHOOK_URL")

    headers = {
        "Content-Type": "application/json",
    }
    if secret:
        headers["Jiyuan-Agent-Secret"] = secret

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            webhook_url,
            json=payload,
            headers=headers,
        )

    response.raise_for_status()

    return {
        "success": True,
        "status_code": response.status_code,
        "response_text": response.text,
    }


class N8NClient:
    """Client wrapper for publishing events to n8n."""

    async def publish_event(self, payload: dict) -> dict:
        return await publish_to_n8n(payload)


__all__ = ["N8NClient", "publish_to_n8n"]


# async def main() -> int:
#     load_dotenv()
#     payload = {
#                 "event_type": "action_tasks.created",
#                 "source": "shopify_agent",
#                 "version": "v1.4",
#                 "store_domain": "demo-store.myshopify.com",
#                 "run_id": "test-run-action-tasks-003",
#                 "generated_at": "2026-06-16T10:00:00Z",
#                 "data": {
#                     "tasks": [
#                     {
#                         "product_id": "gid://shopify/Product/123",
#                         "product_title": "Pet Cooling Mat",
#                         "priority": "high",
#                         "task_type": "product_page_optimization",
#                         "task": "补充商品描述和 SEO description",
#                         "reason": "当前商品描述为空，影响转化和搜索展示"
#                     },
#                     {
#                         "product_id": "gid://shopify/Product/456",
#                         "product_title": "Dog Travel Water Bottle",
#                         "priority": "medium",
#                         "task_type": "seo",
#                         "task": "优化商品标题关键词",
#                         "reason": "当前标题没有体现使用场景，搜索意图不清晰"
#                     }
#                     ]
#                 },
#                 "meta": {
#                     "target": "feishu"
#                 }
#             }

#     try:
#         result = await publish_to_n8n(payload)
#     except httpx.HTTPStatusError as exc:
#         response = exc.response
#         print(
#             json.dumps(
#                 {
#                     "success": False,
#                     "status_code": response.status_code,
#                     "response_text": response.text,
#                     "message": "n8n responded, but the webhook returned an error.",
#                 },
#                 ensure_ascii=False,
#                 indent=2,
#             )
#         )
#         return 1
#     except Exception as exc:
#         print(
#             json.dumps(
#                 {
#                     "success": False,
#                     "error": type(exc).__name__,
#                     "message": str(exc),
#                 },
#                 ensure_ascii=False,
#                 indent=2,
#             )
#         )
#         return 1

#     print(json.dumps(result, ensure_ascii=False, indent=2))
#     return 0


# if __name__ == "__main__":
#     raise SystemExit(asyncio.run(main()))
