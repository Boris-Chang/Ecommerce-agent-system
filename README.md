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
- 按渠道查询 SKU 日/周销量、销售额和退款数据
- 按币种计算各渠道销量占比与净销售额占比
- 按 SKU、仓库查询在库、预占、冻结、可售和在途库存
- 查询库存覆盖、补货风险、积压风险、客户 LTV 和月度利润
- 使用版本化 Python 模型生成渠道级 SKU 周销量预测

## 安全边界

当前 Shopify 工具只读取数据，不会自动修改店铺：

- 不修改商品标题、描述、SEO、价格或库存
- 不删除商品
- 不创建折扣
- 不发送营销邮件
- 商品页优化内容只作为人工审核草稿

## 分层结构

项目采用“接口层—应用层—基础设施层”的依赖方向：

- `src/agent_app/`：面向 API、Worker 和测试适配器的可编程 Agent 入口
- `src/agent_runtime/`：Agent 创建、工具编排和运行时逻辑
- `src/application/dto/`：不可变只读 DTO，按 `sku`、`channel`、`inventory`、`customer`、`profit` 业务域分组
- `src/application/repositories/`：应用层 Repository 协议，按业务域分组
- `src/application/services/`：确定性应用服务，按 `sku`、`channel`、`inventory` 业务域分组
- `src/application/forecasting/sku_weekly/`：可版本管理的 SKU 周预测算法
- `src/infrastructure/database/repositories/`：PostgreSQL Repository 实现，同样按 `sku`、`channel`、`inventory`、`customer`、`profit` 业务域分组
- `src/web/`：FastAPI、Jinja2、Presenter、ViewModel、页面模板与静态资源
- `src/integrations/`：Shopify 等外部系统适配
- `src/schemas/`：Agent 结构化输出契约
- `src/models/`：DeepSeek / OpenAI 模型提供方选择

`application` 不依赖 `infrastructure`；基础设施实现应用层声明的协议。只读查询由 `ReadOnlyUnitOfWork` 管理事务，退出上下文时统一回滚并关闭连接。应用结果由调用方持有，不写入模块级全局状态。

## 安装

```powershell
cd "D:\openai project\python_langchain_agent"
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env
```

然后编辑 `.env`，填入模型、Shopify Admin API 和只读 PostgreSQL 应用账号配置。

PowerShell 如需激活虚拟环境：

```powershell
.\.venv\Scripts\Activate.ps1
```

也可以不激活，始终使用 `.\.venv\Scripts\python` 执行命令。

## PostgreSQL Repository

当前批准范围为 12 个只读业务 Schema、77 张业务表。候选 DDL 基线来自 `coolcool_erp_v0.2_full.sql`，其结构和 SHA-256 记录在 `db/baseline_manifest.json`。候选文件中的 `agent` Schema 和 4 张 Agent 表未纳入本轮。

应用连接通过两层方式保持只读：

- 数据库角色设置 `default_transaction_read_only=on`
- SQLAlchemy Engine 连接参数再次强制 `default_transaction_read_only=on`

Repository 当前读取以下 `analytics` 快照表：

- `analytics.v_sku_daily_sales`：SKU 日销售；周销售与渠道销售汇总由此计算
- `analytics.v_inventory_cover`：库存覆盖
- `analytics.v_customer_ltv`：客户 LTV
- `analytics.v_sku_pnl_monthly`：SKU 月度利润
- `analytics.v_channel_pnl_monthly`：渠道月度利润

这些 `analytics.v_*` 对象在 v0.2 中是普通 PostgreSQL 快照表，不是
SQL View 或 Materialized View。当前应用只负责只读查询，不包含生成或刷新
这些快照的 ETL/Worker；新订单写入 `sales.orders` 后，不会自动出现在销售、
库存覆盖、LTV 或利润快照中。

快照中的 `data_origin` 必须作为数据血缘判断依据。当前基线包含
`derived_sample`、`simulated*` 等样本或模拟来源，原始订单也可能同时包含
`shopify_live` 和模拟渠道数据。因此“运行时真实访问 PostgreSQL”不等于
“所有记录都是生产真实数据”。在生产分析前，应先完成真实渠道同步、快照刷新、
数据新鲜度检查和来源校验。

以下基础数据直接读取业务表：

- SKU 退款：`sales.refunds → sales.refund_lines → sales.order_lines → sales.orders`
- 当前库存：`inventory.inventory_balances`

SKU 销售和退款服务强制传入 `channel_account_id`，不会隐式执行跨渠道汇总。渠道销售占比是明确的跨渠道比较指标，每行仍保留渠道，且不同币种分别计算占比。物理库存按 `SKU + warehouse` 表示，不人为分配到渠道。

