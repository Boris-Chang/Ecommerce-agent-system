from collections import defaultdict
from collections.abc import Sequence
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from application.dto.inventory import InventoryCover
from application.dto.sku.dashboard import (
    SkuDashboard,
    SkuDashboardFilters,
    SkuDashboardKpis,
    SkuDashboardRow,
    SkuDashboardSupplementRequest,
    SkuDetailPoint,
    SkuRefundReasonShare,
    SkuTrendPoint,
)
from application.dto.sku.refunds import SkuDailyRefunds
from application.dto.sku.sales import SkuDailySales, SkuWeeklySales
from application.repositories.inventory import InventoryRepository
from application.repositories.sku import (
    SalesAnalyticsRepository,
    SkuDashboardSupplementProvider,
    SkuRefundRepository,
)
from application.services.sku.refunds import SkuRefundService
from application.services.sku.sales import SkuSalesService


PERCENT = Decimal("100")
FOUR_PLACES = Decimal("0.0001")
TOP_TREND_SKUS = 8
TOP_TABLE_SKUS = 50


class SkuDashboardService:
    """Compose sales, refunds and inventory into one channel-scoped SKU page."""

    def __init__(
        self,
        *,
        sales_repository: SalesAnalyticsRepository,
        refund_repository: SkuRefundRepository,
        inventory_repository: InventoryRepository,
        supplement_provider: SkuDashboardSupplementProvider,
    ) -> None:
        self._sales_repository = sales_repository
        self._refund_repository = refund_repository
        self._inventory_repository = inventory_repository
        self._supplement_provider = supplement_provider

    def get_dashboard(
        self,
        *,
        channel_account_id: str,
        start_date: date,
        end_date: date,
        currency_code: str = "USD",
        grain: str = "daily",
        search: str | None = None,
        limit: int = 10_000,
        generated_at: datetime | None = None,
    ) -> SkuDashboard:
        if grain not in {"daily", "weekly"}:
            raise ValueError("grain must be daily or weekly.")
        resolved_search = search.strip() if search and search.strip() else None
        previous_start, previous_end = _previous_period(start_date, end_date)
        sales_service = SkuSalesService(self._sales_repository)
        refund_service = SkuRefundService(self._refund_repository)
        current_daily = _currency_sales(
            sales_service.list_daily_sales(
                channel_account_id=channel_account_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            ),
            currency_code,
        )
        previous_daily = _currency_sales(
            sales_service.list_daily_sales(
                channel_account_id=channel_account_id,
                start_date=previous_start,
                end_date=previous_end,
                limit=limit,
            ),
            currency_code,
        )
        current_weekly = _currency_sales(
            sales_service.list_weekly_sales(
                channel_account_id=channel_account_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            ),
            currency_code,
        )
        refunds = [
            row
            for row in refund_service.list_daily_refunds(
                channel_account_id=channel_account_id,
                start_date=start_date,
                end_date=end_date,
                limit=limit,
            )
            if row.currency_code == currency_code
        ]
        inventory_cover = list(
            self._inventory_repository.list_inventory_cover(limit=limit)
        )
        current_totals = _sku_sales_totals(current_daily)
        previous_totals = _sku_sales_totals(previous_daily)
        active_skus = len(current_totals)
        supplement = self._supplement_provider.get_supplement(
            SkuDashboardSupplementRequest(
                channel_account_id=channel_account_id,
                start_date=start_date,
                end_date=end_date,
                active_skus=active_skus,
            )
        )
        ranked_skus = sorted(
            current_totals,
            key=lambda sku_id: (
                -current_totals[sku_id]["net_sales"],
                sku_id,
            ),
        )
        top_10_sales = sum(
            (
                current_totals[sku_id]["net_sales"]
                for sku_id in ranked_skus[:10]
            ),
            Decimal("0"),
        )
        all_sales = sum(
            (item["net_sales"] for item in current_totals.values()),
            Decimal("0"),
        )
        total_units = sum(
            (item["units_sold"] for item in current_totals.values()),
            Decimal("0"),
        )
        total_refunds = sum(
            (Decimal(row.refunded_units) for row in refunds),
            Decimal("0"),
        )
        display_skus = [
            sku_id
            for sku_id in ranked_skus
            if resolved_search is None
            or resolved_search.casefold() in sku_id.casefold()
        ][:TOP_TABLE_SKUS]
        return SkuDashboard(
            filters=SkuDashboardFilters(
                channel_account_id=channel_account_id,
                start_date=start_date,
                end_date=end_date,
                currency_code=currency_code,
                grain=grain,
                search=resolved_search,
            ),
            generated_at=generated_at or datetime.now(timezone.utc),
            kpis=SkuDashboardKpis(
                active_skus=active_skus,
                listed_skus=supplement.listed_skus,
                top_10_concentration_pct=_percentage(
                    top_10_sales,
                    all_sales,
                ),
                unit_refund_rate_pct=_percentage(
                    total_refunds,
                    total_units,
                ),
                slow_moving_skus=supplement.slow_moving_skus,
            ),
            trend=_build_trend(
                current_daily if grain == "daily" else current_weekly,
                ranked_skus[:TOP_TREND_SKUS],
            ),
            rows=tuple(
                _build_row(
                    sku_id=sku_id,
                    current=current_totals[sku_id],
                    previous=previous_totals.get(sku_id),
                    daily_sales=current_daily,
                    refunds=refunds,
                    inventory_cover=inventory_cover,
                )
                for sku_id in display_skus
            ),
            data_sources=(
                "analytics.v_sku_daily_sales",
                "analytics.v_sku_daily_refunds",
                "analytics.v_inventory_cover",
                supplement.data_source,
            ),
        )


