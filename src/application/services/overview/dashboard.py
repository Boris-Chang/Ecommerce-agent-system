from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from application.dto.inventory import InventoryCover
from application.dto.overview import (
    OverviewChannelContribution,
    OverviewDashboard,
    OverviewFilters,
    OverviewKpis,
    OverviewSkuPerformance,
    OverviewSupplementRequest,
    OverviewTrendPoint,
)
from application.dto.sku import SkuDailyRefunds, SkuDailySales
from application.repositories.inventory import InventoryRepository
from application.repositories.order import OrderSummaryRepository
from application.repositories.overview import OverviewSupplementProvider
from application.repositories.sku import (
    SalesAnalyticsRepository,
    SkuRefundRepository,
)
from application.services.sku import (
    SkuRefundService,
    SkuSalesService,
    SkuWeeklyForecastService,
)
from application.services.order import OrderSummaryService


PERCENT = Decimal("100")
FOUR_PLACES = Decimal("0.0001")
TWO_PLACES = Decimal("0.01")
TOP_SKU_LIMIT = 8
FORECAST_TRAINING_WEEKS = 12
TREND_DAYS = 21


class OverviewDashboardService:
    """Compose a decision-oriented overview from typed analytics services."""

    def __init__(
        self,
        *,
        sales_repository: SalesAnalyticsRepository,
        refund_repository: SkuRefundRepository,
        inventory_repository: InventoryRepository,
        order_repository: OrderSummaryRepository,
        supplement_provider: OverviewSupplementProvider,
    ) -> None:
        self._sales_repository = sales_repository
        self._refund_repository = refund_repository
        self._inventory_repository = inventory_repository
        self._order_repository = order_repository
        self._supplement_provider = supplement_provider

    def get_dashboard(
        self,
        *,
        channel_account_id: str,
        as_of_date: date,
        currency_code: str = "USD",
        limit: int = 10_000,
        generated_at: datetime | None = None,
    ) -> OverviewDashboard:
        channel = _validate_filters(
            channel_account_id,
            currency_code,
            limit,
        )
        week_start = as_of_date - timedelta(days=as_of_date.weekday())
        trend_start = as_of_date - timedelta(days=TREND_DAYS - 1)
        sales_service = SkuSalesService(self._sales_repository)
        refund_service = SkuRefundService(self._refund_repository)
        order_service = OrderSummaryService(self._order_repository)
        weekly_sales = _load_sales(
            sales_service,
            channel,
            week_start,
            as_of_date,
            currency_code,
            limit,
        )
        daily_sales = [
            row for row in weekly_sales if row.sales_date == as_of_date
        ]
        trend_sales = _load_sales(
            sales_service,
            channel,
            trend_start,
            as_of_date,
            currency_code,
            limit,
        )
        weekly_refunds = _load_refunds(
            refund_service,
            channel,
            week_start,
            as_of_date,
            currency_code,
            limit,
        )
        daily_refunds = [
            row for row in weekly_refunds if row.refund_date == as_of_date
        ]
        trend_refunds = _load_refunds(
            refund_service,
            channel,
            trend_start,
            as_of_date,
            currency_code,
            limit,
        )
        daily_orders_count = order_service.count_orders(
            channel_account_id=channel,
            start_date=as_of_date,
            end_date=as_of_date,
            currency_code=currency_code,
        )
        weekly_orders_count = order_service.count_orders(
            channel_account_id=channel,
            start_date=week_start,
            end_date=as_of_date,
            currency_code=currency_code,
        )
        inventory_cover = list(
            self._inventory_repository.list_inventory_cover(limit=limit)
        )

        daily_totals = _sales_totals(daily_sales)
        weekly_totals = _sales_totals(weekly_sales)
        trend_skus = _sku_totals(trend_sales)
        top_skus = sorted(
            trend_skus,
            key=lambda sku_id: (
                -trend_skus[sku_id]["net_sales"],
                sku_id,
            ),
        )[:TOP_SKU_LIMIT]
        replenishment_skus = tuple(
            sorted(
                {
                    item.sku_id
                    for item in inventory_cover
                    if item.stock_status == "replenish"
                }
            )
        )
        overstock_skus = tuple(
            sorted(
                {
                    item.sku_id
                    for item in inventory_cover
                    if item.stock_status == "overstock"
                }
            )
        )
        supplement = self._supplement_provider.get_supplement(
            OverviewSupplementRequest(
                channel_account_id=channel,
                day=as_of_date,
                week_start=week_start,
                week_end=as_of_date,
                top_sku_units=tuple(
                    (
                        sku_id,
                        int(trend_skus[sku_id]["units_sold"]),
                    )
                    for sku_id in top_skus
                ),
                replenishment_skus=replenishment_skus,
                overstock_skus=overstock_skus,
            )
        )
        forecast_by_sku = dict(supplement.forecast_4w_p50)
        real_forecasts = self._generate_real_forecasts(
            channels=(channel,),
            end_date=as_of_date,
            top_skus=set(top_skus),
            limit=limit,
        )
        forecast_by_sku.update(real_forecasts)

        return OverviewDashboard(
            filters=OverviewFilters(
                channel_account_id=channel,
                day=as_of_date,
                week_start=week_start,
                week_end=as_of_date,
                trend_start=trend_start,
                trend_end=as_of_date,
                currency_code=currency_code,
            ),
            generated_at=generated_at or datetime.now(timezone.utc),
            daily_kpis=_build_kpis(
                totals=daily_totals,
                refunds=daily_refunds,
                orders_count=daily_orders_count,
            ),
            weekly_kpis=_build_kpis(
                totals=weekly_totals,
                refunds=weekly_refunds,
                orders_count=weekly_orders_count,
            ),
            trend=_build_trend(
                trend_sales,
                channel_account_id=channel,
                start_date=trend_start,
                end_date=as_of_date,
            ),
            channel_contributions=_build_channel_contributions(
                weekly_sales,
                (channel,),
                supplement.gross_profit_share_pct,
            ),
            sku_performance=_build_sku_performance(
                top_skus=top_skus,
                current_skus=trend_skus,
                refunds=trend_refunds,
                inventory_cover=inventory_cover,
                forecast_by_sku=forecast_by_sku,
            ),
            insights=supplement.insights,
            data_sources=tuple(
                dict.fromkeys(
                    (
                        "analytics.v_sku_daily_sales",
                        "sales.orders",
                        "analytics.v_sku_daily_refunds",
                        "analytics.v_inventory_cover",
                        *(
                            ("sku_weighted_moving_average:v0.1",)
                            if real_forecasts
                            else ()
                        ),
                        supplement.data_source,
                    )
                )
            ),
        )

    def _generate_real_forecasts(
        self,
        *,
        channels: tuple[str, ...],
        end_date: date,
        top_skus: set[str],
        limit: int,
    ) -> dict[str, Decimal]:
        training_end = _last_completed_sunday(end_date)
        training_start = training_end - timedelta(
            days=FORECAST_TRAINING_WEEKS * 7 - 1
        )
        forecasts: dict[str, Decimal] = defaultdict(Decimal)
        service = SkuWeeklyForecastService(self._sales_repository)
        for channel_id in channels:
            try:
                run = service.generate(
                    channel_account_id=channel_id,
                    training_start=training_start,
                    training_end=training_end,
                    horizon_weeks=4,
                    limit=limit,
                )
            except ValueError:
                continue
            for item in run.forecasts:
                if item.sku_id in top_skus:
                    forecasts[item.sku_id] += item.forecast_p50
        return dict(forecasts)


