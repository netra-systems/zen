"""
Core Domain Models: Single Source of Truth for User, Message, and Thread Models

This module contains the fundamental domain models used across the Netra platform,
ensuring consistency and preventing duplication.

CRITICAL ARCHITECTURAL COMPLIANCE:
- All core model definitions MUST be imported from this module
- NO duplicate model definitions allowed anywhere else in codebase
- This file maintains strong typing and single sources of truth
- Maximum file size: 300 lines (currently under limit)

Usage:
    from netra_backend.app.schemas.core_models import User, Message, Thread
"""

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, ConfigDict, EmailStr, Field

# Import enums from the dedicated module
from netra_backend.app.schemas.core_enums import CircuitBreakerState, MessageType


class UserBase(BaseModel):
    """Base user model."""
    email: EmailStr
    full_name: Optional[str] = None
    picture: Optional[str] = None


class UserCreate(UserBase):
    """User creation model."""
    password: str


class UserCreateOAuth(UserBase):
    """OAuth user creation model."""
    pass


class User(BaseModel):
    """Unified User model - single source of truth."""
    id: str
    email: EmailStr
    full_name: Optional[str] = None
    picture: Optional[str] = None
    is_active: bool = True
    is_superuser: bool = False
    hashed_password: Optional[str] = None
    access_token: Optional[str] = None
    token_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True, extra="allow")


class MessageMetadata(BaseModel):
    """Unified message metadata."""
    model: Optional[str] = None
    tokens_used: Optional[int] = None
    processing_time: Optional[float] = None  
    agent_name: Optional[str] = None
    run_id: Optional[str] = None
    step_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    custom_fields: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class MessageCreate(BaseModel):
    """Message creation model for unified message storage."""
    content: str
    role: str = Field(default="user", description="Message role: user, assistant, system, tool")
    thread_id: str
    assistant_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        extra="forbid"
    )


class MessageResponse(BaseModel):
    """Message response model for unified message storage."""
    id: str
    content: str
    role: str
    thread_id: str
    created_at: datetime
    assistant_id: Optional[str] = None
    run_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        from_attributes=True
    )


class Message(BaseModel):
    """Unified Message model - single source of truth."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    content: str
    type: MessageType
    thread_id: Optional[str] = None
    sub_agent_name: Optional[str] = None
    tool_info: Optional[Dict[str, Any]] = None
    raw_data: Optional[Dict[str, Any]] = None
    displayed_to_user: bool = True
    metadata: Optional[MessageMetadata] = None
    references: Optional[List[str]] = None
    attachments: Optional[List[Dict[str, Any]]] = None
    
    model_config = ConfigDict(
    )


class ThreadMetadata(BaseModel):
    """Unified thread metadata."""
    tags: List[str] = Field(default_factory=list)
    priority: Optional[int] = Field(default=None, ge=0, le=10)
    category: Optional[str] = None
    user_id: Optional[str] = None
    custom_fields: Dict[str, Union[str, int, float, bool]] = Field(default_factory=dict)


class Thread(BaseModel):
    """Unified Thread model - single source of truth."""
    id: str
    name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    metadata: Optional[ThreadMetadata] = None
    message_count: int = 0
    is_active: bool = True
    last_message: Optional[Message] = None
    participants: Optional[List[str]] = None
    
    # Add fields for test compatibility
    user_id: Optional[str] = None
    deleted_at: Optional[datetime] = None
    
    model_config = ConfigDict(
        extra="allow"  # Allow additional fields for test flexibility
    )
    
    @property
    def title(self) -> Optional[str]:
        """Alias for name field for backward compatibility."""
        return self.name
    
    @title.setter  
    def title(self, value: Optional[str]) -> None:
        """Set name when title is assigned."""
        self.name = value


class Optimization(BaseModel):
    """Unified Optimization model - single source of truth."""
    id: str
    name: str
    config: Dict[str, Any] = Field(default_factory=dict)
    version: int = 1
    parent_id: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    
    model_config = ConfigDict(
        from_attributes=True
    )


@dataclass
class CircuitBreakerConfig:
    """Unified configuration for circuit breaker behavior - consolidates all variants."""
    # Basic circuit breaker settings
    failure_threshold: int = 5
    success_threshold: int = 3
    recovery_timeout: float = 60.0
    half_open_max_calls: int = 3
    
    # Advanced settings for adaptive behavior
    timeout_seconds: int = 60
    health_check_interval: int = 30
    slow_call_threshold: float = 5.0
    max_wait_duration: int = 300
    adaptive_threshold: bool = True
    
    # Identification
    name: str = "default"


@dataclass
class HealthCheckResult:
    """Result of a health check operation."""
    component_name: str
    success: bool
    health_score: float
    response_time_ms: float
    status: Optional[str] = None  # Using string to avoid enum dependency
    response_time: Optional[float] = None  # Legacy field for compatibility
    error_message: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Additional attributes expected by health service and routes
    message: Optional[str] = None
    labels: Dict[str, str] = field(default_factory=dict)
    last_check: Optional[datetime] = None


@dataclass
class ReliabilityMetrics:
    """Metrics for reliability monitoring - consolidated from all variants."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    circuit_breaker_opens: int = 0
    recovery_attempts: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    error_types: Dict[str, int] = field(default_factory=dict)


# Export all core models
__all__ = [
    "UserBase",
    "UserCreate", 
    "UserCreateOAuth",
    "User",
    "MessageMetadata",
    "Message",
    "ThreadMetadata", 
    "Thread",
    "CircuitBreakerConfig",
    "HealthCheckResult",
    "ReliabilityMetrics"
]