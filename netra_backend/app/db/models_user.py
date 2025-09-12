"""User and authentication related database models.

[U+1F534] CRITICAL: Auth Service Architecture
- The User table stores user PROFILE data only
- Authentication is handled by the EXTERNAL auth service
- The hashed_password field is ONLY managed by the auth service
- Main backend must NEVER directly authenticate users or hash passwords

 WARNING: [U+FE0F] IMPORTANT:
- User records are created/updated by the auth service
- Main backend can READ user data for authorization
- Main backend must NEVER write to authentication fields
- All password operations go through auth_client

See: app/auth_integration/CRITICAL_AUTH_ARCHITECTURE.md
"""

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from netra_backend.app.db.base import Base


class User(Base):
    __tablename__ = "users"
    
    # Primary key
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    
    # Core user fields
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    full_name: Mapped[Optional[str]] = mapped_column(String, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String)
    picture: Mapped[Optional[str]] = mapped_column(String)
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    # Status fields
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_developer: Mapped[bool] = mapped_column(Boolean, default=False)  # Auto-detected developer status
    
    # Admin permission fields
    role: Mapped[str] = mapped_column(String, default="standard_user")  # standard_user, power_user, developer, admin, super_admin
    permissions: Mapped[dict] = mapped_column(JSON, default=dict)  # Additional granular permissions
    
    # Plan and billing fields
    plan_tier: Mapped[str] = mapped_column(String, default="free")  # free, pro, enterprise, developer
    plan_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    plan_started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    feature_flags: Mapped[dict] = mapped_column(JSON, default=dict)  # Enabled feature flags
    tool_permissions: Mapped[dict] = mapped_column(JSON, default=dict)  # Per-tool permission overrides
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False)  # Auto-renewal enabled
    payment_status: Mapped[str] = mapped_column(String, default="active")  # active, suspended, cancelled
    trial_period: Mapped[int] = mapped_column(Integer, default=0)  # Trial period days (0 = not in trial)
    
    # Relationships
    secrets = relationship("Secret", back_populates="user", cascade="all, delete-orphan")
    credit_transactions = relationship("CreditTransaction", back_populates="user", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="user", cascade="all, delete-orphan")


class Secret(Base):
    __tablename__ = "secrets"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    key: Mapped[str] = mapped_column(String)
    encrypted_value: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), onupdate=func.now())
    
    user: Mapped["User"] = relationship("User", back_populates="secrets")


class ToolUsageLog(Base):
    __tablename__ = "tool_usage_logs"
    
    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    tool_name: Mapped[str] = mapped_column(String, index=True)
    category: Mapped[Optional[str]] = mapped_column(String, index=True)
    execution_time_ms: Mapped[int] = mapped_column(Integer, default=0)
    tokens_used: Mapped[Optional[int]] = mapped_column(Integer)
    cost_cents: Mapped[Optional[int]] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String, index=True)  # success, error, permission_denied, rate_limited
    plan_tier: Mapped[str] = mapped_column(String)  # User's plan at time of usage
    permission_check_result: Mapped[Optional[dict]] = mapped_column(JSON)  # Permission check details
    arguments: Mapped[Optional[dict]] = mapped_column(JSON)  # Tool arguments (for analytics)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now(), index=True)
    
    user: Mapped["User"] = relationship("User")