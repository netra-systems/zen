from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenPayload(BaseModel):
    sub: str
    user_id: Optional[str] = None
    roles: Optional[List[str]] = None
    permissions: Optional[List[str]] = None
    exp: Optional[datetime] = None
