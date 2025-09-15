"""
WebSocket Manager SSOT Validation Enhancer - Issue #712 Remediation

This module provides enhanced validation and enforcement for WebSocket Manager SSOT patterns.
It addresses the specific validation gaps identified in Issue #712 while maintaining
Golden Path functionality and backward compatibility.

Business Value Justification (BVJ):
- Segment: Platform Infrastructure (affects ALL user segments)
- Business Goal: Ensure long-term architectural stability
- Value Impact: Prevents architectural drift that could impact $500K+ ARR chat functionality
- Revenue Impact: Protects business-critical WebSocket infrastructure reliability

ISSUE #712 FIXES:
1. Enhanced factory pattern validation
2. User isolation architecture enforcement
3. Direct instantiation controls
4. Cross-user event bleeding prevention
5. Instance duplication detection
"""

import asyncio
import logging
import threading
import weakref
from typing import Dict, Set, Optional, Any, List, Union
from datetime import datetime, timezone
from collections import defaultdict

from shared.types.core_types import UserID, ensure_user_id
from netra_backend.app.logging_config import central_logger

logger = central_logger.get_logger(__name__)


class SSotValidationError(Exception):
    """Exception raised when SSOT validation rules are violated."""
    pass


class UserIsolationViolation(SSotValidationError):
    """Exception raised when user isolation patterns are violated."""
    pass


class FactoryBypassDetected(SSotValidationError):
    """Exception raised when factory patterns are bypassed."""
    pass


# Global registry for tracking WebSocket manager instances
_manager_instances: weakref.WeakSet = weakref.WeakSet()
_user_manager_mapping: Dict[str, weakref.ref] = {}
_instance_creation_lock = threading.Lock()


