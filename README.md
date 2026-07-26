# Ecommerce Analytics & Inspection Agent

这是一个基于 Python、FastAPI、LangChain 和 PostgreSQL 的只读电商经营分析项目。Web 提供经营总览、渠道、SKU、库存和 Agent 巡检分析入口。

当前 Agent 是无对话、无记忆的经营巡检 Agent。每次每日或每周巡检都使用固定范围调用现有 Application Service，生成一份新的结构化结论；它不接收自然语言问题，也不创建新的确定性指标或业务规则。

## 当前能力

- 按渠道查询 SKU 日/周销量、销售额和退款数据
- 按币种计算各渠道销量占比与净销售额占比
- 按 SKU、仓库查询在库、预占、冻结、可售和在途库存
- 查询库存覆盖、补货风险、积压风险、客户 LTV 和月度利润
- 使用版本化 Python 模型生成渠道级 SKU 周销量预测
- 运行每日或每周经营巡检，输出具体理由、统一指标语义和证据引用
- 通过统一 Dashboard Service 组合 PostgreSQL 真实查询结果与显式标注的临时补充接口
- 在经营总览、SKU 和库存页面按渠道、日期、粒度、仓库或 SKU 进行只读筛选

## 安全边界

当前 Web 和巡检 Agent 只读取数据：

- 不修改订单、商品、价格或库存
- 不执行采购、补货、调价或营销动作
- 不计算现有 Application Service 尚未提供的退款率、利润率或 LTV 结论
- 不执行跨币种汇总
- Agent 结论必须人工复核

## 分层结构

项目采用“接口层—应用层—基础设施层”的依赖方向：

- `src/infrastructure/llm/agent_runtime/agent_app/`：面向 Web、Worker 和测试适配器的 Agent 组合入口
- `src/infrastructure/llm/agent_runtime/`：LangChain 巡检 Agent、只读工具编排和运行时适配
- `src/application/agents/business_inspection/`：巡检用例、输出契约、Runner Port 和已有指标语义目录
- `src/application/dto/`：不可变只读 DTO，按 `overview`、`sku`、`channel`、`inventory`、`customer`、`profit` 业务域分组
- `src/application/repositories/`：应用层 Repository 协议，按业务域分组
- `src/application/services/`：确定性应用服务和 Dashboard 编排服务，按 `overview`、`sku`、`channel`、`inventory` 业务域分组
- `src/application/forecasting/sku_weekly/`：可版本管理的 SKU 周预测算法
- `src/infrastructure/database/repositories/`：PostgreSQL Repository 实现，同样按 `sku`、`channel`、`inventory`、`customer`、`profit` 业务域分组
- `src/infrastructure/mock/`：尚无后端服务字段的临时开发适配器；通过应用层 Protocol 注入，不进入 Repository，也不伪装成数据库结果
- `src/web/`：FastAPI、Jinja2、Presenter、ViewModel、页面模板与静态资源
- `src/integrations/`：Shopify 等外部系统适配
- `src/infrastructure/llm/models/llm_provider.py`：DeepSeek / OpenAI LLM 提供方选择

`application` 不依赖 `infrastructure`；基础设施实现应用层声明的协议。只读查询由 `ReadOnlyUnitOfWork` 管理事务，退出上下文时统一回滚并关闭连接。应用结果由调用方持有，不写入模块级全局状态。

## 安装

```powershell
cd "D:\openai project\python_langchain_agent"
python -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e ".[dev]"
copy .env.example .env
```

然后编辑 `.env`，填入 LLM 和只读 PostgreSQL 应用账号配置。

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
| `OverviewDashboardService` | 组合销售、退款、库存和临时补充指标 | 多渠道 + 查询周期 + 币种 |
| `SkuDashboardService` | 组合 SKU 销售、退款、库存覆盖和目录补充指标 | 渠道账户 + SKU + 日/周 |
| `InventoryDashboardService` | 组合库存余额、覆盖风险和临时决策指标 | SKU + 仓库 |

公共服务可从统一入口导入：

