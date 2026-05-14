from pydantic import BaseModel, EmailStr
from typing import Optional


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class RecoverPasswordRequest(BaseModel):
    email: EmailStr


class MenuOut(BaseModel):
    menuId: int
    name: str
    icon: Optional[str] = None
    path: Optional[str] = None
    menuParentId: Optional[int] = None

    model_config = {"from_attributes": True}


class UserMeOut(BaseModel):
    id: int
    name: str
    last_name: Optional[str] = None
    email: str
    photo: Optional[str] = None
    role: Optional[str] = None
    slug: Optional[str] = None

    model_config = {"from_attributes": True}