class WebSocketManagerSSotValidator:
    """
    Validator for WebSocket Manager SSOT compliance.

    This class implements the validation rules identified in Issue #712 to ensure
    proper SSOT patterns are followed while maintaining Golden Path functionality.
    """

    def __init__(self):
        self.validation_enabled = True
        self.strict_mode = False  # Can be enabled for development/testing
        self._validation_history: List[Dict[str, Any]] = []

    def validate_manager_creation(
        self,
        manager_instance: Any,
        user_context: Optional[Any] = None,
        creation_method: str = "unknown"
    ) -> bool:
        """
        Validate WebSocket manager creation follows SSOT patterns.

        Args:
            manager_instance: The WebSocket manager instance being created
            user_context: UserExecutionContext for user isolation validation
            creation_method: How the manager was created (factory, direct, etc.)

        Returns:
            bool: True if validation passes

        Raises:
            SSotValidationError: If validation fails in strict mode
        """
        validation_issues = []

        # Issue #712 Fix 1: Validate user context for proper isolation
        if user_context is None:
            issue = "Manager created without UserExecutionContext - potential isolation violation"
            validation_issues.append(issue)
            logger.warning(f"SSOT VALIDATION: {issue}")

        # Issue #712 Fix 2: Validate manager type is correct SSOT class
        from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
        if not isinstance(manager_instance, WebSocketManager):
            issue = f"Manager not instance of SSOT WebSocketManager: {type(manager_instance)}"
            validation_issues.append(issue)
            logger.error(f"SSOT VIOLATION: {issue}")

        # Issue #712 Fix 3: Track instance creation to detect duplication
        with _instance_creation_lock:
            _manager_instances.add(manager_instance)

            if user_context and hasattr(user_context, 'user_id'):
                user_id_str = str(user_context.user_id)

                # Check for existing manager for this user
                if user_id_str in _user_manager_mapping:
                    existing_ref = _user_manager_mapping[user_id_str]
                    if existing_ref() is not None:  # Reference still alive
                        issue = f"Multiple manager instances for user {user_id_str} - potential duplication"
                        validation_issues.append(issue)
                        logger.warning(f"SSOT VALIDATION: {issue}")

                # Register this manager for the user
                _user_manager_mapping[user_id_str] = weakref.ref(manager_instance)

        # Record validation attempt
        self._validation_history.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "creation_method": creation_method,
            "has_user_context": user_context is not None,
            "issues": validation_issues,
            "passed": len(validation_issues) == 0
        })

        # Handle validation failures
        if validation_issues:
            if self.strict_mode:
                raise SSotValidationError(f"SSOT validation failed: {validation_issues}")
            else:
                logger.warning(f"SSOT validation issues (non-blocking): {validation_issues}")
                return False

        logger.debug("SSOT validation passed for manager creation")
        return True

    def validate_user_isolation(
        self,
        manager_instance: Any,
        user_id: Union[str, UserID],
        operation: str = "unknown"
    ) -> bool:
        """
        Validate user isolation is properly maintained.

        Args:
            manager_instance: WebSocket manager instance
            user_id: User ID for isolation validation
            operation: Description of the operation being validated

        Returns:
            bool: True if user isolation is valid
        """
        validation_issues = []

        # Issue #712 Fix 4: Validate user context isolation
        if hasattr(manager_instance, '_user_context'):
            manager_user_id = getattr(manager_instance._user_context, 'user_id', None)
            if manager_user_id and str(manager_user_id) != str(user_id):
                issue = f"User ID mismatch: manager={manager_user_id}, operation={user_id}"
                validation_issues.append(issue)
                logger.error(f"USER ISOLATION VIOLATION: {issue} in {operation}")

        # Issue #712 Fix 5: Check for cross-user contamination indicators
        if hasattr(manager_instance, '_active_connections'):
            connections = getattr(manager_instance, '_active_connections', {})
            user_connections = [
                conn for conn in connections.values()
                if getattr(conn, 'user_id', None) == str(user_id)
            ]

            other_user_connections = [
                conn for conn in connections.values()
                if getattr(conn, 'user_id', None) and getattr(conn, 'user_id') != str(user_id)
            ]

            if user_connections and other_user_connections:
                issue = f"Manager has connections for multiple users - potential contamination"
                validation_issues.append(issue)
                logger.warning(f"USER ISOLATION WARNING: {issue}")

        if validation_issues:
            if self.strict_mode:
                raise UserIsolationViolation(f"User isolation validation failed: {validation_issues}")
            else:
                logger.warning(f"User isolation issues (non-blocking): {validation_issues}")
                return False

        return True

    def detect_factory_bypass(self, creation_stack: Optional[List[str]] = None) -> bool:
        """
        Detect if WebSocket manager creation bypassed proper factory patterns.

        Args:
            creation_stack: Optional call stack for analysis

        Returns:
            bool: True if bypass detected
        """
        # Issue #712 Fix 6: Basic factory bypass detection
        if creation_stack:
            # Look for direct instantiation patterns
            direct_patterns = [
                'UnifiedWebSocketManager(',
                'WebSocketManager(',
                '__new__(',
                '__init__('
            ]

            factory_patterns = [
                'create_websocket_manager',
                'get_websocket_manager',
                'WebSocketManagerFactory'
            ]

            has_direct = any(pattern in str(creation_stack) for pattern in direct_patterns)
            has_factory = any(pattern in str(creation_stack) for pattern in factory_patterns)

            if has_direct and not has_factory:
                logger.warning("FACTORY BYPASS DETECTED: Direct manager instantiation without factory")
                return True

        return False

    def get_validation_summary(self) -> Dict[str, Any]:
        """Get summary of validation history and current state."""
        total_validations = len(self._validation_history)
        passed_validations = sum(1 for v in self._validation_history if v['passed'])

        return {
            "total_validations": total_validations,
            "passed_validations": passed_validations,
            "failed_validations": total_validations - passed_validations,
            "success_rate": passed_validations / total_validations if total_validations > 0 else 0.0,
            "active_managers": len(_manager_instances),
            "tracked_users": len(_user_manager_mapping),
            "strict_mode": self.strict_mode,
            "validation_enabled": self.validation_enabled,
            "recent_issues": [
                v for v in self._validation_history[-10:]
                if not v['passed']
            ]
        }


# Global validator instance
_ssot_validator = WebSocketManagerSSotValidator()


def validate_websocket_manager_creation(
    manager_instance: Any,
    user_context: Optional[Any] = None,
    creation_method: str = "unknown"
) -> bool:
    """
    Public interface for validating WebSocket manager creation.

    This function should be called by all WebSocket manager factory functions
    to ensure SSOT compliance.
    """
    return _ssot_validator.validate_manager_creation(
        manager_instance, user_context, creation_method
    )


def validate_user_isolation(
    manager_instance: Any,
    user_id: Union[str, UserID],
    operation: str = "unknown"
) -> bool:
    """
    Public interface for validating user isolation.

    This function should be called before operations that could affect
    user data isolation.
    """
    return _ssot_validator.validate_user_isolation(
        manager_instance, user_id, operation
    )


def enable_strict_validation(enabled: bool = True):
    """Enable or disable strict SSOT validation mode."""
    _ssot_validator.strict_mode = enabled
    logger.info(f"SSOT strict validation mode: {'enabled' if enabled else 'disabled'}")


def get_ssot_validation_summary() -> Dict[str, Any]:
    """Get current SSOT validation summary."""
    return _ssot_validator.get_validation_summary()


# Export key functions
__all__ = [
    'SSotValidationError',
    'UserIsolationViolation',
    'FactoryBypassDetected',
    'validate_websocket_manager_creation',
    'validate_user_isolation',
    'enable_strict_validation',
    'get_ssot_validation_summary'
]

logger.info("WebSocket Manager SSOT Validation Enhancer loaded - Issue #712 remediation active")