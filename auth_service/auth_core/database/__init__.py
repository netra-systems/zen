"""
Auth Service Database Module
Database connection, models, and repositories for auth service
"""
try:
    from auth_service.auth_core.database.connection import auth_db, get_db_session
    from auth_service.auth_core.database.models import AuthAuditLog, AuthSession, AuthUser
    from auth_service.auth_core.database.repository import (
        AuthAuditRepository,
        AuthSessionRepository,
        AuthUserRepository,
    )
except ImportError:
    # Fallback to relative imports for direct execution
    from auth_service.auth_core.database.connection import auth_db, get_db_session
    from auth_service.auth_core.database.models import AuthAuditLog, AuthSession, AuthUser
    from .repository import (
        AuthAuditRepository,
        AuthSessionRepository,
        AuthUserRepository,
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