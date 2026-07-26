from datetime import date

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from application.services.sku import SkuDashboardService
from infrastructure.mock import FixedSkuDashboardSupplementProvider
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork
from web.dependencies import get_read_uow, get_web_settings
from web.presenters import SkuDashboardPresenter
from web.routes._common import (
    resolve_channel_account_id,
    resolve_sales_period,
)
from web.settings import WebSettings


router = APIRouter(tags=["sales"])


@router.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse(url="/overview", status_code=302)


@router.get("/sales", response_class=HTMLResponse)
def sales_page(
    request: Request,
    channel_account_id: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
    currency_code: str = "USD",
    grain: str = "daily",
    search: str | None = None,
    unit_of_work: ReadOnlyUnitOfWork = Depends(get_read_uow),
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    default_start, default_end = resolve_sales_period(settings)
    resolved_start = start_date or default_start
    resolved_end = end_date or default_end
    resolved_channel = resolve_channel_account_id(
        settings,
        channel_account_id,
    )
    dashboard = SkuDashboardService(
        sales_repository=unit_of_work.sales,
        refund_repository=unit_of_work.refunds,
        inventory_repository=unit_of_work.inventory,
        supplement_provider=FixedSkuDashboardSupplementProvider(),
    ).get_dashboard(
        channel_account_id=resolved_channel,
        start_date=resolved_start,
        end_date=resolved_end,
        currency_code=_resolve_currency(currency_code),
        grain=grain,
        search=search,
        limit=settings.web_overview_query_limit,
    )
    page = SkuDashboardPresenter.to_page(
        dashboard,
        channel_account_ids=settings.channel_account_ids,
    )
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="sales/index.html",
        context={
            "page": page,
            "active_navigation": "sku",
            "web_title": settings.web_title,
        },
    )


def _resolve_currency(value: str) -> str:
    resolved = value.strip().upper()
    if resolved != "USD":
        raise ValueError(f"Unsupported currency_code: {resolved or '(blank)'}.")
    return resolved
