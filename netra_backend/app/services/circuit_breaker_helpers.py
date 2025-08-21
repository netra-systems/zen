"""Circuit breaker monitoring helper utilities for decomposed operations."""

from typing import Dict, List, Any, Optional
from datetime import datetime, UTC, timedelta
from dataclasses import dataclass
from netra_backend.app.core.circuit_breaker import CircuitState
from netra_backend.app.logging_config import central_logger

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


def populate_health_summary(summary: Dict[str, Any], last_states: Dict[str, str], recent_events_count: int, recent_alerts_count: int) -> None:
    """Populate health summary with circuit states and counts."""
    summary["total_circuits"] = len(last_states)
    summary["recent_events"] = recent_events_count
    summary["recent_alerts"] = recent_alerts_count
    
    for state in last_states.values():
        category = categorize_circuit_state(state)
        summary[f"{category}_circuits"] += 1


def calculate_aggregated_totals(history: List[Dict[str, Any]]) -> tuple[int, List[float]]:
    """Calculate total calls and success rates from history."""
    total_calls = sum(m.get("total_calls", 0) for m in history)
    success_rates = [m.get("success_rate", 0.0) for m in history if m.get("total_calls", 0) > 0]
    return total_calls, success_rates


def build_aggregated_metrics(total_calls: int, success_rates: List[float], history: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build aggregated metrics dictionary from totals and history."""
    return {
        "avg_success_rate": sum(success_rates) / len(success_rates) if success_rates else 0.0,
        "total_calls": total_calls,
        "total_rejections": sum(m.get("rejected_calls", 0) for m in history),
        "total_timeouts": sum(m.get("timeouts", 0) for m in history),
        "state_changes": len(set(m.get("state", "unknown") for m in history)) - 1
    }


def build_event_data(events) -> List[Dict[str, Any]]:
    """Build event data list from circuit breaker events."""
    return [
        {
            "circuit": event.circuit_name,
            "transition": f"{event.old_state} -> {event.new_state}",
            "timestamp": event.timestamp.isoformat(),
            "success_rate": event.success_rate
        }
        for event in events
    ]


def build_alert_data(alerts) -> List[Dict[str, Any]]:
    """Build alert data list from circuit breaker alerts."""
    return [
        {
            "circuit": alert.circuit_name,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat()
        }
        for alert in alerts
    ]


def filter_metrics_by_time(metrics_history: List[Dict[str, Any]], cutoff_time: datetime) -> List[Dict[str, Any]]:
    """Filter metrics history by cutoff time."""
    return [m for m in metrics_history if m["timestamp"] >= cutoff_time]


def extract_metrics_from_status(status: Dict[str, Any], timestamp: datetime) -> Dict[str, Any]:
    """Extract metrics from circuit status with timestamp."""
    metrics = status.get("metrics", {})
    return {
        "timestamp": timestamp,
        "state": status.get("state", "unknown"),
        "success_rate": status.get("success_rate", 0.0),
        "failure_count": status.get("failure_count", 0),
        "total_calls": metrics.get("total_calls", 0),
        "rejected_calls": metrics.get("rejected_calls", 0),
        "timeouts": metrics.get("timeouts", 0)
    }


def initialize_circuit_history(metrics_history: Dict, circuit_name: str) -> None:
    """Initialize circuit history if it doesn't exist."""
    if circuit_name not in metrics_history:
        metrics_history[circuit_name] = []


def trim_metrics_history(metrics_list: List[Dict[str, Any]], max_entries: int = 1000) -> List[Dict[str, Any]]:
    """Trim metrics history to maximum entries."""
    if len(metrics_list) > max_entries:
        return metrics_list[-max_entries:]
    return metrics_list