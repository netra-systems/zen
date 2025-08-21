"""
Auth Service Database Module
Database connection, models, and repositories for auth service
"""
from auth_service.app.connection import auth_db, get_db_session
from auth_service.app.models import AuthUser, AuthSession, AuthAuditLog
from auth_service.app.repository import (
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