"""CircuitBreaker - Failure detection and recovery system for agents.

This module implements the circuit breaker pattern to detect repeated failures,
temporarily disable failing agents, and provide automatic recovery with fallback options.

Business Value: Prevents cascading failures, improves system resilience, and provides
graceful degradation when agents are experiencing issues.
"""

import asyncio
import time
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from dataclasses import dataclass, field

from pydantic import BaseModel

from netra_backend.app.logging_config import central_logger
from shared.isolated_environment import IsolatedEnvironment

logger = central_logger.get_logger(__name__)


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Circuit is open (blocking requests)
    HALF_OPEN = "half_open"  # Testing if service has recovered


class FailureType(Enum):
    """Types of failures that can trigger circuit breaker."""
    TIMEOUT = "timeout"
    EXCEPTION = "exception"
    SILENT_FAILURE = "silent_failure"
    MEMORY_ERROR = "memory_error"
    RATE_LIMIT = "rate_limit"


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 3  # Number of failures to trigger open state
    recovery_timeout: int = 60  # Seconds to wait before attempting recovery
    success_threshold: int = 2   # Successful calls needed to close circuit
    failure_window_seconds: int = 300  # Window for counting failures (5 minutes)
    max_half_open_calls: int = 3  # Max calls allowed in half-open state


@dataclass
class FailureRecord:
    """Record of a failure."""
    timestamp: datetime
    failure_type: FailureType
    error_message: str
    agent_name: str
    user_id: Optional[str] = None
    context: Optional[Dict[str, Any]] = None


class CircuitBreakerMetrics(BaseModel):
    """Circuit breaker metrics."""
    agent_name: str
    state: CircuitState
    failure_count: int
    success_count: int
    last_failure_time: Optional[datetime]
    last_success_time: Optional[datetime]
    opened_at: Optional[datetime]
    recovery_attempts: int
    total_requests: int
    blocked_requests: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AgentCircuitBreaker:
    """Circuit breaker for individual agents."""
    
    def __init__(self, agent_name: str, config: CircuitBreakerConfig):
        self.agent_name = agent_name
        self.config = config
        self.state = CircuitState.CLOSED
        
        # Failure tracking
        self.failure_records: List[FailureRecord] = []
        self.success_count = 0
        self.total_requests = 0
        self.blocked_requests = 0
        
        # State management
        self.opened_at: Optional[datetime] = None
        self.last_failure_time: Optional[datetime] = None
        self.last_success_time: Optional[datetime] = None
        self.recovery_attempts = 0
        self.half_open_calls = 0
        
        logger.info(f"[U+1F50C] Circuit breaker initialized for {agent_name}")
    
    def can_execute(self) -> bool:
        """Check if agent can execute based on circuit state."""
        self.total_requests += 1
        
        if self.state == CircuitState.CLOSED:
            return True
        
        elif self.state == CircuitState.OPEN:
            # Check if recovery timeout has passed
            if self.opened_at and datetime.now(UTC) - self.opened_at > timedelta(seconds=self.config.recovery_timeout):
                self._transition_to_half_open()
                return self.half_open_calls < self.config.max_half_open_calls
            else:
                self.blocked_requests += 1
                return False
        
        elif self.state == CircuitState.HALF_OPEN:
            if self.half_open_calls < self.config.max_half_open_calls:
                self.half_open_calls += 1
                return True
            else:
                self.blocked_requests += 1
                return False
        
        return False
    
    def record_success(self) -> None:
        """Record a successful execution."""
        self.success_count += 1
        self.last_success_time = datetime.now(UTC)
        
        if self.state == CircuitState.HALF_OPEN:
            if self.success_count >= self.config.success_threshold:
                self._transition_to_closed()
                logger.info(f" PASS:  Circuit breaker CLOSED for {self.agent_name} after {self.success_count} successes")
        
        # Clean up old failure records
        self._cleanup_old_failures()
    
    def record_failure(self, failure_type: FailureType, error_message: str, user_id: Optional[str] = None, context: Optional[Dict[str, Any]] = None) -> None:
        """Record a failure and potentially trip the circuit."""
        failure_record = FailureRecord(
            timestamp=datetime.now(UTC),
            failure_type=failure_type,
            error_message=error_message,
            agent_name=self.agent_name,
            user_id=user_id,
            context=context
        )
        
        self.failure_records.append(failure_record)
        self.last_failure_time = failure_record.timestamp
        
        # Clean up old failures
        self._cleanup_old_failures()
        
        # Count recent failures
        recent_failures = len(self.failure_records)
        
        logger.warning(f" WARNING: [U+FE0F] Failure recorded for {self.agent_name}: {failure_type.value} - {error_message} (recent failures: {recent_failures})")
        
        # Check if we should trip the circuit
        if self.state == CircuitState.CLOSED and recent_failures >= self.config.failure_threshold:
            self._transition_to_open()
            logger.error(f"[U+1F534] Circuit breaker OPENED for {self.agent_name} after {recent_failures} failures")
        
        elif self.state == CircuitState.HALF_OPEN:
            # Any failure in half-open state reopens the circuit
            self._transition_to_open()
            logger.error(f"[U+1F534] Circuit breaker RE-OPENED for {self.agent_name} during recovery attempt")
    
    def _cleanup_old_failures(self) -> None:
        """Remove failures outside the failure window."""
        cutoff_time = datetime.now(UTC) - timedelta(seconds=self.config.failure_window_seconds)
        self.failure_records = [f for f in self.failure_records if f.timestamp > cutoff_time]
    
    def _transition_to_open(self) -> None:
        """Transition to open state."""
        self.state = CircuitState.OPEN
        self.opened_at = datetime.now(UTC)
        self.success_count = 0
        self.half_open_calls = 0
    
    def _transition_to_half_open(self) -> None:
        """Transition to half-open state."""
        self.state = CircuitState.HALF_OPEN
        self.recovery_attempts += 1
        self.half_open_calls = 0
        self.success_count = 0
        logger.info(f"[U+1F7E1] Circuit breaker HALF-OPEN for {self.agent_name} (recovery attempt #{self.recovery_attempts})")
    
    def _transition_to_closed(self) -> None:
        """Transition to closed state."""
        self.state = CircuitState.CLOSED
        self.opened_at = None
        self.half_open_calls = 0
        self.failure_records.clear()  # Reset failure history
    
    def get_metrics(self) -> CircuitBreakerMetrics:
        """Get current metrics for this circuit breaker."""
        return CircuitBreakerMetrics(
            agent_name=self.agent_name,
            state=self.state,
            failure_count=len(self.failure_records),
            success_count=self.success_count,
            last_failure_time=self.last_failure_time,
            last_success_time=self.last_success_time,
            opened_at=self.opened_at,
            recovery_attempts=self.recovery_attempts,
            total_requests=self.total_requests,
            blocked_requests=self.blocked_requests
        )
    
    def force_reset(self) -> None:
        """Force reset the circuit breaker (emergency recovery)."""
        logger.warning(f"[U+1F527] Force resetting circuit breaker for {self.agent_name}")
        self.state = CircuitState.CLOSED
        self.failure_records.clear()
        self.opened_at = None
        self.half_open_calls = 0
        self.success_count = 0
        self.recovery_attempts = 0


