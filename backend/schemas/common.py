from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr


class APIResponse[T](BaseModel):
    success: bool = True
    message: str | None = None
    data: T | None = None


class PaginatedResponse[T](BaseModel):
    items: list[T]
    total: int
    page: int
    size: int
    pages: int


class UserBase(BaseModel):
    email: EmailStr
    username: str
    role: str | None = "developer"


class UserCreate(UserBase):
    pass


class UserInDBBase(UserBase):
    user_id: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class User(UserInDBBase):
    pass
