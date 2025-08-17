"""Types and data structures for graceful degradation system.

This module contains all the basic types, enums, and data classes
used throughout the graceful degradation system.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict


class DegradationLevel(Enum):
    """Levels of service degradation."""
    NORMAL = "normal"
    REDUCED = "reduced"
    MINIMAL = "minimal"
    EMERGENCY = "emergency"


class ServiceTier(Enum):
    """Service tier priorities."""
    CRITICAL = "critical"    # Must maintain
    IMPORTANT = "important"  # Degrade if necessary
    OPTIONAL = "optional"    # Can disable
    AUXILIARY = "auxiliary"  # First to disable


@dataclass
class DegradationPolicy:
    """Policy for degrading a service."""
    service_name: str
    tier: ServiceTier
    degradation_levels: Dict[DegradationLevel, Callable]
    recovery_threshold: float = 0.8
    timeout_seconds: int = 300


@dataclass
class ServiceStatus:
    """Status of a service component."""
    name: str
    is_healthy: bool
    degradation_level: DegradationLevel
    last_check: datetime
    error_count: int = 0
    response_time: float = 0.0


class DegradationStrategy(ABC):
    """Abstract base for degradation strategies."""
    
    @abstractmethod
    async def degrade_to_level(
        self,
        level: DegradationLevel,
        context: Dict[str, Any]
    ) -> Any:
        """Degrade service to specified level."""
        pass
    
    @abstractmethod
    async def can_restore_service(self) -> bool:
        """Check if service can be restored to normal."""
        pass