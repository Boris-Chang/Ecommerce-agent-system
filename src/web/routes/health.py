from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import Engine

from infrastructure.database.health import check_database_health
from web.dependencies import get_database_engine


router = APIRouter(tags=["health"])


@router.get("/health/live")
def health_live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready")
def health_ready(
    engine: Engine = Depends(get_database_engine),
) -> JSONResponse:
    try:
        health = check_database_health(engine)
    except Exception:
        return JSONResponse(
            status_code=503,
            content={"status": "unavailable", "database": "unavailable"},
        )

    status_code = 200 if health.healthy else 503
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "ready" if health.healthy else "unavailable",
            "database": health.database_name,
            "read_only": health.read_only,
        },
    )
