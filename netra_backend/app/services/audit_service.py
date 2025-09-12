"""
General Audit Service
Provides system-wide audit logging and retrieval functionality.
Follows modular design -  <= 300 lines,  <= 8 lines per function.
Implements "Default to Resilience" with flexible parameter validation.

Business Value Justification (BVJ):
- Segment: Enterprise
- Business Goal: Security & Compliance audit trails
- Value Impact: Critical for Enterprise security requirements and compliance
- Revenue Impact: Required for Enterprise tier customers
"""

import warnings
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from netra_backend.app.core.exceptions_base import NetraException
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)

# Resilient parameter defaults and limits
DEFAULT_AUDIT_LIMIT = 100
MAX_AUDIT_LIMIT = 10000  # Increased from 1000 for flexibility
MIN_AUDIT_LIMIT = 1
DEFAULT_AUDIT_DAYS = 7
MAX_AUDIT_DAYS = 365


async def get_recent_logs(limit: int = DEFAULT_AUDIT_LIMIT, offset: int = 0) -> List[Dict[str, Any]]:
    """Get recent audit logs with pagination and resilient parameter handling."""
    try:
        # Apply resilient validation instead of strict validation
        validated_limit, validated_offset = _validate_audit_params_resilient(limit, offset)
        return await _fetch_audit_entries(validated_limit, validated_offset)
    except Exception as e:
        logger.error(f"Audit log fetch failed: {e}")
        raise NetraException(f"Failed to fetch audit logs: {e}")


async def _fetch_audit_entries(limit: int, offset: int) -> List[Dict[str, Any]]:
    """Fetch audit entries from storage."""
    # TODO: Replace with actual database query when audit storage is implemented
    # For now, return empty list as this will be mocked in tests
    return []


def _build_mock_audit_entry(entry_id: str, action: str, user_id: str) -> Dict[str, Any]:
    """Build a mock audit entry for testing."""
    return {
        "id": entry_id,
        "action": action,
        "user_id": user_id,
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z"
    }


async def log_admin_action(action: str, user_id: str, details: Dict[str, Any]) -> None:
    """Log an admin action to the audit trail."""
    try:
        await _persist_audit_entry(action, user_id, details)
    except Exception as e:
        raise NetraException(f"Failed to log audit entry: {e}")


async def _persist_audit_entry(action: str, user_id: str, details: Dict[str, Any]) -> None:
    """Persist audit entry to storage."""
    # TODO: Implement actual persistence when audit storage is ready
    pass


def _validate_audit_params_resilient(limit: int, offset: int) -> tuple[int, int]:
    """Validate audit query parameters with graceful degradation.
    
    Applies "Default to Resilience" - corrects invalid parameters with warnings
    instead of raising exceptions.
    """
    validated_limit = _validate_limit_resilient(limit)
    validated_offset = _validate_offset_resilient(offset)
    return validated_limit, validated_offset


def _validate_limit_resilient(limit: int) -> int:
    """Validate limit parameter with auto-correction."""
    if limit < MIN_AUDIT_LIMIT:
        warnings.warn(
            f"Limit {limit} below minimum {MIN_AUDIT_LIMIT}, using default {DEFAULT_AUDIT_LIMIT}",
            UserWarning,
            stacklevel=3
        )
        return DEFAULT_AUDIT_LIMIT
    
    if limit > MAX_AUDIT_LIMIT:
        warnings.warn(
            f"Limit {limit} exceeds maximum {MAX_AUDIT_LIMIT}, capping to maximum",
            UserWarning,
            stacklevel=3
        )
        return MAX_AUDIT_LIMIT
    
    return limit


def _validate_offset_resilient(offset: int) -> int:
    """Validate offset parameter with auto-correction."""
    if offset < 0:
        warnings.warn(
            f"Negative offset {offset} not allowed, using 0",
            UserWarning,
            stacklevel=3
        )
        return 0
    
    return offset


# Keep legacy function for backward compatibility
def _validate_audit_params(limit: int, offset: int) -> None:
    """Legacy validation function - deprecated in favor of resilient validation."""
    warnings.warn(
        "Using deprecated strict validation. Consider migrating to resilient validation.",
        DeprecationWarning,
        stacklevel=2
    )
    if limit < 1 or limit > 1000:
        raise NetraException("Limit must be between 1 and 1000")
    if offset < 0:
        raise NetraException("Offset must be non-negative")


async def get_audit_summary(days: int = DEFAULT_AUDIT_DAYS) -> Dict[str, int]:
    """Get audit activity summary for the specified days with resilient validation."""
    try:
        validated_days = _validate_days_resilient(days)
        return await _calculate_audit_summary(validated_days)
    except Exception as e:
        logger.error(f"Audit summary generation failed: {e}")
        raise NetraException(f"Failed to get audit summary: {e}")


def _validate_days_resilient(days: int) -> int:
    """Validate days parameter with auto-correction."""
    if days < 1:
        warnings.warn(
            f"Invalid days value {days}, using default {DEFAULT_AUDIT_DAYS}",
            UserWarning,
            stacklevel=3
        )
        return DEFAULT_AUDIT_DAYS
    
    if days > MAX_AUDIT_DAYS:
        warnings.warn(
            f"Days {days} exceeds maximum {MAX_AUDIT_DAYS}, capping to maximum",
            UserWarning,
            stacklevel=3
        )
        return MAX_AUDIT_DAYS
    
    return days


async def _calculate_audit_summary(days: int) -> Dict[str, int]:
    """Calculate audit summary statistics."""
    # TODO: Implement actual summary calculation
    return {"total_actions": 0, "unique_users": 0, "failed_actions": 0}


class AuditService:
    """Audit service class for centralized audit operations with resilient behavior."""
    
    def __init__(self):
        """Initialize the audit service with resilient defaults."""
        self.audit_enabled = True
        self.fallback_mode = False  # Enables graceful degradation
    
    async def log_action(self, action: str, user_id: str, details: Dict[str, Any]) -> None:
        """Log an audit action with resilient error handling."""
        try:
            await log_admin_action(action, user_id, details)
        except Exception as e:
            if self.fallback_mode:
                logger.warning(f"Audit logging failed, continuing in fallback mode: {e}")
            else:
                raise
    
    async def get_logs(self, limit: int = DEFAULT_AUDIT_LIMIT, offset: int = 0) -> List[Dict[str, Any]]:
        """Get audit logs with pagination and resilient parameter validation."""
        return await get_recent_logs(limit, offset)
    
    async def get_summary(self, days: int = DEFAULT_AUDIT_DAYS) -> Dict[str, int]:
        """Get audit summary for specified days with resilient validation."""
        return await get_audit_summary(days)
    
    def is_enabled(self) -> bool:
        """Check if audit logging is enabled."""
        return self.audit_enabled
    
    def enable_audit(self) -> None:
        """Enable audit logging."""
        self.audit_enabled = True
        logger.info("Audit logging enabled")
    
    def disable_audit(self) -> None:
        """Disable audit logging."""
        self.audit_enabled = False
        logger.warning("Audit logging disabled")
    
    def enable_fallback_mode(self) -> None:
        """Enable fallback mode for graceful degradation."""
        self.fallback_mode = True
        logger.info("Audit service fallback mode enabled")
    
    def disable_fallback_mode(self) -> None:
        """Disable fallback mode."""
        self.fallback_mode = False
        logger.info("Audit service fallback mode disabled")