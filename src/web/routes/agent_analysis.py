from datetime import date, timedelta

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse

from application.agents.business_inspection import (
    BusinessInspectionRequest,
    BusinessInspectionService,
)
from web.dependencies import (
    get_business_inspection_service,
    get_web_settings,
)
from web.presenters.agent_analysis import AgentAnalysisPresenter
from web.routes._common import resolve_channel_account_id
from web.settings import WebSettings


router = APIRouter(prefix="/agent-analysis", tags=["agent-analysis"])


@router.get("", response_class=HTMLResponse)
def agent_analysis_page(
    request: Request,
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    page = AgentAnalysisPresenter.empty_page(
        frequency="daily",
        channel_account_id=settings.web_default_channel_account_id,
        channel_account_ids=settings.channel_account_ids,
    )
    return _render(request, settings, page)


@router.post("/refresh", response_class=HTMLResponse)
def refresh_agent_analysis(
    request: Request,
    frequency: str = Form(...),
    channel_account_id: str = Form(...),
    service: BusinessInspectionService = Depends(
        get_business_inspection_service
    ),
    settings: WebSettings = Depends(get_web_settings),
) -> HTMLResponse:
    if frequency not in {"daily", "weekly"}:
        raise ValueError("frequency must be daily or weekly.")
    resolved_channel = resolve_channel_account_id(
        settings,
        channel_account_id,
    )
    end_date = settings.web_default_end_date or date.today()
    start_date = (
        end_date
        if frequency == "daily"
        else end_date - timedelta(days=6)
    )
    output = service.run(
        BusinessInspectionRequest(
            frequency=frequency,
            channel_account_id=resolved_channel,
            start_date=start_date,
            end_date=end_date,
            limit=min(settings.web_query_limit, 500),
        )
    )
    page = AgentAnalysisPresenter.to_page(
        output,
        channel_account_ids=settings.channel_account_ids,
    )
    return _render(request, settings, page)


def _render(
    request: Request,
    settings: WebSettings,
    page: object,
) -> HTMLResponse:
    return request.app.state.templates.TemplateResponse(
        request=request,
        name="agent_analysis/index.html",
        context={
            "page": page,
            "active_navigation": "agent_analysis",
            "web_title": settings.web_title,
        },
    )
