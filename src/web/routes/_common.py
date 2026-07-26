from datetime import date, timedelta

from web.settings import WebSettings


def resolve_sales_period(settings: WebSettings) -> tuple[date, date]:
    end_date = settings.web_default_end_date or date.today()
    start_date = end_date - timedelta(
        days=settings.web_sales_lookback_days - 1
    )
    return start_date, end_date


def resolve_channel_account_id(
    settings: WebSettings,
    requested_channel_account_id: str | None,
) -> str:
    if requested_channel_account_id is None:
        return settings.web_default_channel_account_id

    resolved = requested_channel_account_id.strip()
    if resolved not in settings.channel_account_ids:
        raise ValueError(
            f"Unsupported channel_account_id: {resolved or '(blank)'}."
        )
    return resolved
