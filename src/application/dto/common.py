from pydantic import BaseModel, ConfigDict


class ReadModel(BaseModel):
    """Immutable base model for application-layer read DTOs."""

    model_config = ConfigDict(frozen=True)
