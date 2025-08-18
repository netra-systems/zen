"""Response building utilities for route handlers."""

from typing import Dict, Any, Optional, List
from datetime import datetime, UTC


def build_basic_response(status: str, **kwargs) -> Dict[str, Any]:
    """Build basic response with status."""
    return {"status": status, **kwargs}


def build_timestamped_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """Add timestamp to response."""
    data["timestamp"] = datetime.now(UTC).isoformat()
    return data


def build_health_response(status: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Build health check response."""
    response = build_basic_response(status, **data)
    return build_timestamped_response(response)


def build_job_response(job_id: str, status: str, message: str) -> Dict[str, str]:
    """Build job creation response."""
    return {"job_id": job_id, "status": status, "message": message}


def build_circuit_response(name: str, status: Dict[str, Any]) -> Dict[str, Any]:
    """Build circuit breaker response."""
    return {
        "circuit_name": name,
        "status": status,
        "timestamp": datetime.now(UTC).isoformat()
    }


def _build_base_service_response(service: str, circuits: Dict[str, Any]) -> Dict[str, Any]:
    """Build base service response."""
    return {
        "service": service,
        "circuits": circuits,
        "overall_health": _assess_service_health(circuits),
        "timestamp": datetime.now(UTC).isoformat()
    }


def build_service_health_response(
    service: str, circuits: Dict[str, Any], health_checks: Optional[Dict] = None
) -> Dict[str, Any]:
    """Build service health response."""
    response = _build_base_service_response(service, circuits)
    if health_checks:
        response["health_checks"] = health_checks
    return response


def _extract_circuit_states(circuits: Dict[str, Dict[str, Any]]) -> List[str]:
    """Extract health states from circuits."""
    return [status.get("health", "unknown") for status in circuits.values()]


def _check_all_healthy(states: List[str]) -> bool:
    """Check if all states are healthy."""
    return all(state == "healthy" for state in states)


def _check_any_unhealthy(states: List[str]) -> bool:
    """Check if any states are unhealthy."""
    return any(state == "unhealthy" for state in states)


def _check_any_recovering(states: List[str]) -> bool:
    """Check if any states are recovering."""
    return any(state == "recovering" for state in states)


def _get_health_priority_order() -> List[tuple]:
    """Get health check priority order."""
    return [
        (_check_all_healthy, "healthy"),
        (_check_any_unhealthy, "unhealthy"),
        (_check_any_recovering, "recovering")
    ]


def _determine_overall_health(states: List[str]) -> str:
    """Determine overall health from states."""
    for check_func, status in _get_health_priority_order():
        if check_func(states):
            return status
    return "degraded"


def _assess_service_health(circuits: Dict[str, Dict[str, Any]]) -> str:
    """Assess overall health of service circuits."""
    if not circuits:
        return "unknown"
    states = _extract_circuit_states(circuits)
    return _determine_overall_health(states)