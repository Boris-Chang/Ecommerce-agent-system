from collections import defaultdict
from collections.abc import Callable, Sequence
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

from application.dto.sku import (
    SkuForecastRun,
    SkuWeeklyForecast,
    SkuWeeklySales,
)
from application.forecasting.sku_weekly import (
    WeeklyDemandPoint,
    WeightedMovingAverageForecaster,
)
from application.repositories.sku import SalesAnalyticsRepository
from application.services.sku._validation import validate_channel_account_id
from core.ids import new_uuid


class SkuWeeklyForecastService:
    """Generate versioned SKU-level weekly forecasts from completed sales weeks."""

    def __init__(
        self,
        repository: SalesAnalyticsRepository,
        *,
        forecaster: WeightedMovingAverageForecaster | None = None,
        clock: Callable[[], datetime] | None = None,
        id_factory: Callable[[], UUID] = new_uuid,
    ) -> None:
        self._repository = repository
        self._forecaster = forecaster or WeightedMovingAverageForecaster()
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._id_factory = id_factory

    def generate(
        self,
        *,
        channel_account_id: str,
        training_start: date,
        training_end: date,
        horizon_weeks: int = 8,
        limit: int = 10_000,
    ) -> SkuForecastRun:
        _validate_training_period(training_start, training_end)
        resolved_channel = validate_channel_account_id(channel_account_id)
        if limit < 1:
            raise ValueError("limit must be at least 1.")

        weekly_sales = self._repository.list_sku_weekly_sales(
            channel_account_id=resolved_channel,
            start_date=training_start,
            end_date=training_end,
            limit=limit,
        )
        if not weekly_sales:
            raise ValueError("no weekly SKU sales are available for the training period.")
        if any(
            row.channel_account_id != resolved_channel
            for row in weekly_sales
        ):
            raise ValueError(
                "repository returned weekly sales from another channel account."
            )

        grouped = _group_weekly_sales(weekly_sales)
        forecast_run_id = f"FCRUN-{self._id_factory().hex.upper()}"
        data_origin = (
            f"{self._forecaster.model_name}:{self._forecaster.model_version}"
        )
        forecasts = []
        for sku_id in sorted(grouped):
            sku_rows = grouped[sku_id]
            if len({row.week_start for row in sku_rows}) < 2:
                continue
            history = _complete_training_history(
                sku_rows,
                training_start=training_start,
                training_end=training_end,
            )
            for estimate in self._forecaster.forecast(
                history,
                horizon_weeks=horizon_weeks,
            ):
                forecasts.append(
                    SkuWeeklyForecast(
                        forecast_id=(
                            f"{forecast_run_id}:{sku_id}:{estimate.week_start:%Y%m%d}"
                        ),
                        forecast_run_id=forecast_run_id,
                        sku_id=sku_id,
                        channel_account_id=resolved_channel,
                        week_start=estimate.week_start,
                        forecast_p50=estimate.forecast_p50,
                        forecast_p90=estimate.forecast_p90,
                        data_origin=data_origin,
                    )
                )

        if not forecasts:
            raise ValueError(
                "at least one SKU must have two weeks of demand history."
            )

        parameters = self._forecaster.parameters()
        parameters.update(
            {
                "channel_account_id": resolved_channel,
                "horizon_weeks": horizon_weeks,
                "series_grain": "sku_channel_account",
                "training_weeks_must_be_complete": True,
            }
        )
        return SkuForecastRun(
            forecast_run_id=forecast_run_id,
            channel_account_id=resolved_channel,
            model_name=self._forecaster.model_name,
            model_version=self._forecaster.model_version,
            training_start=training_start,
            training_end=training_end,
            generated_at=self._clock(),
            parameters_json=parameters,
            status="calculated",
            forecasts=tuple(forecasts),
        )


def _validate_training_period(training_start: date, training_end: date) -> None:
    if training_start > training_end:
        raise ValueError("training_start must not be after training_end.")
    if training_start.weekday() != 0:
        raise ValueError("training_start must be a Monday.")
    if training_end.weekday() != 6:
        raise ValueError("training_end must be a Sunday.")


def _group_weekly_sales(
    rows: Sequence[SkuWeeklySales],
) -> dict[str, list[SkuWeeklySales]]:
    grouped: dict[str, list[SkuWeeklySales]] = defaultdict(list)
    for row in rows:
        grouped[row.sku_id].append(row)
    return grouped


def _complete_training_history(
    rows: Sequence[SkuWeeklySales],
    *,
    training_start: date,
    training_end: date,
) -> list[WeeklyDemandPoint]:
    units_by_week: dict[date, Decimal] = defaultdict(Decimal)
    for row in rows:
        units_by_week[row.week_start] += Decimal(row.units_sold)
    last_training_week = training_end - timedelta(days=6)
    history = []
    current_week = training_start
    while current_week <= last_training_week:
        history.append(
            WeeklyDemandPoint(
                week_start=current_week,
                units_sold=units_by_week.get(current_week, Decimal("0")),
            )
        )
        current_week += timedelta(days=7)
    return history
