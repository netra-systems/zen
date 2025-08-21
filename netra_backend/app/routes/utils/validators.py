"""Validation utilities for route handlers."""

from typing import Dict, Any, Optional
from netra_backend.app.error_handlers import handle_not_found_error, handle_access_denied_error


def validate_resource_exists(resource: Any, resource_type: str, identifier: str) -> None:
    """Validate resource exists."""
    if not resource:
        handle_not_found_error(resource_type, identifier)


def validate_user_access(resource: Dict[str, Any], user_id: int, resource_id: str) -> None:
    """Validate user access to resource."""
    if resource.get("user_id") != user_id:
        handle_access_denied_error()


def validate_job_ownership(status: Dict, user_id: int, job_id: str) -> None:
    """Validate job ownership and access."""
    validate_resource_exists(status, "Job", job_id)
    validate_user_access(status, user_id, job_id)


def validate_circuit_exists(all_status: Dict, circuit_name: str) -> str:
    """Validate circuit exists and return matched name."""
    for name, status in all_status.items():
        if name == circuit_name or circuit_name in name:
            return name
    handle_not_found_error("Circuit breaker", circuit_name)


def validate_token_payload(payload: Optional[Dict]) -> Dict:
    """Validate token payload exists."""
    if payload is None:
        raise ValueError("Invalid token")
    return payload


def validate_user_id_in_payload(payload: Dict) -> str:
    """Validate and extract user ID from payload."""
    user_id = payload.get("sub")
    if user_id is None:
        raise ValueError("Invalid token")
    return user_id


def validate_user_active(user: Any) -> str:
    """Validate user is active and return ID string."""
    if user is None:
        raise ValueError("User not found")
    if not user.is_active:
        raise ValueError("User not active")
    return str(user.id)