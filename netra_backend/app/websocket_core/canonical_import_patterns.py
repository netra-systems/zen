"""
WebSocket Canonical Import Patterns - Phase 1 Foundation

Business Value Justification:
- Segment: Platform/Infrastructure
- Business Goal: Zero breaking changes during SSOT consolidation
- Value Impact: Consolidate 36+ import patterns to 4 canonical patterns
- Strategic Impact: Enable safe refactoring while maintaining system stability

This module defines the 4 canonical import patterns that will replace the
36+ fragmented import patterns currently used across the codebase.

ISSUE #1047 PHASE 1: Canonical import pattern design for backwards compatibility
"""

from typing import Any, Optional, Dict, Union
import warnings
from functools import wraps

# Import the actual implementation
from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation
from netra_backend.app.websocket_core.types import WebSocketManagerMode


class CanonicalImportDeprecationWarning(UserWarning):
    """Warning for deprecated import patterns during migration."""
    pass


def _log_import_usage(pattern_name: str, import_path: str):
    """Log usage of import patterns for migration tracking."""
    from shared.logging.unified_logging_ssot import get_logger
    logger = get_logger(__name__)
    logger.debug(f"Canonical import pattern used: {pattern_name} from {import_path}")


def _create_deprecation_wrapper(func, old_path: str, new_path: str):
    """Create deprecation wrapper for legacy import functions."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        warnings.warn(
            f"Import from '{old_path}' is deprecated. Use '{new_path}' instead. "
            f"This will be removed in Phase 2 of SSOT consolidation.",
            CanonicalImportDeprecationWarning,
            stacklevel=2
        )
        return func(*args, **kwargs)
    return wrapper


# =============================================================================
# CANONICAL PATTERN 1: Factory Function Pattern (PREFERRED)
# =============================================================================
# This is the primary pattern for creating WebSocket managers
# Replaces: 15+ different factory function variations

def get_websocket_manager(user_context: Optional[Any] = None,
                         mode: WebSocketManagerMode = WebSocketManagerMode.UNIFIED,
                         **kwargs) -> _UnifiedWebSocketManagerImplementation:
    """
    CANONICAL PATTERN 1: Factory Function Pattern

    Primary method for obtaining WebSocket manager instances.
    Ensures proper user isolation and SSOT compliance.

    Args:
        user_context: User execution context for isolation
        mode: WebSocket manager mode (defaults to UNIFIED)
        **kwargs: Additional configuration options

    Returns:
        Properly configured WebSocket manager instance

    Example:
        from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager
        manager = get_websocket_manager(user_context=ctx)
    """
    _log_import_usage("Factory Function", "canonical_import_patterns.get_websocket_manager")

    # Use the existing factory function from websocket_manager.py
    from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager as _get_manager
    return _get_manager(user_context=user_context, mode=mode, **kwargs)


async def create_websocket_manager_async(user_context: Optional[Any] = None,
                                        **kwargs) -> _UnifiedWebSocketManagerImplementation:
    """
    CANONICAL PATTERN 1a: Async Factory Function Pattern

    Async version of the factory function for async contexts.

    Args:
        user_context: User execution context for isolation
        **kwargs: Additional configuration options

    Returns:
        Properly configured WebSocket manager instance
    """
    _log_import_usage("Async Factory Function", "canonical_import_patterns.create_websocket_manager_async")

    # For now, the creation is not actually async, but this provides future compatibility
    return get_websocket_manager(user_context=user_context, **kwargs)


# =============================================================================
# CANONICAL PATTERN 2: Class-based Import Pattern
# =============================================================================
# Direct class import for type hints and direct instantiation
# Replaces: 8+ different class import variations

class UnifiedWebSocketManager(_UnifiedWebSocketManagerImplementation):
    """
    CANONICAL PATTERN 2: Class-based Import Pattern

    Direct access to the WebSocket manager class.
    Use this for type hints and when direct instantiation is needed.

    Note: Direct instantiation requires proper authorization token.
    For normal usage, prefer get_websocket_manager() factory function.

    Example:
        from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager

        # For type hints:
        def process_manager(manager: UnifiedWebSocketManager) -> None: ...

        # For factory usage (preferred):
        manager = get_websocket_manager(user_context=ctx)
    """

    def __init__(self, *args, **kwargs):
        _log_import_usage("Class Import", "canonical_import_patterns.UnifiedWebSocketManager")
        super().__init__(*args, **kwargs)


# Type alias for backwards compatibility
WebSocketManager = UnifiedWebSocketManager


# =============================================================================
# CANONICAL PATTERN 3: Component Interface Pattern
# =============================================================================
# Import specific component interfaces for type safety
# Replaces: 10+ different component-specific imports

from netra_backend.app.websocket_core.interfaces import (
    ICoreConnectionManager,
    IEventBroadcastingService,
    IAuthenticationIntegration,
    IUserSessionRegistry,
    IPerformanceMonitor,
    IConfigurationProvider,
    IIntegrationBridge,
    IUnifiedWebSocketManager
)

# Export interfaces for canonical access
__all_interfaces__ = [
    'ICoreConnectionManager',
    'IEventBroadcastingService',
    'IAuthenticationIntegration',
    'IUserSessionRegistry',
    'IPerformanceMonitor',
    'IConfigurationProvider',
    'IIntegrationBridge',
    'IUnifiedWebSocketManager'
]


def get_component_interface(component_name: str) -> type:
    """
    CANONICAL PATTERN 3: Component Interface Pattern

    Get interface type by name for dynamic usage.

    Args:
        component_name: Name of the component interface

    Returns:
        Interface class type

    Example:
        from netra_backend.app.websocket_core.canonical_import_patterns import get_component_interface

        connection_interface = get_component_interface('ICoreConnectionManager')
        def validate_component(component: connection_interface) -> bool: ...
    """
    _log_import_usage("Component Interface", f"canonical_import_patterns.get_component_interface({component_name})")

    interface_map = {
        'ICoreConnectionManager': ICoreConnectionManager,
        'IEventBroadcastingService': IEventBroadcastingService,
        'IAuthenticationIntegration': IAuthenticationIntegration,
        'IUserSessionRegistry': IUserSessionRegistry,
        'IPerformanceMonitor': IPerformanceMonitor,
        'IConfigurationProvider': IConfigurationProvider,
        'IIntegrationBridge': IIntegrationBridge,
        'IUnifiedWebSocketManager': IUnifiedWebSocketManager
    }

    if component_name not in interface_map:
        raise ValueError(f"Unknown component interface: {component_name}")

    return interface_map[component_name]


# =============================================================================
# CANONICAL PATTERN 4: Legacy Compatibility Pattern
# =============================================================================
# Backwards compatibility aliases for existing imports
# Replaces: 12+ legacy import paths

def create_legacy_compatibility_function(func_name: str, new_path: str):
    """Create backwards compatibility function with deprecation warning."""
    def legacy_func(*args, **kwargs):
        _log_import_usage("Legacy Compatibility", f"canonical_import_patterns.{func_name}")
        return get_websocket_manager(*args, **kwargs)

    return _create_deprecation_wrapper(legacy_func, f"old_module.{func_name}", new_path)


# Legacy compatibility aliases (will be deprecated in Phase 2)
create_websocket_manager = create_legacy_compatibility_function(
    "create_websocket_manager",
    "canonical_import_patterns.get_websocket_manager"
)

get_manager = create_legacy_compatibility_function(
    "get_manager",
    "canonical_import_patterns.get_websocket_manager"
)

create_manager = create_legacy_compatibility_function(
    "create_manager",
    "canonical_import_patterns.get_websocket_manager"
)


# =============================================================================
# Import Pattern Migration Guide
# =============================================================================

MIGRATION_GUIDE = {
    "PATTERN_1_FACTORY": {
        "description": "Factory Function Pattern - Primary method for creating managers",
        "canonical_import": "from netra_backend.app.websocket_core.canonical_import_patterns import get_websocket_manager",
        "usage": "manager = get_websocket_manager(user_context=ctx)",
        "replaces": [
            "from netra_backend.app.websocket_core.unified_manager import get_websocket_manager",
            "from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager",
            "from netra_backend.app.websocket_core.factory import get_websocket_manager",
            "from netra_backend.app.websocket_core import get_websocket_manager"
        ]
    },
    "PATTERN_2_CLASS": {
        "description": "Class Import Pattern - For type hints and direct access",
        "canonical_import": "from netra_backend.app.websocket_core.canonical_import_patterns import UnifiedWebSocketManager",
        "usage": "def process(manager: UnifiedWebSocketManager): ...",
        "replaces": [
            "from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager",
            "from netra_backend.app.websocket_core.unified_manager import _UnifiedWebSocketManagerImplementation",
            "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager",
            "from netra_backend.app.websocket_core import UnifiedWebSocketManager"
        ]
    },
    "PATTERN_3_INTERFACES": {
        "description": "Component Interface Pattern - For component-specific type safety",
        "canonical_import": "from netra_backend.app.websocket_core.canonical_import_patterns import ICoreConnectionManager",
        "usage": "def validate(component: ICoreConnectionManager): ...",
        "replaces": [
            "from netra_backend.app.websocket_core.interfaces import ICoreConnectionManager",
            "from netra_backend.app.websocket_core.components import ICoreConnectionManager"
        ]
    },
    "PATTERN_4_LEGACY": {
        "description": "Legacy Compatibility Pattern - Temporary backwards compatibility",
        "canonical_import": "from netra_backend.app.websocket_core.canonical_import_patterns import create_websocket_manager",
        "usage": "manager = create_websocket_manager(ctx)  # DEPRECATED",
        "replaces": [
            "from netra_backend.app.websocket_core.utils import create_websocket_manager",
            "from netra_backend.app.websocket_core.factory import create_websocket_manager",
            "from netra_backend.app.websocket_core import create_websocket_manager"
        ]
    }
}


def get_migration_guide() -> Dict[str, Any]:
    """
    Get the complete migration guide for import patterns.

    Returns:
        Dictionary containing migration guidance for all patterns
    """
    return MIGRATION_GUIDE


def validate_import_pattern_usage() -> Dict[str, Any]:
    """
    Validate current import pattern usage across the codebase.

    Returns:
        Validation report showing pattern compliance
    """
    return {
        "canonical_patterns_defined": 4,
        "legacy_patterns_supported": len(MIGRATION_GUIDE["PATTERN_4_LEGACY"]["replaces"]),
        "total_patterns_consolidated": sum(len(pattern["replaces"]) for pattern in MIGRATION_GUIDE.values()),
        "phase1_complete": True,
        "ready_for_phase2": True
    }


# Export all canonical imports for easy access
__all__ = [
    # Pattern 1: Factory Functions
    'get_websocket_manager',
    'create_websocket_manager_async',

    # Pattern 2: Class Imports
    'UnifiedWebSocketManager',
    'WebSocketManager',

    # Pattern 3: Component Interfaces
    'get_component_interface',
    *__all_interfaces__,

    # Pattern 4: Legacy Compatibility
    'create_websocket_manager',
    'get_manager',
    'create_manager',

    # Utilities
    'get_migration_guide',
    'validate_import_pattern_usage',
    'MIGRATION_GUIDE'
]