```python
from application.services import (
    ChannelSalesShareService,
    InventoryBalanceService,
    InventoryDashboardService,
    InventoryRiskService,
    OverviewDashboardService,
    SkuDashboardService,
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

## 经营巡检 Agent

巡检 Agent 只将以下现有 Application Service 封装成四个只读工具：

| Agent Tool | 现有 Application Service | 已有指标语义 |
| --- | --- | --- |
| `read_sku_sales_snapshot` | `SkuSalesService` | `sku_daily_sales` / `sku_weekly_sales` |
| `read_sku_refund_snapshot` | `SkuRefundService` | `sku_daily_refunds` / `sku_weekly_refunds` |
| `read_channel_sales_share` | `ChannelSalesShareService` | `channel_sales_share` |
| `read_inventory_snapshot` | `InventoryBalanceService`、`InventoryRiskService` | `current_inventory_balance`、`inventory_cover_risk` |

指标语义目录只描述这些 Service 已经存在的确定性计算和数据粒度，不新增趋势、阈值、退款率、利润率或跨域匹配规则。每个工具调用独立创建 `ReadOnlyUnitOfWork`，完成查询后回滚并关闭数据库 Session。

每次巡检都有唯一 `run_id`。Application Service 会校验：

- 每条结论必须包含具体理由
- 每条结论必须引用存在的 `evidence_id`
- 每条结论和证据必须引用已登记的 `metric_semantic_id`
- 证据语义必须能够支持结论声明的语义
- LangChain Runtime 必须实际调用全部四个工具
- Agent 不能把未调用的工具写入证据

日志事件包括：

```text
business_inspection_started
business_inspection_tool_started
business_inspection_tool_completed
business_inspection_runner_completed
business_inspection_completed
```

所有事件都带 `run_id`；工具完成日志还包括工具名、返回行数和耗时。模型密钥和数据库凭据不会写入日志。

完整调用链：

```text
Web / 外部任务调度器
→ BusinessInspectionService
→ BusinessInspectionRunner Port
→ LangChainBusinessInspectionRunner
→ 四个只读 Agent Tool
→ 每工具一个 ReadOnlyUnitOfWork
→ 现有 Application Service
→ Application Repository Protocol
→ PostgreSQL Repository
→ PostgreSQL 业务表或分析快照
→ Tool 证据（指标语义、数据截至时间、数据来源、限制）
→ LangChain 结构化输出
→ Application 证据引用校验
→ Presenter / Web 页面
```

LLM 配置：

```dotenv
LLM_PROVIDER=deepseek
LLM_MODEL=deepseek-chat
DEEPSEEK_API_KEY=your-deepseek-api-key
```

也可以设置 `LLM_PROVIDER=openai` 和 `OPENAI_API_KEY`。为了兼容已有本地 `.env`，代码仍会读取旧的 `AGENT_PROVIDER`、`AGENT_MODEL`，但新配置应使用 `LLM_*`。

巡检 Agent 需要同时使用多工具调用和结构化输出，因此 DeepSeek 默认使用
`deepseek-chat`。当前 DeepSeek V4 Pro/Flash 的 Thinking 模式会拒绝该流程所需的
强制 `tool_choice`，不能直接作为本巡检 Agent 的默认模型。

## Web Dashboard

当前 Web 层采用 FastAPI + Jinja2 + HTMX + Bootstrap 5 + Apache ECharts。根路径 `/` 会重定向到经营总览：

| 路由 | 页面能力 |
| --- | --- |
| `/overview` | 多渠道经营总览、周期对比、渠道贡献、SKU 表现、库存风险和经营洞察 |
| `/sales` | 按渠道、日期、日/周粒度和 SKU 关键词查看销量、净销售额、退款率、库存覆盖及展开明细 |
| `/sales/channels` | 各渠道在同一币种内的销量占比和净销售额占比 |
| `/inventory` | 按仓库和 SKU 查看库存组成、在途数量、库存覆盖、补货及积压风险 |
| `/agent-analysis` | 查看巡检预览，或触发每日/每周只读经营巡检并展示证据链和人工复核动作 |
| `/sales/weekly` | 保留的独立 SKU 周销售列表页 |
| `/sales/refunds` | 保留的 SKU 日/周退款列表页 |
| `/health/live` | 进程存活检查 |
| `/health/ready` | PostgreSQL 只读连接检查 |

页面通过固定版本 CDN 加载 Bootstrap、HTMX 和 ECharts；转入生产部署前应将这些资源迁入本地 `static/vendor`。

当前阶段暂不提供登录认证和分页，但经营总览、SKU 和库存主页面已经提供各自的只读筛选能力。默认渠道、销售查询窗口和查询上限由 `.env` 配置：

```dotenv
WEB_TITLE=Ecommerce BI
WEB_DEFAULT_CHANNEL_ACCOUNT_ID=CA_SHOPIFY_US
WEB_CHANNEL_ACCOUNT_IDS=CA_SHOPIFY_US,CA_AMAZON_US
WEB_SALES_LOOKBACK_DAYS=90
WEB_QUERY_LIMIT=500
WEB_OVERVIEW_QUERY_LIMIT=10000
# WEB_DEFAULT_END_DATE=2026-07-24
```

`WEB_DEFAULT_CHANNEL_ACCOUNT_ID` 决定销售页面首次打开时使用的渠道；
`WEB_CHANNEL_ACCOUNT_IDS` 是允许在页面切换的渠道白名单。
`WEB_DEFAULT_END_DATE` 仅用于固定演示或测试时间窗口，生产环境通常不设置。
查询参数示例：

```text
/overview?channel_account_id=CA_SHOPIFY_US&channel_account_id=CA_AMAZON_US&start_date=2026-07-01&end_date=2026-07-31
/sales?channel_account_id=CA_AMAZON_US&start_date=2026-07-01&end_date=2026-07-31&grain=weekly&search=SKU001
/inventory?warehouse_id=WH_US_WEST&search=SKU001
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
http://localhost:8000/overview
http://localhost:8000/sales
http://localhost:8000/inventory
http://localhost:8000/agent-analysis
```

Application Service 不依赖 Web 或基础设施 UoW。FastAPI 请求依赖负责创建
`ReadOnlyUnitOfWork`，再将其中的 Repository 实例传给 Application Service。
Dashboard Service 只通过应用层 Protocol 接收临时补充 Provider。模板只接收
Presenter 生成的 ViewModel，不执行 SQL 或业务指标计算。

真实数据库字段的完整只读页面执行链路为：

```text
浏览器
→ FastAPI Route
→ FastAPI Depends
→ ReadOnlyUnitOfWork（SET TRANSACTION READ ONLY）
→ Dashboard Service / Application Service
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

