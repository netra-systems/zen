"""Service delegation utilities for route handlers."""

from typing import Dict, Any, List, Optional
from .error_handlers import handle_service_error, handle_circuit_breaker_error
from app.services.circuit_breaker_monitor import circuit_monitor, metrics_collector


async def delegate_circuit_dashboard() -> Dict[str, Any]:
    """Delegate circuit breaker dashboard request."""
    try:
        from app.services.circuit_breaker_monitor import get_circuit_health_dashboard
        return await get_circuit_health_dashboard()
    except Exception as e:
        handle_circuit_breaker_error(e, "dashboard")


async def delegate_circuit_status() -> Dict[str, Dict[str, Any]]:
    """Delegate circuit status request."""
    try:
        from app.core.circuit_breaker import circuit_registry
        return await circuit_registry.get_all_status()
    except Exception as e:
        handle_circuit_breaker_error(e, "status")


def delegate_recent_events(limit: int) -> List[Dict[str, Any]]:
    """Delegate recent events request."""
    try:
        events = circuit_monitor.get_recent_events(limit)
        return _format_events_list(events)
    except Exception as e:
        handle_circuit_breaker_error(e, "events")


def delegate_recent_alerts(limit: int) -> List[Dict[str, Any]]:
    """Delegate recent alerts request."""
    try:
        alerts = circuit_monitor.get_recent_alerts(limit)
        return _format_alerts_list(alerts)
    except Exception as e:
        handle_circuit_breaker_error(e, "alerts")


def delegate_circuit_metrics(hours: int) -> Dict[str, Dict[str, Any]]:
    """Delegate circuit metrics request."""
    try:
        return metrics_collector.get_aggregated_metrics(hours)
    except Exception as e:
        handle_circuit_breaker_error(e, "metrics")


def delegate_metrics_history(circuit_name: str, hours: int) -> List[Dict[str, Any]]:
    """Delegate metrics history request."""
    try:
        history = metrics_collector.get_metrics_history(circuit_name, hours)
        return _format_metrics_history(history)
    except Exception as e:
        handle_circuit_breaker_error(e, "metrics history")


def _format_single_event(event) -> Dict[str, Any]:
    """Format single event for response."""
    return {
        "circuit_name": event.circuit_name,
        "old_state": event.old_state,
        "new_state": event.new_state,
        "timestamp": event.timestamp.isoformat(),
        "failure_count": event.failure_count,
        "success_rate": event.success_rate,
        "metadata": event.metadata
    }


def _format_events_list(events) -> List[Dict[str, Any]]:
    """Format events list for response."""
    return [_format_single_event(event) for event in events]


def _format_alerts_list(alerts) -> List[Dict[str, Any]]:
    """Format alerts list for response."""
    return [
        {
            "circuit_name": alert.circuit_name,
            "severity": alert.severity.value,
            "message": alert.message,
            "timestamp": alert.timestamp.isoformat(),
            "state": alert.state,
            "metrics": alert.metrics
        }
        for alert in alerts
    ]


def _format_metrics_history(history) -> List[Dict[str, Any]]:
    """Format metrics history for response."""
    return [
        {
            "timestamp": metrics["timestamp"].isoformat(),
            "state": metrics["state"],
            "success_rate": metrics["success_rate"],
            "total_calls": metrics["total_calls"],
            "rejected_calls": metrics["rejected_calls"],
            "timeouts": metrics["timeouts"]
        }
        for metrics in history
    ]