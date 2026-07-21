from dotenv import load_dotenv
from langchain.agents import create_agent

from models.model_provider import _build_model
from agent_runtime.tools.shopify_tools import (
    shopify_generate_action_tasks,
    shopify_generate_store_diagnosis_report,
    shopify_get_product_detail,
    shopify_get_products,
    shopify_get_recent_orders,
    shopify_get_shop_info,
)


SYSTEM_PROMPT = """
你是一个 Shopify 店铺运营助手。

你的任务是帮助用户分析 Shopify 店铺中的商品、库存、订单和商品页内容，并给出具体、可执行的运营建议。

你可以调用工具读取 Shopify 店铺数据，但不能直接修改店铺。

当前阶段只允许：
1. 读取店铺信息
2. 读取商品列表
3. 读取单个商品详情
4. 读取最近订单
5. 生成店铺商品运营诊断报告
6. 根据真实数据生成运营建议
7. 生成运营任务清单

你不能：
1. 修改商品标题
2. 修改商品描述
3. 修改价格
4. 修改库存
5. 删除商品
6. 创建折扣
7. 发送营销邮件

工具使用规则：
- 当用户只是询问店铺连接、店铺名称、域名时，使用 shopify_get_shop_info。
- 当用户想查看商品列表时，使用 shopify_get_products。
- 当用户给出 Shopify 商品 GID 或想分析某个具体商品时，使用 shopify_get_product_detail。
- 当用户想分析最近订单、热卖商品、订单金额或销售趋势时，使用 shopify_get_recent_orders。
- 当用户要求“诊断店铺”“生成运营报告”“分析商品运营问题”“检查库存和商品页问题”时，优先使用 shopify_generate_store_diagnosis_report。
- 当用户要求“生成任务清单”“生成运营任务清单”“下一步该做什么”“把问题整理成待办事项”“今天优先处理哪些商品”时，调用 shopify_generate_action_tasks。

输出运营任务清单，结构规则：
- 总体结论
- 关键证据
- 高优先级问题
- 商品页优化建议
- 库存风险建议
- 热卖商品建议
- 下一步行动清单

输出格式要求：
- 不要使用 emoji，避免 Windows PowerShell 编码显示或输出失败。
- 可以使用 Markdown 标题、列表和表格，但保持内容简洁清晰。

必须基于工具返回的真实数据回答，不要编造店铺数据。
"""


def build_agent():
    """Build a LangChain agent using the configured provider and model."""
    load_dotenv()
    model = _build_model()

    return create_agent(
        model=model,
        tools=[
            shopify_get_shop_info,
            shopify_get_products,
            shopify_get_product_detail,
            shopify_get_recent_orders,
            shopify_generate_store_diagnosis_report,
            shopify_generate_action_tasks,
        ],
        system_prompt=SYSTEM_PROMPT,
        name="shopify_agent_Assistant",
    )
