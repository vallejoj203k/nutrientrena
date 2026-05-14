from pydantic import BaseModel
from typing import Optional, List


class RoleCreateRequest(BaseModel):
    name: str
    slug: Optional[str] = None


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None


class MenuAssignRequest(BaseModel):
    role_id: int
    menu_ids: List[int]


class RoleOut(BaseModel):
    id: int
    name: str
    slug: Optional[str] = None

    model_config = {"from_attributes": True}
