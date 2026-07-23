from datetime import date
from typing import TypeVar

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session


ReadModelT = TypeVar("ReadModelT", bound=BaseModel)
MAX_QUERY_LIMIT = 10_000


def to_models(
    session: Session,
    statement: str,
    params: dict,
    model: type[ReadModelT],
) -> list[ReadModelT]:
    rows = session.execute(text(statement), params).mappings().all()
    return [model.model_validate(dict(row)) for row in rows]


def validate_limit(limit: int) -> int:
    if not 1 <= limit <= MAX_QUERY_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_QUERY_LIMIT}.")
    return limit


def validate_date_range(start: date, end: date) -> None:
    if start > end:
        raise ValueError("start date must not be after end date.")


def validate_channel_account_id(value: str) -> str:
    resolved = value.strip()
    if not resolved:
        raise ValueError("channel_account_id must not be blank.")
    return resolved
