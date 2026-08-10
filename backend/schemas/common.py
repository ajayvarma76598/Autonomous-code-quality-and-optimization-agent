from pydantic import BaseModel, ConfigDict, EmailStr
from typing import Optional, List, Generic, TypeVar
from datetime import datetime
from uuid import UUID

T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    success: bool = True
    message: Optional[str] = None
    data: Optional[T] = None

class PaginatedResponse(BaseModel, Generic[T]):
    items: List[T]
    total: int
    page: int
    size: int
    pages: int

class UserBase(BaseModel):
    email: EmailStr
    username: str
    role: Optional[str] = "developer"

class UserCreate(UserBase):
    pass

class UserInDBBase(UserBase):
    user_id: UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)

class User(UserInDBBase):
    pass
