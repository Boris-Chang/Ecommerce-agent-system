from datetime import datetime
from decimal import Decimal


def format_money(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f}"


def format_percent(value: Decimal | None) -> str:
    if value is None:
        return "—"
    return f"{value:,.2f}%"


def format_timestamp(value: datetime | None) -> str:
    if value is None:
        return "暂无"
    return value.astimezone().strftime("%Y-%m-%d %H:%M")
