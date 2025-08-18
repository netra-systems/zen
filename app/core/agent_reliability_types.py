"""Agent reliability type definitions.

This module provides data classes and type definitions for agent reliability features.
"""

from typing import Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field

from .error_codes import ErrorSeverity


@dataclass
class AgentError:
    """Represents an error that occurred during agent execution."""
    error_id: str
    agent_name: str
    operation: str
    error_type: str
    message: str
    timestamp: datetime
    severity: ErrorSeverity
    context: Dict[str, Any] = field(default_factory=dict)
    recovery_attempted: bool = False
    recovery_successful: bool = False


@dataclass
class AgentHealthStatus:
    """Comprehensive health status for an agent."""
    agent_name: str
    overall_health: float  # 0.0 to 1.0
    circuit_breaker_state: str
    recent_errors: int
    total_operations: int
    success_rate: float
    average_response_time: float
    last_error: Optional[AgentError] = None
    status: str = "healthy"  # healthy, degraded, unhealthy