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


PERCENT = Decimal("100")
FOUR_PLACES = Decimal("0.0001")
TWO_PLACES = Decimal("0.01")
TOP_SKU_LIMIT = 8
FORECAST_TRAINING_WEEKS = 12


class OverviewDashboardService:
    """Compose a decision-oriented overview from typed analytics services."""

    def __init__(
        self,
        *,
        sales_repository: SalesAnalyticsRepository,
        refund_repository: SkuRefundRepository,
        inventory_repository: InventoryRepository,
        supplement_provider: OverviewSupplementProvider,
    ) -> None:
        self._sales_repository = sales_repository
        self._refund_repository = refund_repository
        self._inventory_repository = inventory_repository
        self._supplement_provider = supplement_provider

    def get_dashboard(
        self,
        *,
        channel_account_ids: Sequence[str],
        start_date: date,
        end_date: date,
        currency_code: str = "USD",
        limit: int = 10_000,
        generated_at: datetime | None = None,
    ) -> OverviewDashboard:
        channels = _validate_filters(
            channel_account_ids,
            start_date,
            end_date,
            currency_code,
            limit,
        )
        previous_start, previous_end = _previous_period(start_date, end_date)
        sales_service = SkuSalesService(self._sales_repository)
        refund_service = SkuRefundService(self._refund_repository)
        current_sales = _load_sales(
            sales_service,
            channels,
            start_date,
            end_date,
            currency_code,
            limit,
        )
        previous_sales = _load_sales(
            sales_service,
            channels,
            previous_start,
            previous_end,
            currency_code,
            limit,
        )
        current_refunds = _load_refunds(
            refund_service,
            channels,
            start_date,
            end_date,
            currency_code,
            limit,
        )
        previous_refunds = _load_refunds(
            refund_service,
            channels,
            previous_start,
            previous_end,
            currency_code,
            limit,
        )
        inventory_cover = list(
            self._inventory_repository.list_inventory_cover(limit=limit)
        )

        current_totals = _sales_totals(current_sales)
        previous_totals = _sales_totals(previous_sales)
        current_skus = _sku_totals(current_sales)
        previous_skus = _sku_totals(previous_sales)
        top_skus = sorted(
            current_skus,
            key=lambda sku_id: (
                -current_skus[sku_id]["net_sales"],
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
                channel_account_ids=channels,
                start_date=start_date,
                end_date=end_date,
                current_net_sales=current_totals["net_sales"],
                previous_net_sales=previous_totals["net_sales"],
                top_sku_units=tuple(
                    (
                        sku_id,
                        int(current_skus[sku_id]["units_sold"]),
                    )
                    for sku_id in top_skus
                ),
                replenishment_skus=replenishment_skus,
                overstock_skus=overstock_skus,
            )
        )
        forecast_by_sku = dict(supplement.forecast_4w_p50)
        real_forecasts = self._generate_real_forecasts(
            channels=channels,
            end_date=end_date,
            top_skus=set(top_skus),
            limit=limit,
        )
        forecast_by_sku.update(real_forecasts)

        current_refunded_units = sum(
            row.refunded_units for row in current_refunds
        )
        previous_refunded_units = sum(
            row.refunded_units for row in previous_refunds
        )
        current_refund_rate = _percentage(
            Decimal(current_refunded_units),
            current_totals["units_sold"],
        )
        previous_refund_rate = _percentage(
            Decimal(previous_refunded_units),
            previous_totals["units_sold"],
        )
        current_aov = _safe_divide(
            current_totals["net_sales"],
            Decimal(supplement.orders_count),
        )
        previous_aov = _safe_divide(
            previous_totals["net_sales"],
            Decimal(supplement.previous_orders_count),
        )

        return OverviewDashboard(
            filters=OverviewFilters(
                channel_account_ids=channels,
                start_date=start_date,
                end_date=end_date,
                currency_code=currency_code,
            ),
            generated_at=generated_at or datetime.now(timezone.utc),
            kpis=OverviewKpis(
                net_sales=current_totals["net_sales"],
                net_sales_change_pct=_percent_change(
                    current_totals["net_sales"],
                    previous_totals["net_sales"],
                ),
                units_sold=int(current_totals["units_sold"]),
                units_change_pct=_percent_change(
                    current_totals["units_sold"],
                    previous_totals["units_sold"],
                ),
                orders_count=supplement.orders_count,
                orders_change_pct=_percent_change(
                    Decimal(supplement.orders_count),
                    Decimal(supplement.previous_orders_count),
                ),
                average_order_value=current_aov,
                average_order_value_change_pct=_percent_change(
                    current_aov,
                    previous_aov,
                ),
                unit_refund_rate_pct=current_refund_rate,
                unit_refund_rate_change_points=(
                    current_refund_rate - previous_refund_rate
                ).quantize(FOUR_PLACES),
                stockout_risk_skus=len(replenishment_skus),
            ),
            trend=_build_trend(current_sales),
            channel_contributions=_build_channel_contributions(
                current_sales,
                channels,
                supplement.gross_profit_share_pct,
            ),
            sku_performance=_build_sku_performance(
                top_skus=top_skus,
                current_skus=current_skus,
                previous_skus=previous_skus,
                refunds=current_refunds,
                inventory_cover=inventory_cover,
                forecast_by_sku=forecast_by_sku,
            ),
            insights=supplement.insights,
            data_sources=tuple(
                dict.fromkeys(
                    (
                        "analytics.v_sku_daily_sales",
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
    channel_account_ids: Sequence[str],
    start_date: date,
    end_date: date,
    currency_code: str,
    limit: int,
) -> tuple[str, ...]:
    channels = tuple(
        dict.fromkeys(value.strip() for value in channel_account_ids)
    )
    if not channels or any(not value for value in channels):
        raise ValueError("at least one channel_account_id is required.")
    if start_date > end_date:
        raise ValueError("start_date must not be after end_date.")
    if not currency_code.strip():
        raise ValueError("currency_code must not be blank.")
    if not 1 <= limit <= 10_000:
        raise ValueError("limit must be between 1 and 10000.")
    return channels


def _previous_period(start_date: date, end_date: date) -> tuple[date, date]:
    period_days = (end_date - start_date).days + 1
    previous_end = start_date - timedelta(days=1)
    return previous_end - timedelta(days=period_days - 1), previous_end


def _load_sales(
    service: SkuSalesService,
    channels: Sequence[str],
    start_date: date,
    end_date: date,
    currency_code: str,
    limit: int,
) -> list[SkuDailySales]:
    rows: list[SkuDailySales] = []
    for channel_id in channels:
        rows.extend(
            row
            for row in service.list_daily_sales(
                channel_account_id=channel_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
            if row.currency_code == currency_code
        )
    return rows


def _load_refunds(
    service: SkuRefundService,
    channels: Sequence[str],
    start_date: date,
    end_date: date,
    currency_code: str,
    limit: int,
) -> list[SkuDailyRefunds]:
    rows: list[SkuDailyRefunds] = []
    for channel_id in channels:
        rows.extend(
            row
            for row in service.list_daily_refunds(
                channel_account_id=channel_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
            if row.currency_code == currency_code
        )
    return rows


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
) -> tuple[OverviewTrendPoint, ...]:
    values: dict[tuple[date, str], Decimal] = defaultdict(Decimal)
    for row in rows:
        values[(row.sales_date, row.channel_account_id)] += (
            row.net_sales or Decimal("0")
        )
    return tuple(
        OverviewTrendPoint(
            sales_date=sales_date,
            channel_account_id=channel_id,
            net_sales=net_sales,
        )
        for (sales_date, channel_id), net_sales in sorted(values.items())
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
    previous_skus: dict[str, dict[str, Decimal]],
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
            sales_change_pct=_percent_change(
                current_skus[sku_id]["net_sales"],
                previous_skus.get(
                    sku_id,
                    {"net_sales": Decimal("0")},
                )["net_sales"],
            ),
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


def _percent_change(current: Decimal, previous: Decimal) -> Decimal | None:
    if previous == 0:
        return None
    return (((current - previous) / previous) * PERCENT).quantize(
        FOUR_PLACES,
        ROUND_HALF_UP,
    )


def _last_completed_sunday(value: date) -> date:
    return value - timedelta(days=(value.weekday() + 1) % 7)
