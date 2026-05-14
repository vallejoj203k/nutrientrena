from pydantic import BaseModel
from typing import Optional, List


class RoleCreateRequest(BaseModel):
    name: str


class RoleUpdateRequest(BaseModel):
    name: Optional[str] = None


class MenuAssignRequest(BaseModel):
    role_id: int
    menu_ids: List[int]


class RoleOut(BaseModel):
    id: int
    name: str

    model_config = {"from_attributes": True}
