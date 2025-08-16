"""Circuit breaker monitoring helper utilities for decomposed operations."""

from typing import Dict, List, Any, Optional
from datetime import datetime, UTC, timedelta
from dataclasses import dataclass
from app.core.circuit_breaker import CircuitState
from app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


@dataclass
class CircuitBreakerEvent:
    """Circuit breaker state change event."""
    circuit_name: str
    old_state: str
    new_state: str
    timestamp: datetime
    failure_count: int
    success_rate: float
    metadata: Dict[str, Any]


@dataclass
class CircuitBreakerAlert:
    """Circuit breaker alert."""
    circuit_name: str
    severity: str
    message: str
    timestamp: datetime
    state: str
    metrics: Dict[str, Any]


def create_state_change_event(circuit_name: str, old_state: str, new_state: str, status: Dict[str, Any]) -> CircuitBreakerEvent:
    """Create a circuit breaker state change event."""
    return CircuitBreakerEvent(
        circuit_name=circuit_name,
        old_state=old_state,
        new_state=new_state,
        timestamp=datetime.now(UTC),
        failure_count=status.get("failure_count", 0),
        success_rate=status.get("success_rate", 0.0),
        metadata=status.get("metrics", {})
    )


def should_create_open_circuit_alert(new_state: str) -> bool:
    """Check if an alert should be created for circuit opening."""
    return new_state == CircuitState.OPEN.value


def create_circuit_alert(circuit_name: str, severity: str, message: str, state: str, metrics: Dict[str, Any]) -> CircuitBreakerAlert:
    """Create a circuit breaker alert."""
    return CircuitBreakerAlert(
        circuit_name=circuit_name,
        severity=severity,
        message=message,
        timestamp=datetime.now(UTC),
        state=state,
        metrics=metrics
    )


def should_alert_low_success_rate(state: str, success_rate: float, total_calls: int) -> bool:
    """Check if low success rate alert should be triggered."""
    is_closed = state == CircuitState.CLOSED.value
    low_success = success_rate < 0.5
    enough_calls = total_calls > 10
    return is_closed and low_success and enough_calls


def calculate_rejection_rate(rejected_calls: int, total_calls: int) -> float:
    """Calculate rejection rate from call metrics."""
    return rejected_calls / total_calls if total_calls > 0 else 0


def should_alert_high_rejection_rate(rejection_rate: float, rejected_calls: int) -> bool:
    """Check if high rejection rate alert should be triggered."""
    return rejection_rate > 0.1 and rejected_calls > 5


def extract_circuit_metrics(status: Dict[str, Any]) -> Dict[str, Any]:
    """Extract key metrics from circuit status."""
    metrics = status.get("metrics", {})
    return {
        "state": status.get("state", "unknown"),
        "success_rate": status.get("success_rate", 1.0),
        "failure_count": status.get("failure_count", 0),
        "total_calls": metrics.get("total_calls", 0),
        "rejected_calls": metrics.get("rejected_calls", 0),
        "timeouts": metrics.get("timeouts", 0)
    }


def build_health_summary_base() -> Dict[str, Any]:
    """Build base structure for health summary."""
    return {
        "total_circuits": 0,
        "healthy_circuits": 0,
        "degraded_circuits": 0,
        "unhealthy_circuits": 0,
        "recent_events": 0,
        "recent_alerts": 0
    }


def categorize_circuit_state(state: str) -> str:
    """Categorize circuit state into health category."""
    if state == CircuitState.CLOSED.value:
        return "healthy"
    elif state == CircuitState.HALF_OPEN.value:
        return "degraded"
    else:
        return "unhealthy"