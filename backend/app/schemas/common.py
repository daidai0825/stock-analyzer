"""Common Pydantic response schemas shared across multiple route modules."""

from pydantic import BaseModel


class MetaResponse(BaseModel):
    """Pagination metadata returned in list endpoint envelopes."""

    total: int
    page: int
    limit: int
