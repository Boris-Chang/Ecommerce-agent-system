from uuid import UUID, uuid4


def new_uuid() -> UUID:
    """Return a UUID suitable for future application-owned records."""
    return uuid4()
