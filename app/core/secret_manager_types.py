"""
Secret manager types and enums.
Defines basic types used across the secret management system.
"""

from enum import Enum
from typing import Set
from datetime import datetime, timezone

from app.schemas.config_types import EnvironmentType


class SecretAccessLevel(str, Enum):
    """Secret access levels for permission control."""
    PUBLIC = "public"          # Non-sensitive configuration
    INTERNAL = "internal"      # Internal app secrets  
    RESTRICTED = "restricted"  # Database passwords, API keys
    CRITICAL = "critical"      # Production secrets, encryption keys


class SecretMetadata:
    """Metadata for secret tracking and rotation."""
    
    def __init__(self, secret_name: str, access_level: SecretAccessLevel,
                 environment: EnvironmentType, rotation_days: int = 90):
        self.secret_name = secret_name
        self.access_level = access_level
        self.environment = environment
        self.created_at = datetime.now(timezone.utc)
        self.last_accessed = datetime.now(timezone.utc)
        self.last_rotated = datetime.now(timezone.utc)
        self.rotation_days = rotation_days
        self.access_count = 0
        self.authorized_components: Set[str] = set()
    
    @property
    def needs_rotation(self) -> bool:
        """Check if secret needs rotation."""
        return self._days_since_rotation() >= self.rotation_days
    
    @property
    def is_expired(self) -> bool:
        """Check if secret is expired (past rotation deadline)."""
        return self._days_since_rotation() > (self.rotation_days + 30)  # 30 day grace period
    
    def record_access(self, component: str) -> None:
        """Record secret access."""
        self._update_access_time()
        self._increment_access_count()
        self._add_authorized_component(component)
    
    def _days_since_rotation(self) -> int:
        """Calculate days since last rotation."""
        return (datetime.now(timezone.utc) - self.last_rotated).days
    
    def _update_access_time(self) -> None:
        """Update last accessed timestamp."""
        self.last_accessed = datetime.now(timezone.utc)
    
    def _increment_access_count(self) -> None:
        """Increment access counter."""
        self.access_count += 1
    
    def _add_authorized_component(self, component: str) -> None:
        """Add component to authorized list."""
        self.authorized_components.add(component)