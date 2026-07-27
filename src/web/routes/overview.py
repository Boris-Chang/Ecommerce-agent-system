from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from application.services.overview import OverviewDashboardService
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork
from infrastructure.mock import FixedOverviewSupplementProvider
from web.dependencies import get_read_uow, get_web_settings
from web.presenters.overview import OverviewPresenter
from web.routes._common import resolve_channel_account_id
from web.settings import WebSettings


router = APIRouter(tags=["overview"])


@router.get("/overview", response_class=HTMLResponse)
def overview_page(
    request: Request,
    channel_account_id: str | None = None,
    currency_code: str = "USD",
    unit_of_work: ReadOnlyUnitOfWork = Depends(get_read_uow),
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    resolved_channel = resolve_channel_account_id(
        settings,
        channel_account_id,
    )
    as_of_date = settings.web_default_end_date or date.today()
    dashboard = OverviewDashboardService(
        sales_repository=unit_of_work.sales,
        refund_repository=unit_of_work.refunds,
        inventory_repository=unit_of_work.inventory,
        order_repository=unit_of_work.orders,
        supplement_provider=FixedOverviewSupplementProvider(),
    ).get_dashboard(
        channel_account_id=resolved_channel,
        as_of_date=as_of_date,
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


def _resolve_currency(value: str) -> str:
    resolved = value.strip().upper()
    if resolved != "USD":
        raise ValueError(f"Unsupported currency_code: {resolved or '(blank)'}.")
    return resolved
