from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from application.services.inventory import InventoryDashboardService
from infrastructure.mock import FixedInventoryDashboardSupplementProvider
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork
from web.dependencies import get_read_uow, get_web_settings
from web.presenters import InventoryDashboardPresenter
from web.settings import WebSettings


router = APIRouter(tags=["inventory"])


@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(
    request: Request,
    warehouse_id: str | None = None,
    search: str | None = None,
    unit_of_work: ReadOnlyUnitOfWork = Depends(get_read_uow),
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    dashboard = InventoryDashboardService(
        repository=unit_of_work.inventory,
        supplement_provider=FixedInventoryDashboardSupplementProvider(),
    ).get_dashboard(
        warehouse_id=warehouse_id,
        search=search,
        limit=settings.web_overview_query_limit,
    )
    page = InventoryDashboardPresenter.to_page(dashboard)
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="inventory/index.html",
        context={
            "page": page,
            "active_navigation": "inventory",
            "web_title": settings.web_title,
        },
    )
