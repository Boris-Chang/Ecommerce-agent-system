from datetime import date, timedelta

from web.settings import WebSettings


def resolve_sales_period(settings: WebSettings) -> tuple[date, date]:
    end_date = settings.web_default_end_date or date.today()
    start_date = end_date - timedelta(
        days=settings.web_sales_lookback_days - 1
    )
    return start_date, end_date