def _currency_sales(
    rows: Sequence[SkuDailySales] | Sequence[SkuWeeklySales],
    currency_code: str,
) -> list[SkuDailySales] | list[SkuWeeklySales]:
    return [row for row in rows if row.currency_code == currency_code]


def _previous_period(start_date: date, end_date: date) -> tuple[date, date]:
    days = (end_date - start_date).days + 1
    previous_end = start_date - timedelta(days=1)
    return previous_end - timedelta(days=days - 1), previous_end


def _sku_sales_totals(
    rows: Sequence[SkuDailySales],
) -> dict[str, dict[str, Decimal]]:
    values: dict[str, dict[str, Decimal]] = defaultdict(
        lambda: {"units_sold": Decimal("0"), "net_sales": Decimal("0")}
    )
    for row in rows:
        values[row.sku_id]["units_sold"] += Decimal(row.units_sold or 0)
        values[row.sku_id]["net_sales"] += row.net_sales or Decimal("0")
    return dict(values)


def _build_trend(
    rows: Sequence[SkuDailySales] | Sequence[SkuWeeklySales],
    top_skus: Sequence[str],
) -> tuple[SkuTrendPoint, ...]:
    values: dict[tuple[date, str], int] = defaultdict(int)
    allowed = set(top_skus)
    for row in rows:
        if row.sku_id not in allowed:
            continue
        period_start = (
            row.sales_date
            if isinstance(row, SkuDailySales)
            else row.week_start
        )
        values[(period_start, row.sku_id)] += row.units_sold or 0
    return tuple(
        SkuTrendPoint(
            period_start=period_start,
            sku_id=sku_id,
            units_sold=units,
        )
        for (period_start, sku_id), units in sorted(values.items())
    )


def _build_row(
    *,
    sku_id: str,
    current: dict[str, Decimal],
    previous: dict[str, Decimal] | None,
    daily_sales: Sequence[SkuDailySales],
    refunds: Sequence[SkuDailyRefunds],
    inventory_cover: Sequence[InventoryCover],
) -> SkuDashboardRow:
    sku_refunds = [row for row in refunds if row.sku_id == sku_id]
    refunded_units = sum(row.refunded_units for row in sku_refunds)
    reason_units: dict[str, int] = defaultdict(int)
    for row in sku_refunds:
        reason_units[row.refund_reason or "未分类"] += row.refunded_units
    total_reason_units = sum(reason_units.values())
    reason_shares = tuple(
        SkuRefundReasonShare(
            reason=reason,
            refunded_units=units,
            share_pct=_percentage(
                Decimal(units),
                Decimal(total_reason_units),
            ),
        )
        for reason, units in sorted(
            reason_units.items(),
            key=lambda item: (-item[1], item[0]),
        )
    )
    daily_units: dict[date, int] = defaultdict(int)
    daily_refunds: dict[date, int] = defaultdict(int)
    for row in daily_sales:
        if row.sku_id == sku_id:
            daily_units[row.sales_date] += row.units_sold or 0
    for row in sku_refunds:
        daily_refunds[row.refund_date] += row.refunded_units
    dates = sorted(set(daily_units) | set(daily_refunds))
    covers = [
        item.inventory_cover_days
        for item in inventory_cover
        if item.sku_id == sku_id and item.inventory_cover_days is not None
    ]
    previous_sales = (
        previous["net_sales"] if previous else Decimal("0")
    )
    return SkuDashboardRow(
        sku_id=sku_id,
        units_sold=int(current["units_sold"]),
        net_sales=current["net_sales"],
        sales_change_pct=_percent_change(
            current["net_sales"],
            previous_sales,
        ),
        unit_refund_rate_pct=_percentage(
            Decimal(refunded_units),
            current["units_sold"],
        ),
        primary_refund_reason=(
            reason_shares[0].reason if reason_shares else "—"
        ),
        inventory_cover_days=min(covers) if covers else None,
        detail_points=tuple(
            SkuDetailPoint(
                sales_date=value,
                units_sold=daily_units[value],
                refunded_units=daily_refunds[value],
            )
            for value in dates
        ),
        refund_reasons=reason_shares,
    )


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
