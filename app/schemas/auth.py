from pydantic import BaseModel, EmailStr
from typing import Optional, List


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
    remember_me: Optional[bool] = False


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RecoverPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    password: str


class MenuOut(BaseModel):
    menuId: int
    name: str
    icon: Optional[str] = None
    path: Optional[str] = None
    menuParentId: Optional[int] = None
    childMenu: Optional[List["MenuOut"]] = []

    model_config = {"from_attributes": True}


MenuOut.model_rebuild()


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