def _validate_filters(
    channel_account_id: str,
    currency_code: str,
    limit: int,
) -> str:
    channel = channel_account_id.strip()
    if not channel:
        raise ValueError("channel_account_id must not be blank.")
    if not currency_code.strip():
        raise ValueError("currency_code must not be blank.")
    if not 1 <= limit <= 10_000:
        raise ValueError("limit must be between 1 and 10000.")
    return channel


def _load_sales(
    service: SkuSalesService,
    channel_account_id: str,
    start_date: date,
    end_date: date,
    currency_code: str,
    limit: int,
) -> list[SkuDailySales]:
    return [
        row
        for row in service.list_daily_sales(
            channel_account_id=channel_account_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        if row.currency_code == currency_code
    ]


def _load_refunds(
    service: SkuRefundService,
    channel_account_id: str,
    start_date: date,
    end_date: date,
    currency_code: str,
    limit: int,
) -> list[SkuDailyRefunds]:
    return [
        row
        for row in service.list_daily_refunds(
            channel_account_id=channel_account_id,
            start_date=start_date,
            end_date=end_date,
            limit=limit,
        )
        if row.currency_code == currency_code
    ]


def _sales_totals(
    rows: Sequence[SkuDailySales],
) -> dict[str, Decimal]:
    return {
        "units_sold": sum(
            (Decimal(row.units_sold or 0) for row in rows),
            Decimal("0"),
        ),
        "net_sales": sum(
            (row.net_sales or Decimal("0") for row in rows),
            Decimal("0"),
        ),
    }


def _build_kpis(
    *,
    totals: dict[str, Decimal],
    refunds: Sequence[SkuDailyRefunds],
    orders_count: int,
) -> OverviewKpis:
    refunded_units = sum(row.refunded_units for row in refunds)
    return OverviewKpis(
        net_sales=totals["net_sales"],
        units_sold=int(totals["units_sold"]),
        orders_count=orders_count,
        average_order_value=_safe_divide(
            totals["net_sales"],
            Decimal(orders_count),
        ),
        unit_refund_rate_pct=_percentage(
            Decimal(refunded_units),
            totals["units_sold"],
        ),
    )


def _sku_totals(
    rows: Sequence[SkuDailySales],
) -> dict[str, dict[str, Decimal]]:
    totals: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"units_sold": Decimal("0"), "net_sales": Decimal("0")}
    )
    for row in rows:
        totals[row.sku_id]["units_sold"] += Decimal(row.units_sold or 0)
        totals[row.sku_id]["net_sales"] += row.net_sales or Decimal("0")
    return dict(totals)