## 应用层分析服务

| 服务 | 主要能力 | 数据粒度 |
| --- | --- | --- |
| `SkuSalesService` | SKU 日/周销量及销售额 | 渠道账户 + SKU + 日/周 + 币种 |
| `SkuRefundService` | SKU 日/周退款次数、订单数、数量及金额 | 渠道账户 + SKU + 日/周 + 原因 + 状态 + 币种 |
| `ChannelSalesShareService` | 渠道销量占比、净销售额占比 | 渠道账户 + 币种 + 查询周期 |
| `InventoryBalanceService` | 在库、预占、冻结、可售、在途数量 | SKU + 仓库 |
| `InventoryRiskService` | 补货风险、积压风险 | SKU + 仓库 |
| `SkuWeeklyForecastService` | 未来 1–52 周 P50/P90 销量预测 | 渠道账户 + SKU + 周 |

公共服务可从统一入口导入：

```python
from application.services import (
    ChannelSalesShareService,
    InventoryBalanceService,
    InventoryRiskService,
    SkuRefundService,
    SkuSalesService,
    SkuWeeklyForecastService,
)
```

只读数据库调用示例：

```python
from datetime import date

from application.services import (
    ChannelSalesShareService,
    InventoryBalanceService,
    SkuSalesService,
)
from infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork

engine = create_database_engine()
session_factory = create_session_factory(engine)

with ReadOnlyUnitOfWork(session_factory) as unit_of_work:
    daily_sales = SkuSalesService(unit_of_work.sales).list_daily_sales(
        channel_account_id="CA_SHOPIFY_US",
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )
    channel_shares = ChannelSalesShareService(
        unit_of_work.channel_sales
    ).list_sales_shares(
        start_date=date(2026, 7, 1),
        end_date=date(2026, 7, 31),
    )
    inventory = InventoryBalanceService(
        unit_of_work.inventory
    ).list_current_inventory(limit=100)
```

## SKU 周预测

`SkuWeeklyForecastService` 从 `analytics.v_sku_daily_sales` 按渠道账户、SKU 和自然周汇总历史销量，使用 `sku_weighted_moving_average:v0.1` 生成未来 1–52 周预测。`channel_account_id` 为必填项，服务不会隐式执行跨渠道汇总：

- 最近四周权重依次为 40%、30%、20%、10%
- 近期平均周增量按 50% 阻尼后加入 `forecast_p50`
- 历史单步预测正残差的 90 分位数作为 `forecast_p90` 安全增量
- 训练区间必须从周一开始、到周日结束，缺失周按零销量处理

当前应用数据库连接保持只读，因此服务只返回版本化预测结果，不写入 `planning.forecast_runs` 或 `planning.weekly_forecasts`。预测持久化应由独立 Worker 使用单独的最小写入权限完成。

```python
from datetime import date

from application.services import SkuWeeklyForecastService

result = SkuWeeklyForecastService(unit_of_work.sales).generate(
    channel_account_id="CA_SHOPIFY_US",
    training_start=date(2026, 4, 13),
    training_end=date(2026, 7, 12),
    horizon_weeks=8,
)
```

## Web Dashboard

第一阶段 Web 层采用 FastAPI + Jinja2 + HTMX + Bootstrap 5 + Apache ECharts，提供：

- `/sales`：默认渠道最近一段时间的 SKU 日销量趋势和销售明细
- `/sales/weekly`：默认渠道按自然周汇总的 SKU 销量、订单量和销售额
- `/sales/refunds`：默认渠道的 SKU 日退款和周退款明细
- `/sales/channels`：各渠道在同一币种内的销量占比和净销售额占比
- `/inventory`：当前库存组成、在途库存、补货风险、积压风险和库存公式差异
- `/health/live`：进程存活检查
- `/health/ready`：PostgreSQL 只读连接检查

第一阶段页面通过固定版本 CDN 加载 Bootstrap、HTMX 和 ECharts；转入生产部署前再将这些资源迁入本地 `static/vendor`。

当前阶段暂不提供登录认证、页面筛选和分页。默认渠道、销售查询窗口和查询上限由 `.env` 配置：

```dotenv
WEB_TITLE=Ecommerce BI
WEB_DEFAULT_CHANNEL_ACCOUNT_ID=CA_SHOPIFY_US
WEB_CHANNEL_ACCOUNT_IDS=CA_SHOPIFY_US,CA_AMAZON_US
WEB_SALES_LOOKBACK_DAYS=90
WEB_QUERY_LIMIT=500
```

