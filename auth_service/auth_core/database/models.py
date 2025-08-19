"""
Auth Service Database Models
SQLAlchemy models for auth service database persistence
"""
from sqlalchemy import Column, String, DateTime, Boolean, JSON, Integer
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timezone
import uuid

Base = declarative_base()

class AuthUser(Base):
    """Auth service user model for authentication data"""
    __tablename__ = "auth_users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)  # Null for OAuth users
    
    # OAuth provider information
    auth_provider = Column(String, nullable=False, default="local")
    provider_user_id = Column(String, nullable=True)  # Provider's user ID
    provider_data = Column(JSON, nullable=True)  # Additional provider data
    
    # Account status
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), 
                       default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), 
                       default=lambda: datetime.now(timezone.utc),
                       onupdate=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    
    # Security tracking
    failed_login_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime(timezone=True), nullable=True)

class AuthSession(Base):
    """Active session tracking"""
    __tablename__ = "auth_sessions"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    refresh_token_hash = Column(String, nullable=True)
    
    # Session metadata
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    device_id = Column(String, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), 
                       default=lambda: datetime.now(timezone.utc))
    expires_at = Column(DateTime(timezone=True), nullable=False)
    last_activity = Column(DateTime(timezone=True), 
                          default=lambda: datetime.now(timezone.utc))
    
    # Status
    is_active = Column(Boolean, default=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

class AuthAuditLog(Base):
    """Audit log for authentication events"""
    __tablename__ = "auth_audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=True, index=True)
    
    # Event details
    success = Column(Boolean, nullable=False)
    error_message = Column(String, nullable=True)
    event_metadata = Column(JSON, nullable=True)
    
    # Request context
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)
    
    # Timestamp
    created_at = Column(DateTime(timezone=True), 
                       default=lambda: datetime.now(timezone.utc), 
                       index=True)

class PasswordResetToken(Base):
    """Password reset token tracking"""
    __tablename__ = "password_reset_tokens"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, nullable=False, index=True)
    token_hash = Column(String, nullable=False, unique=True)
    email = Column(String, nullable=False, index=True)
    
    # Token status
    is_used = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), 
                       default=lambda: datetime.now(timezone.utc))
    used_at = Column(DateTime(timezone=True), nullable=True)