"""
Auth Service Database Models
SQLAlchemy models for auth service database persistence

These models include Python-level default initialization to ensure
compatibility with testing frameworks that expect defaults to be 
available at object creation time.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from shared.id_generation.unified_id_generator import UnifiedIdGenerator

class Base(DeclarativeBase):
    """Declarative base class for auth service models using SQLAlchemy 2.0 patterns."""
    pass

class AuthUser(Base):
    """Auth service user model for authentication data"""
    __tablename__ = "auth_users"
    
    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: UnifiedIdGenerator.generate_base_id("auth_user"))
    
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
    
    def __init__(self, **kwargs):
        """Initialize with proper defaults for testing compatibility."""
        # Set Python-level defaults before calling super().__init__
        if 'id' not in kwargs:
            kwargs['id'] = UnifiedIdGenerator.generate_base_id("auth_user")
        if 'auth_provider' not in kwargs:
            kwargs['auth_provider'] = "local"
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        if 'is_verified' not in kwargs:
            kwargs['is_verified'] = False
        if 'failed_login_attempts' not in kwargs:
            kwargs['failed_login_attempts'] = 0
        
        super().__init__(**kwargs)

class AuthSession(Base):
    """Active session tracking"""
    __tablename__ = "auth_sessions"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: UnifiedIdGenerator.generate_base_id("auth_session"))
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
    
    def __init__(self, **kwargs):
        """Initialize with proper defaults for testing compatibility."""
        if 'id' not in kwargs:
            kwargs['id'] = UnifiedIdGenerator.generate_base_id("auth_session")
        if 'is_active' not in kwargs:
            kwargs['is_active'] = True
        
        super().__init__(**kwargs)

class AuthAuditLog(Base):
    """Audit log for authentication events"""
    __tablename__ = "auth_audit_logs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: UnifiedIdGenerator.generate_base_id("auth_audit_log"))
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
    
    def __init__(self, **kwargs):
        """Initialize with proper defaults for testing compatibility."""
        if 'id' not in kwargs:
            kwargs['id'] = UnifiedIdGenerator.generate_base_id("auth_audit_log")
        
        super().__init__(**kwargs)

class PasswordResetToken(Base):
    """Password reset token tracking"""
    __tablename__ = "password_reset_tokens"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: UnifiedIdGenerator.generate_base_id("password_reset_token"))
    user_id: Mapped[str] = mapped_column(String, index=True)
    token_hash: Mapped[str] = mapped_column(String, unique=True)
    email: Mapped[str] = mapped_column(String, index=True)
    
    # Token status
    is_used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    
    def __init__(self, **kwargs):
        """Initialize with proper defaults for testing compatibility."""
        if 'id' not in kwargs:
            kwargs['id'] = UnifiedIdGenerator.generate_base_id("password_reset_token")
        if 'is_used' not in kwargs:
            kwargs['is_used'] = False
        
        super().__init__(**kwargs)