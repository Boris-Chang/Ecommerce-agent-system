from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse

from application.services.inventory import (
    InventoryBalanceService,
    InventoryRiskService,
)
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork
from web.dependencies import get_read_uow, get_web_settings
from web.presenters import InventoryPresenter
from web.settings import WebSettings


router = APIRouter(tags=["inventory"])


@router.get("/inventory", response_class=HTMLResponse)
def inventory_page(
    request: Request,
    unit_of_work: ReadOnlyUnitOfWork = Depends(get_read_uow),
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    balances = InventoryBalanceService(
        unit_of_work.inventory
    ).list_current_inventory(limit=settings.web_query_limit)
    risk_service = InventoryRiskService(unit_of_work.inventory)
    replenishment_risks = risk_service.list_replenishment_risks(
        limit=settings.web_query_limit
    )
    overstock_risks = risk_service.list_overstock_risks(
        limit=settings.web_query_limit
    )
    page = InventoryPresenter.to_page(
        balances=balances,
        replenishment_risks=replenishment_risks,
        overstock_risks=overstock_risks,
    )
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="inventory/index.html",
        context={
            "page": page,
            "active_navigation": "inventory",
            "web_title": settings.web_title,
        },
    )