当前 Web 中真实访问 PostgreSQL 的数据包括：

| 页面 | 真实数据库链路 |
| --- | --- |
| `/overview` | `OverviewDashboardService → Sales/Refund/Inventory Repository → analytics.v_sku_daily_sales、sales.refunds/refund_lines/order_lines/orders、inventory.inventory_balances、analytics.v_inventory_cover` |
| `/sales` | `SkuDashboardService → Sales/Refund/Inventory Repository → analytics.v_sku_daily_sales、退款业务表、analytics.v_inventory_cover` |
| `/sales/weekly` | `SkuSalesService → PostgresSalesAnalyticsRepository → analytics.v_sku_daily_sales` |
| `/sales/refunds` | `SkuRefundService → PostgresSkuRefundRepository → sales.refunds/refund_lines/order_lines/orders` |
| `/sales/channels` | `ChannelSalesShareService → PostgresChannelSalesRepository → analytics.v_sku_daily_sales` |
| `/inventory` | `InventoryDashboardService → PostgresInventoryRepository → inventory.inventory_balances、analytics.v_inventory_cover` |
| `/agent-analysis/refresh` | `BusinessInspectionService → LangChain Runner → 四个只读 Tool → Application Service → PostgreSQL` |

### 临时补充数据边界

部分新版 UI 字段尚无正式后端服务。它们通过 `src/infrastructure/mock/` 中实现
应用层 Protocol 的固定 Provider 注入，不写入数据库，也不经过 PostgreSQL
Repository：

| 页面 | 临时补充字段 | `data_source` |
| --- | --- | --- |
| `/overview` | 估算订单数、毛利贡献权重、四周预测展示值和最多三条经营洞察 | `fixed_overview_supplement_v1` |
| `/sales` | 在售 SKU 总数和滞销 SKU 数量 | `fixed_sku_catalog_metrics_v1` |
| `/inventory` | 库存金额、预计缺货损失、积压资金、建议补货数量 | `fixed_inventory_decision_metrics_v1` |
| `/agent-analysis` GET 预览及复核区 | 预览结论、审核状态和建议动作；POST 刷新后的巡检结论与证据来自真实 Agent 调用，但复核元数据仍由固定 Provider 补充 | `fixed_inspection_review_workflow_v1` |

这些 Provider 是可替换适配器：正式服务接入时只需实现相同应用层 Protocol，
Dashboard Service、Presenter 和模板结构无需改变。不能把临时补充字段解释为
PostgreSQL 的真实业务结果。

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

## 可编程巡检

项目不提供命令行对话入口。Web、外部定时任务或 Worker 使用同一个无对话巡检用例：

```python
from datetime import date

from application.agents.business_inspection import BusinessInspectionRequest
from infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from infrastructure.llm.agent_runtime.agent_app import (
    create_business_inspection_service,
)

engine = create_database_engine()
service = create_business_inspection_service(
    create_session_factory(engine)
)
result = service.run(
    BusinessInspectionRequest(
        frequency="daily",
        channel_account_id="CA_SHOPIFY_US",
        start_date=date(2026, 7, 24),
        end_date=date(2026, 7, 24),
    )
)
print(result.model_dump_json(indent=2))
```

该调用每次只生成一份结果，不保存会话记忆。当前 Web 也不持久化历史巡检；如需每天或每周自动运行并保留历史，应由外部任务调度器调用该接口，并由独立结果存储适配器负责持久化。

## 启动检查

“正常启动”定义为项目安装成功、公共接口可导入、Web 可以创建巡检服务。快速检查公共接口：

```powershell
.\.venv\Scripts\python -c "from infrastructure.llm.agent_runtime.agent_app import create_business_inspection_service; from infrastructure.llm.models.llm_provider import build_llm; print('inspection imports: OK')"
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
