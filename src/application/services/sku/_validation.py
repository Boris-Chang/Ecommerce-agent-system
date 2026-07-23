from datetime import date


MAX_QUERY_LIMIT = 10_000


def validate_channel_account_id(value: str) -> str:
    resolved = value.strip()
    if not resolved:
        raise ValueError("channel_account_id must not be blank.")
    return resolved


def validate_query(
    start_date: date,
    end_date: date,
    limit: int,
) -> None:
    if start_date > end_date:
        raise ValueError("start_date must not be after end_date.")
    if not 1 <= limit <= MAX_QUERY_LIMIT:
        raise ValueError(f"limit must be between 1 and {MAX_QUERY_LIMIT}.")
