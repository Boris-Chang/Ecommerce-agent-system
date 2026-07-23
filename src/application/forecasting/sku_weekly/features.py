from datetime import date, timedelta
from decimal import Decimal
from typing import Sequence

from application.forecasting.sku_weekly.schemas import WeeklyDemandPoint


def fill_missing_weeks(
    history: Sequence[WeeklyDemandPoint],
) -> list[WeeklyDemandPoint]:
    """Sort weekly history and fill missing Monday-starting weeks with zero demand."""
    if not history:
        return []

    by_week: dict[date, Decimal] = {}
    for point in history:
        if point.week_start.weekday() != 0:
            raise ValueError("week_start must be a Monday.")
        if point.units_sold < 0:
            raise ValueError("weekly units_sold must not be negative.")
        if point.week_start in by_week:
            raise ValueError(f"duplicate weekly demand for {point.week_start}.")
        by_week[point.week_start] = point.units_sold

    first_week = min(by_week)
    last_week = max(by_week)
    normalized = []
    current_week = first_week
    while current_week <= last_week:
        normalized.append(
            WeeklyDemandPoint(
                week_start=current_week,
                units_sold=by_week.get(current_week, Decimal("0")),
            )
        )
        current_week += timedelta(days=7)
    return normalized
