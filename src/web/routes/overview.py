from datetime import date

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import HTMLResponse

from application.services.overview import OverviewDashboardService
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork
from infrastructure.mock import FixedOverviewSupplementProvider
from web.dependencies import get_read_uow, get_web_settings
from web.presenters.overview import OverviewPresenter
from web.routes._common import resolve_sales_period
from web.settings import WebSettings


router = APIRouter(tags=["overview"])


@router.get("/overview", response_class=HTMLResponse)
def overview_page(
    request: Request,
    channel_account_id: list[str] = Query(default=[]),
    start_date: date | None = None,
    end_date: date | None = None,
    currency_code: str = "USD",
    unit_of_work: ReadOnlyUnitOfWork = Depends(get_read_uow),
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    default_start, default_end = resolve_sales_period(settings)
    resolved_start = start_date or default_start
    resolved_end = end_date or default_end
    channels = _resolve_channels(settings, channel_account_id)
    dashboard = OverviewDashboardService(
        sales_repository=unit_of_work.sales,
        refund_repository=unit_of_work.refunds,
        inventory_repository=unit_of_work.inventory,
        supplement_provider=FixedOverviewSupplementProvider(),
    ).get_dashboard(
        channel_account_ids=channels,
        start_date=resolved_start,
        end_date=resolved_end,
        currency_code=_resolve_currency(currency_code),
        limit=settings.web_overview_query_limit,
    )
    page = OverviewPresenter.to_page(
        dashboard,
        available_channel_account_ids=settings.channel_account_ids,
    )
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="overview/index.html",
        context={
            "page": page,
            "active_navigation": "overview",
            "web_title": settings.web_title,
        },
    )


def _resolve_channels(
    settings: WebSettings,
    requested: list[str],
) -> tuple[str, ...]:
    if not requested:
        return settings.channel_account_ids
    resolved = tuple(dict.fromkeys(value.strip() for value in requested))
    unsupported = [
        value
        for value in resolved
        if value not in settings.channel_account_ids
    ]
    if unsupported or any(not value for value in resolved):
        invalid = unsupported[0] if unsupported else "(blank)"
        raise ValueError(f"Unsupported channel_account_id: {invalid}.")
    return resolved


def _resolve_currency(value: str) -> str:
    resolved = value.strip().upper()
    if resolved != "USD":
        raise ValueError(f"Unsupported currency_code: {resolved or '(blank)'}.")
    return resolved
