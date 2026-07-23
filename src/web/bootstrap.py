from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.settings import DatabaseSettings
from infrastructure.database import (
    create_database_engine,
    create_session_factory,
)
from web.exception_handlers import register_exception_handlers
from web.paths import STATIC_DIR, TEMPLATES_DIR
from web.routes import health, inventory, sales
from web.settings import WebSettings


def create_app(
    *,
    database_settings: DatabaseSettings | None = None,
    web_settings: WebSettings | None = None,
) -> FastAPI:
    resolved_web_settings = web_settings or WebSettings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        engine = create_database_engine(database_settings)
        app.state.database_engine = engine
        app.state.session_factory = create_session_factory(engine)
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
    app.include_router(sales.router)
    app.include_router(inventory.router)
    register_exception_handlers(app, templates)
    return app
