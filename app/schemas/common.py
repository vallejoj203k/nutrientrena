from pydantic import BaseModel
from typing import Optional, Any, List, Generic, TypeVar

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    data: List[Any]
    total: int
    page: int
    per_page: int
    last_page: int


class SearchQuery(BaseModel):
    search: Optional[str] = None
    page: int = 1
    per_page: int = 15
    state: Optional[int] = None


class SuccessResponse(BaseModel):
    message: str
    data: Optional[Any] = None
