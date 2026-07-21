# Shopify Store Ops Agent

这是一个基于 Python、LangChain 和 Shopify Admin GraphQL API 的店铺运营 Agent 项目。当前阶段聚焦只读分析：读取店铺、商品和订单数据，生成运营诊断、任务清单和商品页优化草稿。

项目不再提供 CLI、关键词路由、进程内 latest 状态或 JSON / Markdown 文件导出。上层 API、任务 Worker 或其他服务通过 Python 接口创建和调用 Agent，并自行管理会话与持久化。

## 当前能力

- 检查 Shopify 店铺连接和基础信息
- 获取商品列表与单个商品详情
- 获取最近订单并汇总热卖商品
- 诊断商品页、SEO、库存和近期销售风险
- 生成运营任务清单
- 生成符合 `ProductPageDraftOutput` 的商品页优化草稿

## 安全边界

当前 Shopify 工具只读取数据，不会自动修改店铺：

- 不修改商品标题、描述、SEO、价格或库存
- 不删除商品
- 不创建折扣
- 不发送营销邮件
- 商品页优化内容只作为人工审核草稿

## 分层结构

本轮采用渐进式的“接口层—应用层—Repository—基础设施层”：

- 接口层 `src/agent_app/`：面向未来 API、Worker、测试适配器的可编程入口
- 应用层 `src/agent_runtime/`、`src/analytics/`：Agent、工具编排和确定性诊断逻辑
- Repository：本轮没有持久化需求，因此暂不创建空实现；后续引入 PostgreSQL 时增加
- 基础设施层 `src/integrations/`：Shopify Admin API 客户端
- 数据契约 `src/schemas/`：Agent 结构化输出 schema
- 模型适配 `src/models/`：DeepSeek / OpenAI provider 选择

依赖方向保持为：接口层 → 应用层 → 基础设施层。应用结果由调用方持有，不写入模块级全局状态。

## 安装

```powershell
cd "D:\openai project\python_langchain_agent"
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env
```

然后编辑 `.env`，填入模型和 Shopify Admin API 配置。

## 可编程调用

项目不提供命令行对话入口。上层服务直接传入消息：

```python
from agent_app import create_store_ops_agent, invoke_store_ops_agent

agent = create_store_ops_agent()
result = invoke_store_ops_agent(
    [{"role": "user", "content": "生成店铺运营诊断"}],
    agent=agent,
)
```

商品页草稿接口会负责商品 ID 标准化和结构校验：

```python
from agent_app import create_product_page_draft_agent, invoke_product_page_draft_agent

agent = create_product_page_draft_agent()
draft = invoke_product_page_draft_agent(
    "gid://shopify/Product/1234567890",
    agent=agent,
)
```

## 启动检查

没有 CLI 后，“正常启动”定义为项目安装成功、公共接口可导入、Agent 可通过工厂创建。快速检查公共接口：

```powershell
.\.venv\Scripts\python -c "from agent_app import create_store_ops_agent, create_product_page_draft_agent; print('agent_app import: OK')"
```

## 测试

```powershell
.\.venv\Scripts\python -m pytest
```

测试默认走离线逻辑，不需要真实 Shopify 或模型 API 调用。
