from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from application.services.sku import SkuSalesService
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork
from web.dependencies import get_read_uow, get_web_settings
from web.presenters import SalesPresenter
from web.routes._common import (
    resolve_channel_account_id,
    resolve_sales_period,
)
from web.settings import WebSettings


router = APIRouter(tags=["sales"])


@router.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse(url="/sales", status_code=302)


@router.get("/sales", response_class=HTMLResponse)
def sales_page(
    request: Request,
    channel_account_id: str | None = None,
    unit_of_work: ReadOnlyUnitOfWork = Depends(get_read_uow),
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    start_date, end_date = resolve_sales_period(settings)
    resolved_channel = resolve_channel_account_id(
        settings,
        channel_account_id,
    )
    rows = SkuSalesService(unit_of_work.sales).list_daily_sales(
        channel_account_id=resolved_channel,
        start_date=start_date,
        end_date=end_date,
        limit=settings.web_query_limit,
    )
    page = SalesPresenter.to_page(
        rows=rows,
        channel_account_id=resolved_channel,
        channel_account_ids=settings.channel_account_ids,
        start_date=start_date,
        end_date=end_date,
    )
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="sales/index.html",
        context={
            "page": page,
            "active_navigation": "sales",
            "active_sales_view": "daily",
            "web_title": settings.web_title,
        },
    )
