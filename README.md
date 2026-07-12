# Shopify Store Ops Assistant

这是一个基于 Python、LangChain 和 Shopify Admin GraphQL API 的店铺运营助手。当前阶段聚焦只读分析：读取店铺、商品和订单数据，生成运营诊断、任务清单和商品页优化草稿，并导出 JSON / Markdown 文件。

## 当前能力

- 检查 Shopify 店铺连接和基础信息
- 获取商品列表与单个商品详情
- 获取最近订单并汇总热卖商品
- 诊断商品页、SEO、库存和近期销售风险
- 生成店铺运营诊断报告
- 生成运营任务清单
- 为单个商品生成商品页优化草稿
- 将报告、任务清单和商品页草稿导出为 JSON / Markdown

## 安全边界

当前工具只读取 Shopify 数据，不会自动修改店铺：

- 不修改商品标题、描述、SEO、价格或库存
- 不删除商品
- 不创建折扣
- 不发送营销邮件
- 商品页优化内容只作为人工审核草稿

## 安装

```powershell
cd "D:\openai project\python_langchain_agent"
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env
```

然后编辑 `.env`，填入模型和 Shopify Admin API 配置。

## 运行

直接运行源码入口：

```powershell
.\.venv\Scripts\python .\src\main.py
```

或使用安装后的命令：

```powershell
.\.venv\Scripts\shopify-agent
```

示例输入：

```text
检查店铺连接是否正常
查看前 5 个商品
帮我生成一份当前店铺商品运营诊断报告
帮我生成运营任务清单
帮我为这个商品生成商品页优化草稿：gid://shopify/Product/1234567890
```

## 测试

```powershell
.\.venv\Scripts\python -m pytest
```

测试默认走离线逻辑，不需要真实 Shopify 或模型 API 调用。

## 项目结构

- `src/main.py`：兼容入口，调用 `agent_app.cli`
- `src/agent_app/cli.py`：CLI 对话和路由逻辑
- `src/agent_runtime/agents/`：LangChain Agent 定义
- `src/agent_runtime/tools/`：LangChain 工具封装
- `src/agent_runtime/skills/`：Agent 使用的方法论和领域知识
- `src/integrations/shopify/`：Shopify Admin API client、GraphQL 查询和读取服务
- `src/integrations/n8n/`：n8n webhook HTTP client
- `src/analytics/`：店铺诊断和运营任务生成逻辑
- `src/reports/`：报告会话状态和报告/任务清单导出
- `src/drafts/`：商品页草稿生成和草稿导出
- `src/models/`：模型 provider 选择
- `src/schemas/`：结构化输出 schema
- `data/exports/`：导出的 JSON / Markdown 文件
- `tests/`：离线单元测试

