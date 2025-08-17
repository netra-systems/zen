"""
Auth Module - Client interface to auth service
All auth operations go through the standalone auth service
"""
from app.clients.auth_client import auth_client

__all__ = ["auth_client"]