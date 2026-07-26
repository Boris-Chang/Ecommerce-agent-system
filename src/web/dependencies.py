from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import Engine

from application.agents.business_inspection import BusinessInspectionService
from infrastructure.database.session import SessionFactory
from infrastructure.database.unit_of_work import ReadOnlyUnitOfWork
from web.settings import WebSettings


def get_web_settings(request: Request) -> WebSettings:
    return request.app.state.web_settings


def get_database_engine(request: Request) -> Engine:
    return request.app.state.database_engine


def get_session_factory(request: Request) -> SessionFactory:
    return request.app.state.session_factory


def get_business_inspection_service(
    request: Request,
) -> BusinessInspectionService:
    return request.app.state.business_inspection_service


def get_read_uow(request: Request) -> Iterator[ReadOnlyUnitOfWork]:
    session_factory = get_session_factory(request)
    with ReadOnlyUnitOfWork(session_factory) as unit_of_work:
        yield unit_of_work
