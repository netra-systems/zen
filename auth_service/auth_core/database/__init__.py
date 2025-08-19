"""
Auth Service Database Module
Database connection, models, and repositories for auth service
"""
from .connection import auth_db, get_db_session
from .models import AuthUser, AuthSession, AuthAuditLog
from .repository import (
    AuthUserRepository,
    AuthSessionRepository,
    AuthAuditRepository
)

__all__ = [
    "auth_db",
    "get_db_session",
    "AuthUser",
    "AuthSession",
    "AuthAuditLog",
    "AuthUserRepository",
    "AuthSessionRepository",
    "AuthAuditRepository"
]