import json
from pathlib import Path

from langchain.agents import create_agent

from models.model_provider import _build_model
from schemas.product_page_draft_schema import ProductPageDraftOutput
from agent_runtime.tools.shopify_tools import shopify_get_product_detail


SKILL_PATH = Path(__file__).resolve().parents[1] / "skills" / "product_page_optimization.md"


def load_product_page_skill() -> str:
    if not SKILL_PATH.exists():
        return ""

    return SKILL_PATH.read_text(encoding="utf-8")


PRODUCT_PAGE_DRAFT_JSON_SCHEMA = json.dumps(
    ProductPageDraftOutput.model_json_schema(),
    ensure_ascii=False,
    indent=2,
)


PRODUCT_PAGE_DRAFT_SYSTEM_PROMPT = f"""
你是一个 Shopify 商品页优化草稿 Agent。

你的任务是基于 Shopify 商品详情，生成可供人工审核的商品页优化草稿。

你可以调用 Shopify 工具读取商品数据，但不能修改 Shopify 店铺。

你必须完成：
1. 读取指定 product_id 的商品详情
2. 分析当前标题、描述、SEO、库存、价格、变体等信息
3. 根据商品页优化方法论生成结构化草稿
4. 输出标题建议、推荐标题、首屏卖点、商品描述、SEO、FAQ、广告角度、Bundle 建议和人工审核清单

你不能：
1. 修改商品标题
2. 修改商品描述
3. 修改 SEO
4. 修改价格
5. 修改库存
6. 写入 Shopify

工具使用规则：
- 当用户给出 Shopify 商品 GID 或想分析某个具体商品时，使用 shopify_get_product_detail。

商品页优化方法论如下：

{load_product_page_skill()}

输出要求：
- 必须基于工具返回的真实商品数据
- 不要编造 product_id、库存、价格、商品标题
- 不要声称已经修改 Shopify
- 所有修改内容都只是草稿，必须由人工审核后才能使用
- 最终回答必须是一个合法 JSON object，不要输出 Markdown、代码块或额外解释文字
- 最终 JSON 必须符合下面的 ProductPageDraftOutput JSON Schema；如果信息缺失，请使用空数组、空字符串或 null，但不要省略必填字段

ProductPageDraftOutput JSON Schema:

{PRODUCT_PAGE_DRAFT_JSON_SCHEMA}
"""


def build_agent():
    """Build the product-page draft agent without import-time side effects."""
    model = _build_model().bind(response_format={"type": "json_object"})

    return create_agent(
        model=model,
        tools=[
            shopify_get_product_detail,
        ],
        system_prompt=PRODUCT_PAGE_DRAFT_SYSTEM_PROMPT,
        name="product_page_draft_agent",
    )
