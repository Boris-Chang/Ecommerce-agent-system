"""Forecast uncertainty evaluation helpers."""

from decimal import Decimal


def upper_residual_quantile(
    residuals: list[Decimal],
    quantile: Decimal,
) -> Decimal:
    """Return a linearly interpolated upper-demand residual quantile."""
    if not residuals:
        return Decimal("0")
    if not Decimal("0") <= quantile <= Decimal("1"):
        raise ValueError("quantile must be between 0 and 1.")

    ordered = sorted(max(Decimal("0"), value) for value in residuals)
    position = Decimal(len(ordered) - 1) * quantile
    lower_index = int(position)
    upper_index = min(lower_index + 1, len(ordered) - 1)
    fraction = position - Decimal(lower_index)
    return ordered[lower_index] + (
        ordered[upper_index] - ordered[lower_index]
    ) * fraction
