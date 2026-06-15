from pydantic import BaseModel, EmailStr

from app.schemas.mixins import BaseMixin


class UserCreateDTO(BaseModel):
    name: str
    email: EmailStr
    password: str


class UserUpdateDTO(BaseModel):
    name: str | None = None
    email: EmailStr | None = None
    password: str | None = None


class UserResponse(BaseMixin):
    name: str
    email: EmailStr
    role: str

    model_config = {"from_attributes": True}
