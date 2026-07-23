from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException


def register_exception_handlers(
    app: FastAPI,
    templates: Jinja2Templates,
) -> None:
    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException,
    ) -> HTMLResponse:
        status_code = exc.status_code
        template = (
            "errors/404.html" if status_code == 404 else "errors/error.html"
        )
        return templates.TemplateResponse(
            request=request,
            name=template,
            context={
                "status_code": status_code,
                "message": str(exc.detail),
            },
            status_code=status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="errors/error.html",
            context={
                "status_code": 422,
                "message": "请求参数无效，请检查后重试。",
            },
            status_code=422,
        )

    @app.exception_handler(ValueError)
    async def value_exception_handler(
        request: Request,
        exc: ValueError,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="errors/error.html",
            context={"status_code": 400, "message": str(exc)},
            status_code=400,
        )

    @app.exception_handler(SQLAlchemyError)
    async def database_exception_handler(
        request: Request,
        exc: SQLAlchemyError,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="errors/error.html",
            context={
                "status_code": 503,
                "message": "数据库暂时不可用，请稍后重试。",
            },
            status_code=503,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request,
        exc: Exception,
    ) -> HTMLResponse:
        return templates.TemplateResponse(
            request=request,
            name="errors/error.html",
            context={
                "status_code": 500,
                "message": "系统暂时无法处理该请求。",
            },
            status_code=500,
        )