`WEB_DEFAULT_CHANNEL_ACCOUNT_ID` 决定销售页面首次打开时使用的渠道；
`WEB_CHANNEL_ACCOUNT_IDS` 是允许在页面切换的渠道白名单。SKU 日销售、周销售和
退款页面支持通过查询参数保留当前选择：

```text
/sales?channel_account_id=CA_AMAZON_US
/sales/weekly?channel_account_id=CA_AMAZON_US
/sales/refunds?channel_account_id=CA_AMAZON_US
```

不在 `WEB_CHANNEL_ACCOUNT_IDS` 中的渠道会返回 HTTP 400。

开发启动：

```powershell
.\.venv\Scripts\python -m uvicorn web.main:app --reload
```

然后访问：

```text
http://localhost:8000/sales
http://localhost:8000/inventory
```

Application Service 不依赖 Web 或基础设施 UoW。FastAPI 请求依赖负责创建 `ReadOnlyUnitOfWork`，再将其中的 Repository 实例传给 Application Service。模板只接收 Presenter 生成的 ViewModel，不执行 SQL 或业务指标计算。

完整的只读页面执行链路为：

```text
浏览器
→ FastAPI Route
→ FastAPI Depends
→ ReadOnlyUnitOfWork（SET TRANSACTION READ ONLY）
→ Application Service
→ Application Repository Protocol
→ PostgreSQL Repository 实现
→ PostgreSQL 表/分析快照
→ DTO
→ Presenter
→ ViewModel
→ Jinja2 Template
→ HTML + ECharts
→ 浏览器
```

当前只有以下业务形成了从 Web 到 PostgreSQL 的完整链路：

- `/sales`：`SkuSalesService → PostgresSalesAnalyticsRepository → analytics.v_sku_daily_sales`
- `/sales/weekly`：`SkuSalesService → PostgresSalesAnalyticsRepository → analytics.v_sku_daily_sales`
- `/sales/refunds`：`SkuRefundService → PostgresSkuRefundRepository → sales.refunds / refund_lines / order_lines / orders`
- `/sales/channels`：`ChannelSalesShareService → PostgresChannelSalesRepository → analytics.v_sku_daily_sales`
- `/inventory`：`InventoryBalanceService → PostgresInventoryRepository → inventory.inventory_balances`
- `/inventory`：`InventoryRiskService → PostgresInventoryRepository → analytics.v_inventory_cover`

SKU 周预测已经具备 Application Service 与 PostgreSQL Repository，但尚未
接入 Web Route、Presenter 和页面。客户 LTV、SKU 月度利润和渠道月度利润当前
只有 DTO 与 Repository 查询能力，也尚未接入 Web。

已知限制：`PostgresCustomerRepository.list_customer_lifetime_value()` 当前在
PostgreSQL/psycopg 下会因可选筛选参数缺少显式类型转换而触发
`AmbiguousParameter`。接入客户 LTV 页面前需要先修复该查询并增加真实数据库
集成测试。

配置数据库后执行只读健康检查：

```powershell
.\.venv\Scripts\python -c "from infrastructure.database import create_database_engine; from infrastructure.database.health import check_database_health; print(check_database_health(create_database_engine()))"
```

验证候选 DDL：

```powershell
.\.venv\Scripts\python -m infrastructure.database.schema_validation --ddl "C:\path\to\coolcool_erp_v0.2_full.sql"
```

验证 live database：

```powershell
.\.venv\Scripts\python -m infrastructure.database.schema_validation --database
```

表级 live validator 通过后，还必须按照 `db/migrations/README.md`，使用同一版本的 `pg_dump --schema-only` 对 reference database 与 live database 做完整结构对比。两道验证均通过后，才允许手工执行 Alembic baseline stamp。应用不会自动执行迁移。

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

默认离线测试：

```powershell
.\.venv\Scripts\python -m pytest -m "not integration and not shopify_live"
```

离线测试不需要真实 Shopify、PostgreSQL 或模型 API。数据库集成测试必须使用独立测试数据库，并且数据库名必须以 `_test` 结尾：

```powershell
$env:DATABASE_TEST_URL="postgresql+psycopg://coolcool_app_test:password@localhost:5432/coolcool_erp_test"
.\.venv\Scripts\python -m pytest -m integration
```

`DATABASE_URL` 用于应用只读连接和健康检查；`DATABASE_TEST_URL` 只用于集成测试。`shopify_live` 测试必须显式选择，不能混入默认离线测试。
