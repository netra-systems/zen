"""Service delegation utilities for route handlers."""

from typing import Dict, Any, List, Optional
from netra_backend.app.core.error_handlers import handle_service_error, handle_circuit_breaker_error
from netra_backend.app.services.circuit_breaker_monitor import circuit_monitor, metrics_collector


async def delegate_circuit_dashboard() -> Dict[str, Any]:
    """Delegate circuit breaker dashboard request."""
    try:
        from netra_backend.app.services.circuit_breaker_monitor import get_circuit_health_dashboard
        return await get_circuit_health_dashboard()
    except Exception as e:
        handle_circuit_breaker_error(e, "dashboard")


async def delegate_circuit_status() -> Dict[str, Dict[str, Any]]:
    """Delegate circuit status request."""
    try:
        from netra_backend.app.core.circuit_breaker import circuit_registry
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


def _format_event_basic_fields(event) -> Dict[str, Any]:
    """Format basic event fields."""
    return {
        "circuit_name": event.circuit_name,
        "old_state": event.old_state,
        "new_state": event.new_state,
        "timestamp": event.timestamp.isoformat()
    }


def _format_event_metric_fields(event) -> Dict[str, Any]:
    """Format event metric fields."""
    return {
        "failure_count": event.failure_count,
        "success_rate": event.success_rate,
        "metadata": event.metadata
    }


def _format_single_event(event) -> Dict[str, Any]:
    """Format single event for response."""
    basic_fields = _format_event_basic_fields(event)
    metric_fields = _format_event_metric_fields(event)
    return {**basic_fields, **metric_fields}


def _format_events_list(events) -> List[Dict[str, Any]]:
    """Format events list for response."""
    return [_format_single_event(event) for event in events]


def _format_alert_basic_info(alert) -> Dict[str, Any]:
    """Format alert basic information."""
    return {
        "circuit_name": alert.circuit_name,
        "severity": alert.severity.value,
        "message": alert.message,
        "timestamp": alert.timestamp.isoformat()
    }


def _format_alert_status_info(alert) -> Dict[str, Any]:
    """Format alert status information."""
    return {
        "state": alert.state,
        "metrics": alert.metrics
    }


def _format_single_alert(alert) -> Dict[str, Any]:
    """Format single alert for response."""
    basic_info = _format_alert_basic_info(alert)
    status_info = _format_alert_status_info(alert)
    return {**basic_info, **status_info}


def _format_alerts_list(alerts) -> List[Dict[str, Any]]:
    """Format alerts list for response."""
    return [_format_single_alert(alert) for alert in alerts]


def _format_metrics_timing_info(metrics) -> Dict[str, Any]:
    """Format metrics timing information."""
    return {
        "timestamp": metrics["timestamp"].isoformat(),
        "state": metrics["state"]
    }


def _format_metrics_performance_info(metrics) -> Dict[str, Any]:
    """Format metrics performance information."""
    return {
        "success_rate": metrics["success_rate"],
        "total_calls": metrics["total_calls"],
        "rejected_calls": metrics["rejected_calls"],
        "timeouts": metrics["timeouts"]
    }


def _format_single_metrics_entry(metrics) -> Dict[str, Any]:
    """Format single metrics entry for response."""
    timing_info = _format_metrics_timing_info(metrics)
    performance_info = _format_metrics_performance_info(metrics)
    return {**timing_info, **performance_info}


def _format_metrics_history(history) -> List[Dict[str, Any]]:
    """Format metrics history for response."""
    return [_format_single_metrics_entry(metrics) for metrics in history]