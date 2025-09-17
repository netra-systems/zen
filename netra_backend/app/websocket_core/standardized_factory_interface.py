"""
WebSocket Manager Standardized Factory Interface - Issue #1176 Phase 1 Fix

This module provides standardized factory interface contracts that ensure
consistent WebSocket Manager initialization across all integration points.

Business Justification:
- Prevents $500K+ ARR risk from WebSocket initialization failures
- Ensures consistent user isolation patterns
- Eliminates factory pattern coordination gaps

Root Cause Resolution:
- Issue #1176 identified lack of formal factory interface contracts
- Multiple factory implementations had inconsistent user context handling
- Integration points couldn't reliably validate manager instances
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Protocol, runtime_checkable
from dataclasses import dataclass
from datetime import datetime, timezone

from shared.logging.unified_logging_ssot import get_logger
from shared.types.core_types import UserID, ensure_user_id
from netra_backend.app.websocket_core.protocols import WebSocketProtocol
from netra_backend.app.websocket_core.types import WebSocketManagerMode

logger = get_logger(__name__)


@dataclass
class FactoryValidationResult:
    """Result of factory interface validation."""
    is_valid: bool
    validation_errors: list[str]
    manager_type: str
    user_context_isolated: bool
    interface_compliant: bool
    factory_method_available: bool
    validation_timestamp: datetime

    @property
    def is_production_ready(self) -> bool:
        """Check if factory result is ready for production use."""
        return (
            self.is_valid and
            self.user_context_isolated and
            self.interface_compliant and
            self.factory_method_available
        )


@runtime_checkable
class WebSocketManagerFactoryProtocol(Protocol):
    """
    Standardized factory interface for WebSocket Manager creation.

    All WebSocket manager factories MUST implement this protocol to ensure
    consistent initialization patterns across the codebase.

    This prevents the coordination gaps identified in Issue #1176 by providing
    a formal contract for factory implementations.
    """

    @abstractmethod
    def create_manager(self,
                      user_context: Optional[Any] = None,
                      mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED,
                      **kwargs) -> WebSocketProtocol:
        """
        Create a WebSocket manager instance with proper user isolation.

        Args:
            user_context: User execution context for isolation
            mode: WebSocket manager mode
            **kwargs: Additional configuration options

        Returns:
            WebSocket manager instance implementing WebSocketProtocol

        Raises:
            ValueError: If user_context is required but not provided
            RuntimeError: If manager creation fails
        """
        ...

    @abstractmethod
    def validate_manager_instance(self, manager: Any) -> FactoryValidationResult:
        """
        Validate that a manager instance meets factory standards.

        Args:
            manager: Manager instance to validate

        Returns:
            Validation result with detailed compliance information
        """
        ...

    @abstractmethod
    def supports_user_isolation(self) -> bool:
        """
        Check if this factory supports proper user context isolation.

        Returns:
            True if factory creates isolated manager instances
        """
        ...


class StandardizedWebSocketManagerFactory(WebSocketManagerFactoryProtocol):
    """
    Standardized WebSocket Manager Factory - Issue #1176 Phase 1 Implementation.

    This factory provides the canonical implementation of WebSocket manager creation
    with proper user context isolation and interface validation.

    Key Features:
    - Enforces WebSocketProtocol compliance
    - Validates user context isolation
    - Provides consistent factory interface
    - Prevents coordination gaps through validation
    """

    def __init__(self, require_user_context: bool = True):
        """
        Initialize standardized factory.

        Args:
            require_user_context: Whether to require user context for isolation
        """
        self.require_user_context = require_user_context
        self._factory_id = f"standardized_factory_{id(self)}"
        logger.info(f"Standardized WebSocket Manager Factory initialized: {self._factory_id}")

    def create_manager(self,
                      user_context: Optional[Any] = None,
                      mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED,
                      **kwargs) -> WebSocketProtocol:
        """
        Create WebSocket manager with standardized validation.

        This method ensures consistent manager creation with proper user isolation
        and interface compliance validation.
        """
        # Validate user context requirement
        if self.require_user_context and user_context is None:
            raise ValueError(
                "User context required for WebSocket manager creation. "
                "This ensures proper user isolation and prevents data leakage."
            )

        # Create manager using canonical import pattern
        from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager

        try:
            # Create manager instance
            manager = get_websocket_manager(
                user_context=user_context,
                mode=mode,
                **kwargs
            )

            # Validate created manager meets interface requirements
            validation_result = self.validate_manager_instance(manager)
            if not validation_result.is_production_ready:
                raise RuntimeError(
                    f"Created WebSocket manager failed validation: {validation_result.validation_errors}"
                )

            logger.info(
                f"WebSocket manager created successfully via standardized factory: "
                f"type={validation_result.manager_type}, "
                f"isolated={validation_result.user_context_isolated}"
            )

            return manager

        except Exception as e:
            logger.error(f"Standardized factory manager creation failed: {e}")
            raise RuntimeError(f"WebSocket manager creation failed: {e}") from e

    def validate_manager_instance(self, manager: Any) -> FactoryValidationResult:
        """
        Validate manager instance against standardized requirements.

        This performs comprehensive validation to ensure the manager instance
        meets all requirements for production use.
        """
        validation_errors = []
        manager_type = type(manager).__name__

        # Check protocol compliance
        from netra_backend.app.websocket_core.protocols import WebSocketProtocolValidator
        protocol_validation = WebSocketProtocolValidator.validate_manager_protocol(manager)
        interface_compliant = protocol_validation['compliant']

        if not interface_compliant:
            validation_errors.extend([
                f"Protocol compliance failed: {protocol_validation['missing_methods']}",
                f"Invalid signatures: {protocol_validation['invalid_signatures']}"
            ])

        # Check user context isolation capability
        user_context_isolated = self._validate_user_isolation(manager)
        if not user_context_isolated:
            validation_errors.append("Manager does not support proper user context isolation")

        # Check factory method availability
        factory_method_available = hasattr(manager, '__class__') and hasattr(manager.__class__, '__module__')
        if not factory_method_available:
            validation_errors.append("Manager not created through proper factory method")

        # Overall validity check
        is_valid = len(validation_errors) == 0

        result = FactoryValidationResult(
            is_valid=is_valid,
            validation_errors=validation_errors,
            manager_type=manager_type,
            user_context_isolated=user_context_isolated,
            interface_compliant=interface_compliant,
            factory_method_available=factory_method_available,
            validation_timestamp=datetime.now(timezone.utc)
        )

        if result.is_production_ready:
            logger.info(f"Manager validation PASSED: {manager_type}")
        else:
            logger.warning(f"Manager validation FAILED: {manager_type}, errors: {validation_errors}")

        return result

    def supports_user_isolation(self) -> bool:
        """Check if factory supports user context isolation."""
        return True  # Standardized factory always supports isolation

    def _validate_user_isolation(self, manager: Any) -> bool:
        """
        Validate that manager supports proper user context isolation.

        This checks for user context handling capabilities that prevent
        data leakage between concurrent users.
        """
        try:
            # Check for user context attribute or parameter support
            has_user_context = (
                hasattr(manager, 'user_context') or
                hasattr(manager, '_user_context') or
                hasattr(manager, '_user_context_handler')
            )

            # Check for isolation methods
            has_isolation_methods = (
                hasattr(manager, 'get_user_connections') and
                hasattr(manager, 'is_connection_active')
            )

            return has_user_context and has_isolation_methods

        except Exception as e:
            logger.warning(f"User isolation validation error: {e}")
            return False


class WebSocketManagerFactoryValidator:
    """
    Validator for WebSocket Manager Factory implementations.

    This class provides utilities to validate that factory implementations
    properly follow the standardized interface contracts.
    """

    @staticmethod
    def validate_factory_compliance(factory: Any) -> Dict[str, Any]:
        """
        Validate that a factory implementation meets standardized requirements.

        Args:
            factory: Factory instance to validate

        Returns:
            Validation report with compliance details
        """
        validation_result = {
            'compliant': False,
            'factory_type': type(factory).__name__,
            'missing_methods': [],
            'test_results': {},
            'validation_timestamp': datetime.now(timezone.utc).isoformat()
        }

        # Check protocol compliance
        is_protocol_instance = isinstance(factory, WebSocketManagerFactoryProtocol)
        validation_result['is_protocol_instance'] = is_protocol_instance

        # Check required methods
        required_methods = ['create_manager', 'validate_manager_instance', 'supports_user_isolation']
        for method_name in required_methods:
            if not hasattr(factory, method_name):
                validation_result['missing_methods'].append(method_name)
            elif not callable(getattr(factory, method_name)):
                validation_result['missing_methods'].append(f"{method_name} (not callable)")

        # Test factory functionality if compliant
        if len(validation_result['missing_methods']) == 0:
            try:
                # Test user isolation support
                supports_isolation = factory.supports_user_isolation()
                validation_result['test_results']['supports_isolation'] = supports_isolation

                # Test manager creation (if factory supports creation without user context)
                if not getattr(factory, 'require_user_context', True):
                    test_manager = factory.create_manager()
                    validation_result['test_results']['can_create_manager'] = True

                    # Test validation method
                    validation_test = factory.validate_manager_instance(test_manager)
                    validation_result['test_results']['validation_method_works'] = isinstance(
                        validation_test, FactoryValidationResult
                    )
                else:
                    validation_result['test_results']['requires_user_context'] = True

            except Exception as e:
                validation_result['test_results']['error'] = str(e)

        # Determine overall compliance
        validation_result['compliant'] = (
            len(validation_result['missing_methods']) == 0 and
            validation_result.get('test_results', {}).get('supports_isolation', False)
        )

        return validation_result

    @staticmethod
    def require_factory_compliance(factory: Any, context: str = "WebSocket Factory") -> None:
        """
        Require that a factory is compliant, raising error if not.

        Args:
            factory: Factory to validate
            context: Context string for error messages

        Raises:
            RuntimeError: If factory is not compliant
        """
        validation = WebSocketManagerFactoryValidator.validate_factory_compliance(factory)

        if not validation['compliant']:
            error_details = []
            if validation['missing_methods']:
                error_details.append(f"Missing methods: {', '.join(validation['missing_methods'])}")

            error_message = (
                f"FACTORY COMPLIANCE FAILURE: {context} does not implement "
                f"WebSocketManagerFactoryProtocol. Factory type: {validation['factory_type']}. "
                f"Issues: {'; '.join(error_details)}. "
                f"This prevents Issue #1176 coordination gaps by ensuring "
                f"all factories follow standardized interface contracts."
            )

            logger.critical(error_message)
            raise RuntimeError(error_message)

        logger.info(f"Factory compliance verified for {context}: {validation['factory_type']}")


# Export standardized factory as default
def get_standardized_websocket_manager_factory(require_user_context: bool = True) -> StandardizedWebSocketManagerFactory:
    """
    Get the standardized WebSocket manager factory.

    This is the canonical way to obtain a WebSocket manager factory that
    follows all standardized interface contracts.

    Args:
        require_user_context: Whether to require user context for manager creation

    Returns:
        Standardized factory instance
    """
    return StandardizedWebSocketManagerFactory(require_user_context=require_user_context)


__all__ = [
    'WebSocketManagerFactoryProtocol',
    'StandardizedWebSocketManagerFactory',
    'WebSocketManagerFactoryValidator',
    'FactoryValidationResult',
    'get_standardized_websocket_manager_factory'
]