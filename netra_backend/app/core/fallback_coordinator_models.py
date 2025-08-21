"""
Models and data structures for fallback coordination.
"""

from typing import Optional, List
from enum import Enum
from dataclasses import dataclass
from datetime import datetime


class SystemHealthLevel(Enum):
    """System-wide health levels"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    CRITICAL = "critical"
    EMERGENCY = "emergency"


@dataclass
class AgentFallbackStatus:
    """Status of fallback mechanisms for an agent"""
    agent_name: str
    circuit_breaker_open: bool
    recent_failures: int
    fallback_active: bool
    last_failure_time: Optional[datetime]
    health_score: float


@dataclass
class SystemFallbackStatus:
    """Overall system fallback status"""
    health_level: SystemHealthLevel
    agents_in_fallback: List[str]
    total_agents: int
    cascade_prevention_active: bool
    emergency_mode_active: bool
    last_health_check: datetime