class SystemCircuitBreaker:
    """Global circuit breaker management system."""
    
    def __init__(self, default_config: Optional[CircuitBreakerConfig] = None):
        """Initialize system circuit breaker."""
        self.env = IsolatedEnvironment()
        
        # Load default configuration
        self.default_config = default_config or CircuitBreakerConfig(
            failure_threshold=int(self.env.get('CIRCUIT_BREAKER_FAILURE_THRESHOLD', '3')),
            recovery_timeout=int(self.env.get('CIRCUIT_BREAKER_RECOVERY_TIMEOUT', '60')),
            success_threshold=int(self.env.get('CIRCUIT_BREAKER_SUCCESS_THRESHOLD', '2')),
            failure_window_seconds=int(self.env.get('CIRCUIT_BREAKER_FAILURE_WINDOW', '300')),
            max_half_open_calls=int(self.env.get('CIRCUIT_BREAKER_MAX_HALF_OPEN', '3'))
        )
        
        # Agent circuit breakers
        self.agent_breakers: Dict[str, AgentCircuitBreaker] = {}
        
        # Fallback agents (simpler agents to use when primary agents fail)
        self.fallback_agents: Dict[str, str] = {
            "data": "triage",  # Use triage agent if data agent fails
            "optimization": "data",  # Use data agent if optimization fails
            "reporting": "triage",  # Use triage if reporting fails
            "actions": "triage",  # Use triage if actions fail
        }
        
        # Global failure tracking
        self.global_failure_count = 0
        self.system_degraded = False
        
        logger.info(f"[U+1F50C] System circuit breaker initialized with default config: {self.default_config}")
    
    def get_or_create_breaker(self, agent_name: str, config: Optional[CircuitBreakerConfig] = None) -> AgentCircuitBreaker:
        """Get or create circuit breaker for an agent."""
        if agent_name not in self.agent_breakers:
            breaker_config = config or self.default_config
            self.agent_breakers[agent_name] = AgentCircuitBreaker(agent_name, breaker_config)
        
        return self.agent_breakers[agent_name]
    
    async def can_execute_agent(self, agent_name: str) -> tuple[bool, Optional[str]]:
        """Check if agent can execute and get fallback if needed.
        
        Returns:
            (can_execute, fallback_agent_name)
        """
        breaker = self.get_or_create_breaker(agent_name)
        
        if breaker.can_execute():
            return True, None
        
        # Check for fallback agent
        fallback_agent = self.fallback_agents.get(agent_name)
        if fallback_agent:
            fallback_breaker = self.get_or_create_breaker(fallback_agent)
            if fallback_breaker.can_execute():
                logger.info(f" CYCLE:  Using fallback agent {fallback_agent} for failed {agent_name}")
                return True, fallback_agent
        
        logger.error(f"[U+1F6AB] No available agents for {agent_name} (circuit open, no fallback)")
        return False, None
    
    async def record_execution_result(
        self,
        agent_name: str,
        success: bool,
        failure_type: Optional[FailureType] = None,
        error_message: str = "",
        user_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record the result of an agent execution."""
        breaker = self.get_or_create_breaker(agent_name)
        
        if success:
            breaker.record_success()
            logger.debug(f" PASS:  Success recorded for {agent_name}")
        else:
            breaker.record_failure(failure_type or FailureType.EXCEPTION, error_message, user_id, context)
            self.global_failure_count += 1
            
            # Check if system should be marked as degraded
            open_breakers = sum(1 for b in self.agent_breakers.values() if b.state == CircuitState.OPEN)
            if open_breakers >= len(self.agent_breakers) * 0.5:  # 50% of agents failing
                self.system_degraded = True
                logger.critical(f" ALERT:  SYSTEM DEGRADED: {open_breakers}/{len(self.agent_breakers)} agents have circuit breakers open")
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system circuit breaker status."""
        agent_statuses = {}
        
        for agent_name, breaker in self.agent_breakers.items():
            metrics = breaker.get_metrics()
            agent_statuses[agent_name] = {
                "state": metrics.state.value,
                "failure_count": metrics.failure_count,
                "success_count": metrics.success_count,
                "total_requests": metrics.total_requests,
                "blocked_requests": metrics.blocked_requests,
                "last_failure": metrics.last_failure_time.isoformat() if metrics.last_failure_time else None,
                "recovery_attempts": metrics.recovery_attempts,
                "can_execute": breaker.can_execute()
            }
        
        # Calculate system health
        total_agents = len(self.agent_breakers)
        open_breakers = sum(1 for b in self.agent_breakers.values() if b.state == CircuitState.OPEN)
        degraded_breakers = sum(1 for b in self.agent_breakers.values() if b.state == CircuitState.HALF_OPEN)
        
        system_health = "healthy"
        if open_breakers > 0:
            if open_breakers >= total_agents * 0.5:
                system_health = "critical"
            elif open_breakers >= total_agents * 0.25:
                system_health = "degraded"
            else:
                system_health = "warning"
        
        return {
            "system_health": system_health,
            "system_degraded": self.system_degraded,
            "global_failure_count": self.global_failure_count,
            "agent_summary": {
                "total_agents": total_agents,
                "healthy_agents": total_agents - open_breakers - degraded_breakers,
                "degraded_agents": degraded_breakers,
                "failed_agents": open_breakers
            },
            "agents": agent_statuses,
            "fallback_chains": self.fallback_agents,
            "timestamp": datetime.now(UTC).isoformat()
        }
    
    async def get_failure_analysis(self) -> Dict[str, Any]:
        """Get detailed failure analysis across all agents."""
        all_failures = []
        
        for breaker in self.agent_breakers.values():
            for failure in breaker.failure_records:
                all_failures.append({
                    "agent_name": failure.agent_name,
                    "timestamp": failure.timestamp.isoformat(),
                    "failure_type": failure.failure_type.value,
                    "error_message": failure.error_message,
                    "user_id": failure.user_id,
                    "context": failure.context
                })
        
        # Sort by timestamp (most recent first)
        all_failures.sort(key=lambda x: x["timestamp"], reverse=True)
        
        # Analyze failure patterns
        failure_by_type = {}
        failure_by_agent = {}
        
        for failure in all_failures:
            failure_type = failure["failure_type"]
            agent_name = failure["agent_name"]
            
            failure_by_type[failure_type] = failure_by_type.get(failure_type, 0) + 1
            failure_by_agent[agent_name] = failure_by_agent.get(agent_name, 0) + 1
        
        return {
            "total_recent_failures": len(all_failures),
            "failure_by_type": failure_by_type,
            "failure_by_agent": failure_by_agent,
            "recent_failures": all_failures[:20],  # Last 20 failures
            "analysis_window_seconds": self.default_config.failure_window_seconds
        }
    
    async def force_reset_agent(self, agent_name: str) -> bool:
        """Force reset a specific agent's circuit breaker."""
        if agent_name in self.agent_breakers:
            self.agent_breakers[agent_name].force_reset()
            logger.info(f"[U+1F527] Force reset circuit breaker for {agent_name}")
            return True
        return False
    
    async def force_reset_all_agents(self) -> int:
        """Emergency reset of all circuit breakers."""
        logger.critical("[U+1F527] EMERGENCY RESET: Resetting all circuit breakers")
        
        reset_count = 0
        for breaker in self.agent_breakers.values():
            breaker.force_reset()
            reset_count += 1
        
        self.system_degraded = False
        self.global_failure_count = 0
        
        logger.critical(f"[U+1F527] Emergency reset completed: {reset_count} circuit breakers reset")
        return reset_count
    
    async def add_fallback_agent(self, primary_agent: str, fallback_agent: str) -> None:
        """Add or update a fallback agent mapping."""
        self.fallback_agents[primary_agent] = fallback_agent
        logger.info(f" CYCLE:  Added fallback mapping: {primary_agent} -> {fallback_agent}")
    
    async def remove_fallback_agent(self, primary_agent: str) -> bool:
        """Remove a fallback agent mapping."""
        if primary_agent in self.fallback_agents:
            del self.fallback_agents[primary_agent]
            logger.info(f" CYCLE:  Removed fallback mapping for {primary_agent}")
            return True
        return False
    
    async def test_agent_recovery(self, agent_name: str) -> Dict[str, Any]:
        """Test if an agent has recovered from failures."""
        if agent_name not in self.agent_breakers:
            return {"error": f"No circuit breaker found for {agent_name}"}
        
        breaker = self.agent_breakers[agent_name]
        
        if breaker.state == CircuitState.OPEN:
            # Force transition to half-open for testing
            breaker._transition_to_half_open()
            
            return {
                "agent_name": agent_name,
                "action": "forced_half_open",
                "state": breaker.state.value,
                "test_calls_allowed": breaker.config.max_half_open_calls,
                "message": f"Circuit forced to half-open for recovery testing. Up to {breaker.config.max_half_open_calls} test calls allowed."
            }
        
        return {
            "agent_name": agent_name,
            "state": breaker.state.value,
            "message": f"Circuit is already {breaker.state.value}. No recovery testing needed."
        }
    
    def get_recommended_agent(self, requested_agent: str) -> str:
        """Get the best available agent for a request (including fallbacks)."""
        can_execute, fallback = asyncio.run(self.can_execute_agent(requested_agent))
        
        if can_execute:
            return fallback if fallback else requested_agent
        
        # If no fallback available, return a basic fallback
        return "triage"  # Always fallback to triage as last resort


# DEPRECATED: Create global instances with deprecation warnings
def create_system_circuit_breaker() -> SystemCircuitBreaker:
    """DEPRECATED: Create system circuit breaker. Use UnifiedCircuitBreakerManager instead."""
    warnings.warn(
        "create_system_circuit_breaker() is deprecated. "
        "Use get_unified_circuit_breaker_manager() directly for new code.",
        DeprecationWarning,
        stacklevel=2
    )
    return SystemCircuitBreaker()


# DEPRECATED: Global instances for backward compatibility
_system_circuit_breaker: Optional[SystemCircuitBreaker] = None


def get_system_circuit_breaker() -> SystemCircuitBreaker:
    """DEPRECATED: Get global system circuit breaker. Use UnifiedCircuitBreakerManager instead."""
    warnings.warn(
        "get_system_circuit_breaker() is deprecated. "
        "Use get_unified_circuit_breaker_manager() directly for new code.",
        DeprecationWarning,
        stacklevel=2
    )
    global _system_circuit_breaker
    if _system_circuit_breaker is None:
        _system_circuit_breaker = SystemCircuitBreaker()
    return _system_circuit_breaker