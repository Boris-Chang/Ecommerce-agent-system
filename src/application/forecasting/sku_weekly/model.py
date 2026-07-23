from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Sequence

from application.forecasting.sku_weekly.evaluation import upper_residual_quantile
from application.forecasting.sku_weekly.features import fill_missing_weeks
from application.forecasting.sku_weekly.schemas import (
    ForecastEstimate,
    WeeklyDemandPoint,
)


MODEL_NAME = "sku_weighted_moving_average"
MODEL_VERSION = "v0.1"
DEFAULT_WEIGHTS = (
    Decimal("0.40"),
    Decimal("0.30"),
    Decimal("0.20"),
    Decimal("0.10"),
)
SIX_PLACES = Decimal("0.000001")


class WeightedMovingAverageForecaster:
    """Forecast weekly SKU demand with recent weighting and a damped trend."""

    model_name = MODEL_NAME
    model_version = MODEL_VERSION

    def __init__(
        self,
        *,
        weights: Sequence[Decimal] = DEFAULT_WEIGHTS,
        trend_damping: Decimal = Decimal("0.50"),
        p90_quantile: Decimal = Decimal("0.90"),
    ) -> None:
        resolved_weights = tuple(Decimal(str(weight)) for weight in weights)
        if len(resolved_weights) < 2:
            raise ValueError("at least two forecast weights are required.")
        if any(weight <= 0 for weight in resolved_weights):
            raise ValueError("forecast weights must be positive.")
        if sum(resolved_weights) != Decimal("1"):
            raise ValueError("forecast weights must sum to 1.")
        if not Decimal("0") <= trend_damping <= Decimal("1"):
            raise ValueError("trend_damping must be between 0 and 1.")
        if not Decimal("0") <= p90_quantile <= Decimal("1"):
            raise ValueError("p90_quantile must be between 0 and 1.")

        self.weights = resolved_weights
        self.trend_damping = trend_damping
        self.p90_quantile = p90_quantile

    @property
    def window_weeks(self) -> int:
        return len(self.weights)

    def forecast(
        self,
        history: Sequence[WeeklyDemandPoint],
        *,
        horizon_weeks: int = 8,
    ) -> list[ForecastEstimate]:
        if not 1 <= horizon_weeks <= 52:
            raise ValueError("horizon_weeks must be between 1 and 52.")

        normalized = fill_missing_weeks(history)
        if len(normalized) < 2:
            raise ValueError("at least two weeks of demand history are required.")

        values = [point.units_sold for point in normalized]
        upper_error = upper_residual_quantile(
            self._backtest_residuals(values),
            self.p90_quantile,
        )
        recent = values[-self.window_weeks :]
        base = self._weighted_average(recent)
        trend = self._average_trend(recent) * self.trend_damping
        first_week = normalized[-1].week_start + timedelta(days=7)

        forecasts = []
        for step in range(1, horizon_weeks + 1):
            p50 = self._quantize(max(Decimal("0"), base + trend * step))
            p90 = self._quantize(max(p50, p50 + upper_error))
            forecasts.append(
                ForecastEstimate(
                    week_start=first_week + timedelta(days=7 * (step - 1)),
                    forecast_p50=p50,
                    forecast_p90=p90,
                )
            )
        return forecasts

    def parameters(self) -> dict[str, object]:
        return {
            "weights_recent_to_oldest": [str(weight) for weight in self.weights],
            "trend_damping": str(self.trend_damping),
            "p90_residual_quantile": str(self.p90_quantile),
            "window_weeks": self.window_weeks,
        }

    def _backtest_residuals(self, values: list[Decimal]) -> list[Decimal]:
        residuals = []
        for index in range(2, len(values)):
            recent = values[max(0, index - self.window_weeks) : index]
            predicted = self._point_forecast(recent)
            residuals.append(values[index] - predicted)
        return residuals

    def _point_forecast(self, recent: Sequence[Decimal]) -> Decimal:
        base = self._weighted_average(recent)
        trend = self._average_trend(recent) * self.trend_damping
        return max(Decimal("0"), base + trend)

    def _weighted_average(self, recent: Sequence[Decimal]) -> Decimal:
        active_weights = self.weights[: len(recent)]
        weight_total = sum(active_weights)
        return sum(
            value * weight
            for value, weight in zip(reversed(recent), active_weights, strict=True)
        ) / weight_total

    @staticmethod
    def _average_trend(recent: Sequence[Decimal]) -> Decimal:
        differences = [
            current - previous
            for previous, current in zip(recent, recent[1:])
        ]
        return sum(differences) / Decimal(len(differences))

    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        return value.quantize(SIX_PLACES, rounding=ROUND_HALF_UP)
