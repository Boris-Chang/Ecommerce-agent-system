from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from application.services.channel import ChannelSalesShareService
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork
from web.dependencies import get_read_uow, get_web_settings
from web.presenters import ChannelSalesSharePresenter
from web.routes._common import resolve_sales_period
from web.settings import WebSettings


router = APIRouter(tags=["channels"])


@router.get("/sales/channels", response_class=HTMLResponse)
def channel_sales_page(
    request: Request,
    unit_of_work: ReadOnlyUnitOfWork = Depends(get_read_uow),
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    start_date, end_date = resolve_sales_period(settings)
    rows = ChannelSalesShareService(
        unit_of_work.channel_sales
    ).list_sales_shares(
        start_date=start_date,
        end_date=end_date,
    )
    page = ChannelSalesSharePresenter.to_page(
        rows=rows,
        start_date=start_date,
        end_date=end_date,
    )
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="sales/channels.html",
        context={
            "page": page,
            "active_navigation": "channel",
            "active_sales_view": "channels",
            "web_title": settings.web_title,
        },
    )
