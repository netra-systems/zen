"""Enhanced Tool Dispatcher - SSOT Compatibility Bridge.

This module provides backward compatibility for imports expecting EnhancedToolDispatcher.
After SSOT consolidation, all tool dispatcher functionality is now in UnifiedToolDispatcher.

Business Value:
- Maintains backward compatibility for existing test imports
- Redirects to SSOT UnifiedToolDispatcher implementation  
- Eliminates code duplication while preserving working imports
- Ensures all tool dispatching uses the same isolated, secure system

Architecture:
- Compatibility bridge pattern to maintain import compatibility
- All functionality delegated to UnifiedToolDispatcher SSOT implementation
- Factory methods preserved for proper user isolation
- Deprecation warnings guide migration to SSOT imports
"""

import warnings
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from netra_backend.app.services.user_execution_context import UserExecutionContext

# SSOT Import - redirect to the unified implementation
from netra_backend.app.core.tools.unified_tool_dispatcher import (
    UnifiedToolDispatcher,
    UnifiedToolDispatcherFactory,
    ToolDispatchRequest,
    ToolDispatchResponse,
    DispatchStrategy,
    AuthenticationError,
    PermissionError,
    SecurityViolationError,
)

# Factory function from the SSOT implementation
try:
    from netra_backend.app.core.tools.unified_tool_dispatcher import create_request_scoped_dispatcher
except ImportError:
    # Fallback if the function doesn't exist
    def create_request_scoped_dispatcher(*args, **kwargs):
        """Fallback factory method for request-scoped dispatcher."""
        return UnifiedToolDispatcherFactory.create_request_scoped(*args, **kwargs)


class EnhancedToolDispatcher(UnifiedToolDispatcher):
    """Enhanced Tool Dispatcher - Compatibility alias for UnifiedToolDispatcher.
    
    DEPRECATED: Use UnifiedToolDispatcher directly from SSOT module.
    This class is maintained for backward compatibility only.
    """
    
    def __init__(self, *args, **kwargs):
        """Initialize EnhancedToolDispatcher with deprecation warning."""
        warnings.warn(
            "EnhancedToolDispatcher is deprecated. Use UnifiedToolDispatcher from "
            "netra_backend.app.core.tools.unified_tool_dispatcher instead.",
            DeprecationWarning,
            stacklevel=2
        )
        super().__init__(*args, **kwargs)
    
    @classmethod
    def create_for_user(cls, user_context: "UserExecutionContext", **kwargs) -> "EnhancedToolDispatcher":
        """Create enhanced dispatcher for user with deprecation warning."""
        warnings.warn(
            "EnhancedToolDispatcher.create_for_user() is deprecated. Use "
            "UnifiedToolDispatcher.create_for_user() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Delegate to SSOT implementation
        instance = UnifiedToolDispatcher.create_for_user(user_context, **kwargs)
        # Return as EnhancedToolDispatcher type for compatibility
        instance.__class__ = cls
        return instance


class EnhancedToolDispatcherFactory(UnifiedToolDispatcherFactory):
    """Enhanced Tool Dispatcher Factory - Compatibility alias.
    
    DEPRECATED: Use UnifiedToolDispatcherFactory directly from SSOT module.
    This class is maintained for backward compatibility only.
    """
    
    @classmethod
    def create_enhanced_dispatcher(cls, *args, **kwargs) -> EnhancedToolDispatcher:
        """Create enhanced dispatcher with deprecation warning."""
        warnings.warn(
            "EnhancedToolDispatcherFactory.create_enhanced_dispatcher() is deprecated. "
            "Use UnifiedToolDispatcherFactory.create_request_scoped() instead.",
            DeprecationWarning,
            stacklevel=2
        )
        # Delegate to SSOT implementation
        instance = cls.create_request_scoped(*args, **kwargs)
        # Return as EnhancedToolDispatcher type for compatibility
        instance.__class__ = EnhancedToolDispatcher
        return instance


# Legacy compatibility aliases
ToolDispatcher = EnhancedToolDispatcher
ToolDispatcherFactory = EnhancedToolDispatcherFactory

# Factory functions for backward compatibility
def create_enhanced_dispatcher(*args, **kwargs):
    """Legacy factory function - redirects to SSOT implementation."""
    warnings.warn(
        "create_enhanced_dispatcher() is deprecated. Use UnifiedToolDispatcher.create_for_user() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    return EnhancedToolDispatcherFactory.create_enhanced_dispatcher(*args, **kwargs)


# Export all SSOT types for compatibility
__all__ = [
    'EnhancedToolDispatcher',
    'EnhancedToolDispatcherFactory', 
    'ToolDispatcher',
    'ToolDispatcherFactory',
    'ToolDispatchRequest',
    'ToolDispatchResponse',
    'DispatchStrategy',
    'AuthenticationError',
    'PermissionError',
    'SecurityViolationError',
    'create_enhanced_dispatcher',
    'create_request_scoped_dispatcher',
]