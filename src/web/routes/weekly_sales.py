from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from application.services.sku import SkuSalesService
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork
from web.dependencies import get_read_uow, get_web_settings
from web.presenters import WeeklySalesPresenter
from web.routes._common import resolve_sales_period
from web.settings import WebSettings


router = APIRouter(tags=["sales"])


@router.get("/sales/weekly", response_class=HTMLResponse)
def weekly_sales_page(
    request: Request,
    unit_of_work: ReadOnlyUnitOfWork = Depends(get_read_uow),
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    start_date, end_date = resolve_sales_period(settings)
    rows = SkuSalesService(unit_of_work.sales).list_weekly_sales(
        channel_account_id=settings.web_default_channel_account_id,
        start_date=start_date,
        end_date=end_date,
        limit=settings.web_query_limit,
    )
    page = WeeklySalesPresenter.to_page(
        rows=rows,
        channel_account_id=settings.web_default_channel_account_id,
        start_date=start_date,
        end_date=end_date,
    )
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="sales/weekly.html",
        context={
            "page": page,
            "active_navigation": "sales",
            "active_sales_view": "weekly",
            "web_title": settings.web_title,
        },
    )
