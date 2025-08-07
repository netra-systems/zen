from pydantic import BaseModel, EmailStr, Field
from typing import Optional
import uuid
from datetime import datetime

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: EmailStr
    created_at: datetime = Field(default_factory=datetime.utcnow)
    full_name: Optional[str] = None
    picture: Optional[str] = None

    class Config:
        from_attributes = True
