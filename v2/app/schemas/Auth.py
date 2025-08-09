from typing import List, Optional
from pydantic import BaseModel
from .User import User

class GoogleUser(BaseModel):
    """
    Represents the user information received from Google's OAuth service.
    """
    email: str
    name: Optional[str] = None
    picture: Optional[str] = None

class DevUser(BaseModel):
    email: str = "dev@example.com"
    full_name: str = "Dev User"
    picture: Optional[str] = None
    is_dev: bool = True

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
