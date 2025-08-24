"""
Auth Service Database Module - Single Source of Truth for Auth Database Access

CRITICAL: This is the ONLY location where auth database sessions should be re-exported.
The primary implementation is in auth_service.auth_core.database.connection.

Business Value Justification (BVJ):
- Segment: Platform stability (all tiers)  
- Business Goal: Eliminate duplicate database session management code
- Value Impact: Ensures auth service integrity and prevents "Abominations" per CLAUDE.md
- Strategic Impact: Single source of truth for auth database access patterns
"""

# Import from SINGLE SOURCE OF TRUTH - connection.py
from auth_service.auth_core.database.connection import auth_db, get_db_session
from auth_service.auth_core.database.models import AuthAuditLog, AuthSession, AuthUser
from auth_service.auth_core.database.repository import (
    AuthAuditRepository,
    AuthSessionRepository,
    AuthUserRepository,
)

# NO fallback imports - use absolute imports only per CLAUDE.md

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