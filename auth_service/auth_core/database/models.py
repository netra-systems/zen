"""
Auth Service Database Models
SQLAlchemy models for auth service database persistence
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    """Declarative base class for auth service models using SQLAlchemy 2.0 patterns."""
    pass

class AuthUser(Base):
    """Auth service user model for authentication data"""
    __tablename__ = "auth_users"
    
    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Core user fields
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String)
    hashed_password: Mapped[Optional[str]] = mapped_column(String)  # Null for OAuth users
    
    # OAuth provider information
    auth_provider: Mapped[str] = mapped_column(String, default="local")
    provider_user_id: Mapped[Optional[str]] = mapped_column(String)  # Provider's user ID
    provider_data: Mapped[Optional[dict]] = mapped_column(JSON)  # Additional provider data
    
    # Account status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    last_login_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    # Security tracking
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

class AuthSession(Base):
    """Active session tracking"""
    __tablename__ = "auth_sessions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True)
    refresh_token_hash: Mapped[Optional[str]] = mapped_column(String)
    
    # Session metadata
    ip_address: Mapped[Optional[str]] = mapped_column(String)
    user_agent: Mapped[Optional[str]] = mapped_column(String)
    device_id: Mapped[Optional[str]] = mapped_column(String)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_activity: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

class AuthAuditLog(Base):
    """Audit log for authentication events"""
    __tablename__ = "auth_audit_logs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String, index=True)
    user_id: Mapped[Optional[str]] = mapped_column(String, index=True)
    
    # Event details
    success: Mapped[bool] = mapped_column(Boolean)
    error_message: Mapped[Optional[str]] = mapped_column(String)
    event_metadata: Mapped[Optional[dict]] = mapped_column(JSON)
    
    # Request context
    ip_address: Mapped[Optional[str]] = mapped_column(String)
    user_agent: Mapped[Optional[str]] = mapped_column(String)
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)

class PasswordResetToken(Base):
    """Password reset token tracking"""
    __tablename__ = "password_reset_tokens"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, index=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[str] = mapped_column(String, index=True)
    
    # Token status
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))