def _build_trend(
    rows: Sequence[SkuDailySales],
    *,
    channel_account_id: str,
    start_date: date,
    end_date: date,
) -> tuple[OverviewTrendPoint, ...]:
    if not rows:
        return ()
    values: dict[date, Decimal] = defaultdict(Decimal)
    for row in rows:
        values[row.sales_date] += row.net_sales or Decimal("0")
    return tuple(
        OverviewTrendPoint(
            sales_date=start_date + timedelta(days=offset),
            channel_account_id=channel_account_id,
            net_sales=values[start_date + timedelta(days=offset)],
        )
        for offset in range((end_date - start_date).days + 1)
    )


def _build_channel_contributions(
    rows: Sequence[SkuDailySales],
    channels: Sequence[str],
    gross_profit_shares: dict[str, Decimal],
) -> tuple[OverviewChannelContribution, ...]:
    totals: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"units_sold": Decimal("0"), "net_sales": Decimal("0")}
    )
    for row in rows:
        totals[row.channel_account_id]["units_sold"] += Decimal(
            row.units_sold or 0
        )
        totals[row.channel_account_id]["net_sales"] += (
            row.net_sales or Decimal("0")
        )
    all_units = sum(
        (totals[value]["units_sold"] for value in channels),
        Decimal("0"),
    )
    all_net_sales = sum(
        (totals[value]["net_sales"] for value in channels),
        Decimal("0"),
    )
    return tuple(
        OverviewChannelContribution(
            channel_account_id=channel_id,
            units_sold=int(totals[channel_id]["units_sold"]),
            net_sales=totals[channel_id]["net_sales"],
            units_share_pct=_percentage(
                totals[channel_id]["units_sold"],
                all_units,
            ),
            net_sales_share_pct=_percentage(
                totals[channel_id]["net_sales"],
                all_net_sales,
            ),
            gross_profit_share_pct=gross_profit_shares.get(
                channel_id,
                Decimal("0"),
            ),
        )
        for channel_id in channels
    )


def _build_sku_performance(
    *,
    top_skus: Sequence[str],
    current_skus: dict[str, dict[str, Decimal]],
    refunds: Sequence[SkuDailyRefunds],
    inventory_cover: Sequence[InventoryCover],
    forecast_by_sku: dict[str, Decimal],
) -> tuple[OverviewSkuPerformance, ...]:
    refunded_units: dict[str, int] = defaultdict(int)
    for row in refunds:
        refunded_units[row.sku_id] += row.refunded_units
    cover_days: dict[str, int] = {}
    for row in inventory_cover:
        if row.inventory_cover_days is None:
            continue
        cover_days[row.sku_id] = min(
            cover_days.get(row.sku_id, row.inventory_cover_days),
            row.inventory_cover_days,
        )
    return tuple(
        OverviewSkuPerformance(
            sku_id=sku_id,
            units_sold=int(current_skus[sku_id]["units_sold"]),
            net_sales=current_skus[sku_id]["net_sales"],
            unit_refund_rate_pct=_percentage(
                Decimal(refunded_units[sku_id]),
                current_skus[sku_id]["units_sold"],
            ),
            inventory_cover_days=cover_days.get(sku_id),
            forecast_4w_p50=forecast_by_sku.get(
                sku_id,
                Decimal("0"),
            ),
        )
        for sku_id in top_skus
    )


def _safe_divide(value: Decimal, denominator: Decimal) -> Decimal:
    if denominator == 0:
        return Decimal("0")
    return (value / denominator).quantize(TWO_PLACES, ROUND_HALF_UP)


def _percentage(value: Decimal, total: Decimal) -> Decimal:
    if total == 0:
        return Decimal("0")
    return ((value / total) * PERCENT).quantize(
        FOUR_PLACES,
        ROUND_HALF_UP,
    )


def _last_completed_sunday(value: date) -> date:
    return value - timedelta(days=(value.weekday() + 1) % 7)
