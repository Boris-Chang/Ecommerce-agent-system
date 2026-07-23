from datetime import date, timedelta

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, RedirectResponse

from application.services.sku import SkuSalesService
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork
from web.dependencies import get_read_uow, get_web_settings
from web.presenters import SalesPresenter
from web.settings import WebSettings


router = APIRouter(tags=["sales"])


@router.get("/", include_in_schema=False)
def index() -> RedirectResponse:
    return RedirectResponse(url="/sales", status_code=302)


@router.get("/sales", response_class=HTMLResponse)
def sales_page(
    request: Request,
    unit_of_work: ReadOnlyUnitOfWork = Depends(get_read_uow),
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    end_date = settings.web_default_end_date or date.today()
    start_date = end_date - timedelta(
        days=settings.web_sales_lookback_days - 1
    )
    rows = SkuSalesService(unit_of_work.sales).list_daily_sales(
        channel_account_id=settings.web_default_channel_account_id,
        start_date=start_date,
        end_date=end_date,
        limit=settings.web_query_limit,
    )
    page = SalesPresenter.to_page(
        rows=rows,
        channel_account_id=settings.web_default_channel_account_id,
        start_date=start_date,
        end_date=end_date,
    )
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="sales/index.html",
        context={
            "page": page,
            "active_navigation": "sales",
            "web_title": settings.web_title,
        },
    )
