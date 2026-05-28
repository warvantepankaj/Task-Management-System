from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    """
    Unified response envelope for paginated list endpoints.

    `total_pages` is derived (`ceil(total / page_size)`) but it's cheap and
    convenient for the frontend, so we ship it on the wire.
    """
    total: int
    page: int
    page_size: int
    total_pages: int
    data: List[T]
