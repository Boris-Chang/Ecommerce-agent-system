from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from application.services.sku import SkuRefundService
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork
from web.dependencies import get_read_uow, get_web_settings
from web.presenters import RefundsPresenter
from web.routes._common import resolve_sales_period
from web.settings import WebSettings


router = APIRouter(tags=["refunds"])


@router.get("/sales/refunds", response_class=HTMLResponse)
def refunds_page(
    request: Request,
    unit_of_work: ReadOnlyUnitOfWork = Depends(get_read_uow),
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    start_date, end_date = resolve_sales_period(settings)
    service = SkuRefundService(unit_of_work.refunds)
    daily_rows = service.list_daily_refunds(
        channel_account_id=settings.web_default_channel_account_id,
        start_date=start_date,
        end_date=end_date,
        limit=settings.web_query_limit,
    )
    weekly_rows = service.list_weekly_refunds(
        channel_account_id=settings.web_default_channel_account_id,
        start_date=start_date,
        end_date=end_date,
        limit=settings.web_query_limit,
    )
    page = RefundsPresenter.to_page(
        daily_rows=daily_rows,
        weekly_rows=weekly_rows,
        channel_account_id=settings.web_default_channel_account_id,
        start_date=start_date,
        end_date=end_date,
    )
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="sales/refunds.html",
        context={
            "page": page,
            "active_navigation": "sales",
            "active_sales_view": "refunds",
            "web_title": settings.web_title,
        },
    )
