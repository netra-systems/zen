"""User and authentication related database models.

Defines User, Secret, and ToolUsageLog models for authentication and user management.
Focused module adhering to modular architecture and single responsibility.
"""

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from .base import Base
import uuid
from datetime import datetime, timezone


class User(Base):
    __tablename__ = "userbase"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, index=True)
    hashed_password = Column(String, nullable=True)
    picture = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    is_active = Column(Boolean(), default=True)
    is_superuser = Column(Boolean(), default=False)
    # Admin permission fields
    role = Column(String, default="standard_user")  # standard_user, power_user, developer, admin, super_admin
    permissions = Column(JSON, default=dict)  # Additional granular permissions
    is_developer = Column(Boolean(), default=False)  # Auto-detected developer status
    
    # New plan and tool permission fields
    plan_tier = Column(String, default="free")  # free, pro, enterprise, developer
    plan_expires_at = Column(DateTime(timezone=True), nullable=True)  # Plan expiration
    feature_flags = Column(JSON, default=dict)  # Enabled feature flags
    tool_permissions = Column(JSON, default=dict)  # Per-tool permission overrides
    
    # Plan billing fields
    plan_started_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    auto_renew = Column(Boolean(), default=False)  # Auto-renewal enabled
    payment_status = Column(String, default="active")  # active, suspended, cancelled
    trial_period = Column(Boolean(), default=False)  # Is in trial period
    
    # Relationships
    secrets = relationship("Secret", back_populates="user", cascade="all, delete-orphan")


class Secret(Base):
    __tablename__ = "secrets"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("userbase.id"), nullable=False)
    key = Column(String, nullable=False)
    encrypted_value = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc))
    user = relationship("User", back_populates="secrets")


class ToolUsageLog(Base):
    __tablename__ = "tool_usage_logs"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String, ForeignKey("userbase.id"), nullable=False)
    tool_name = Column(String, nullable=False, index=True)
    category = Column(String, index=True)
    execution_time_ms = Column(Integer, default=0)
    tokens_used = Column(Integer, nullable=True)
    cost_cents = Column(Integer, nullable=True)
    status = Column(String, nullable=False, index=True)  # success, error, permission_denied, rate_limited
    plan_tier = Column(String, nullable=False)  # User's plan at time of usage
    permission_check_result = Column(JSON, nullable=True)  # Permission check details
    arguments = Column(JSON, nullable=True)  # Tool arguments (for analytics)
    created_at = Column(DateTime(timezone=True), default=datetime.now(timezone.utc), index=True)
    
    user = relationship("User")