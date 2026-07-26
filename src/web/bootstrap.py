from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.settings import DatabaseSettings
from infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from infrastructure.llm.agent_runtime.agent_app import (
    create_business_inspection_service,
)
from web.exception_handlers import register_exception_handlers
from web.paths import STATIC_DIR, TEMPLATES_DIR
from web.routes import (
    agent_analysis,
    channel_sales,
    health,
    inventory,
    refunds,
    sales,
    weekly_sales,
)
from web.settings import WebSettings


def create_app(
    *,
    database_settings: DatabaseSettings | None = None,
    web_settings: WebSettings | None = None,
) -> FastAPI:
    _configure_inspection_logging()
    resolved_web_settings = web_settings or WebSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(database_settings)
        app.state.database_engine = engine
        app.state.session_factory = create_session_factory(engine)
        app.state.business_inspection_service = (
            create_business_inspection_service(app.state.session_factory)
        )
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(
        title=resolved_web_settings.web_title,
        lifespan=lifespan,
    )
    app.state.web_settings = resolved_web_settings
    templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
    app.state.templates = templates

    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
    app.include_router(health.router)
    app.include_router(agent_analysis.router)
    app.include_router(sales.router)
    app.include_router(weekly_sales.router)
    app.include_router(refunds.router)
    app.include_router(channel_sales.router)
    app.include_router(inventory.router)
    register_exception_handlers(app, templates)
    return app


def _configure_inspection_logging() -> None:
    """Expose traceable inspection events through Uvicorn's log handlers."""
    logging.getLogger(
        "application.agents.business_inspection"
    ).setLevel(logging.INFO)
    logging.getLogger("infrastructure.llm").setLevel(logging.INFO)
