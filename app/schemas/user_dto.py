from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr


class UserCreateDTO(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserUpdateDTO(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None


class UserResponse(BaseModel):
    id: UUID
    name: str
    email: EmailStr
    role: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
