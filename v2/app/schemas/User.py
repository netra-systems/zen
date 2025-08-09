from pydantic import BaseModel, EmailStr
from typing import Optional

class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None
    picture: Optional[str] = None

class UserCreate(UserBase):
    password: str

class UserCreateOAuth(UserBase):
    pass

class UserUpdate(UserBase):
    pass

class User(UserBase):
    id: str
    is_active: bool
    is_superuser: bool
    hashed_password: Optional[str] = None

    class Config:
        from_attributes = True