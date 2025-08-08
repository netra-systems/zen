from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime

class User(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    email: str
    full_name: Optional[str] = None
    picture: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)

class DevLoginRequest(BaseModel):
    email: str

class AuthEndpoints(BaseModel):
    login: str
    logout: str
    token: str
    user: str
    dev_login: str

class AuthConfigResponse(BaseModel):
    google_client_id: str
    endpoints: AuthEndpoints
    development_mode: bool
    user: Optional[User] = None
    authorized_javascript_origins: List[str]
    authorized_redirect_uris: List[str]
