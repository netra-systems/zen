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


def build_service_health_response(
    service: str, circuits: Dict[str, Any], health_checks: Optional[Dict] = None
) -> Dict[str, Any]:
    """Build service health response."""
    response = {
        "service": service,
        "circuits": circuits,
        "overall_health": _assess_service_health(circuits),
        "timestamp": datetime.now(UTC).isoformat()
    }
    if health_checks:
        response["health_checks"] = health_checks
    return response


def _assess_service_health(circuits: Dict[str, Dict[str, Any]]) -> str:
    """Assess overall health of service circuits."""
    if not circuits:
        return "unknown"
    states = [status.get("health", "unknown") for status in circuits.values()]
    if all(state == "healthy" for state in states):
        return "healthy"
    elif any(state == "unhealthy" for state in states):
        return "unhealthy"
    elif any(state == "recovering" for state in states):
        return "recovering"
    else:
        return "degraded"