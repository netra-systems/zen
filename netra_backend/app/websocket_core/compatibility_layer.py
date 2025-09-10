"""
WebSocket Manager Compatibility Layer - Phase 1 SSOT Remediation

This module provides backward compatibility during the SSOT consolidation process.
It ensures existing code continues to work while guiding migration to SSOT patterns.

PHASE 1 OBJECTIVE: Preserve functionality while enabling deprecation warnings
PHASE 2-4: Gradual migration to pure SSOT implementation
"""

import warnings
from typing import Any, Dict, Optional
from netra_backend.app.logging_config import central_logger
from netra_backend.app.websocket_core.unified_manager import WebSocketManager

logger = central_logger.get_logger(__name__)


def _emit_deprecation_warning(old_pattern: str, new_pattern: str, caller_context: str = ""):
    """
    Emit standardized deprecation warning for WebSocket manager usage.
    
    Args:
        old_pattern: The deprecated usage pattern
        new_pattern: The recommended SSOT pattern
        caller_context: Additional context about the caller
    """
    import inspect
    
    # Get caller information
    frame = inspect.currentframe()
    caller_info = "unknown"
    if frame and frame.f_back and frame.f_back.f_back:
        caller_frame = frame.f_back.f_back
        caller_info = f"{caller_frame.f_code.co_filename}:{caller_frame.f_lineno}"
    
    warning_message = (
        f"WEBSOCKET SSOT DEPRECATION: {old_pattern} is deprecated. "
        f"Use {new_pattern} instead. "
        f"Called from: {caller_info} {caller_context}"
    )
    
    warnings.warn(warning_message, DeprecationWarning, stacklevel=3)
    logger.warning(f"SSOT Migration Required: {warning_message}")


class DeprecatedWebSocketManagerFactory:
    """
    Deprecated wrapper for WebSocketManagerFactory.
    
    PHASE 1 COMPATIBILITY: Provides backward compatibility while guiding migration.
    This class wraps the SSOT WebSocketManager with factory-like interface.
    """
    
    def __init__(self, max_managers_per_user: int = 20, connection_timeout_seconds: int = 1800):
        """
        Initialize deprecated factory.
        
        Args:
            max_managers_per_user: Ignored (SSOT handles resource management)
            connection_timeout_seconds: Ignored (SSOT handles timeouts)
        """
        _emit_deprecation_warning(
            "WebSocketManagerFactory(...)",
            "WebSocketManager.from_user_context(user_context)",
            "- Factory pattern replaced by SSOT class method"
        )
        
        self._ssot_manager = WebSocketManager()
        logger.info("COMPATIBILITY: Created deprecated WebSocketManagerFactory wrapper")
    
    async def create_manager(self, user_context) -> WebSocketManager:
        """
        Create manager using deprecated factory pattern.
        
        Args:
            user_context: User execution context
            
        Returns:
            WebSocketManager instance (SSOT)
        """
        _emit_deprecation_warning(
            "factory.create_manager(user_context)",
            "WebSocketManager.from_user_context(user_context)",
            "- Use SSOT class method directly"
        )
        
        # Delegate to SSOT factory method
        return WebSocketManager.from_user_context(user_context)
    
    def cleanup_manager(self, isolation_key: str) -> bool:
        """
        Deprecated cleanup method.
        
        Args:
            isolation_key: Manager isolation key (ignored)
            
        Returns:
            Always True (SSOT handles cleanup automatically)
        """
        _emit_deprecation_warning(
            "factory.cleanup_manager(isolation_key)",
            "await manager.shutdown()",
            "- SSOT handles cleanup automatically"
        )
        
        logger.info(f"COMPATIBILITY: Cleanup requested for {isolation_key} (SSOT auto-manages)")
        return True


def create_deprecated_websocket_manager(*args, **kwargs) -> WebSocketManager:
    """
    Deprecated factory function for WebSocket manager creation.
    
    PHASE 1 COMPATIBILITY: Maintains old function-based creation pattern.
    Guides migration to SSOT class-based pattern.
    
    Args:
        *args: Legacy positional arguments (ignored)
        **kwargs: Legacy keyword arguments (ignored)
        
    Returns:
        WebSocketManager instance (SSOT)
    """
    _emit_deprecation_warning(
        "create_websocket_manager(*args, **kwargs)",
        "WebSocketManager() or WebSocketManager.from_user_context(user_context)",
        "- Function replaced by SSOT class instantiation"
    )
    
    # Return SSOT instance
    return WebSocketManager()


# Legacy import aliases with deprecation warnings
def _create_legacy_alias(old_name: str, new_location: str):
    """Create a deprecated alias that warns when accessed."""
    
    class DeprecatedAlias:
        def __getattr__(self, name):
            _emit_deprecation_warning(
                f"from ... import {old_name}",
                f"from netra_backend.app.websocket_core.unified_manager import WebSocketManager",
                f"- Accessing {name} on deprecated {old_name}"
            )
            # Return the SSOT implementation
            from netra_backend.app.websocket_core.unified_manager import WebSocketManager
            return getattr(WebSocketManager, name, None)
    
    return DeprecatedAlias()


# Provide deprecated aliases for common import patterns
WebSocketManagerFactory = DeprecatedWebSocketManagerFactory
create_websocket_manager = create_deprecated_websocket_manager

# Export legacy names with deprecation warnings
__all__ = [
    'WebSocketManagerFactory',
    'create_websocket_manager', 
    'DeprecatedWebSocketManagerFactory',
    'create_deprecated_websocket_manager'
]


def validate_ssot_migration_readiness() -> Dict[str, Any]:
    """
    Validate system readiness for SSOT migration.
    
    PHASE 1 UTILITY: Helps assess migration progress and compatibility.
    
    Returns:
        Dictionary with migration readiness assessment
    """
    try:
        # Test SSOT instantiation
        manager = WebSocketManager()
        
        # Test enhanced interface methods
        interface_methods = [
            'get_connection_count',
            'get_connection_info', 
            'send_message',
            'broadcast_to_room',
            'recv',
            'send',
            'connect',
            'disconnect'
        ]
        
        missing_methods = []
        for method_name in interface_methods:
            if not hasattr(manager, method_name):
                missing_methods.append(method_name)
        
        return {
            'ssot_available': True,
            'enhanced_interface_complete': len(missing_methods) == 0,
            'missing_methods': missing_methods,
            'compatibility_layer_active': True,
            'deprecation_warnings_enabled': True,
            'migration_phase': 'Phase 1 - Interface Standardization',
            'readiness_score': 100 - (len(missing_methods) * 10),
            'next_phase_ready': len(missing_methods) == 0
        }
        
    except Exception as e:
        return {
            'ssot_available': False,
            'error': str(e),
            'migration_phase': 'Phase 1 - Interface Standardization',
            'readiness_score': 0,
            'next_phase_ready': False
        }


def get_migration_guide() -> str:
    """
    Get migration guide for developers.
    
    Returns:
        Formatted migration guide text
    """
    return """
# WebSocket Manager SSOT Migration Guide - Phase 1

## Current Phase: Interface Standardization

### ✅ RECOMMENDED PATTERNS (SSOT):

1. **Manager Creation:**
   ```python
   # SSOT - Direct instantiation
   manager = WebSocketManager()
   
   # SSOT - From user context  
   manager = WebSocketManager.from_user_context(user_context)
   ```

2. **Canonical Import:**
   ```python
   from netra_backend.app.websocket_core.unified_manager import WebSocketManager
   ```

### ⚠️ DEPRECATED PATTERNS (will be removed in Phase 3):

1. **Factory Usage:**
   ```python
   # DEPRECATED - will trigger warnings
   factory = WebSocketManagerFactory()
   manager = await factory.create_manager(user_context)
   ```

2. **Function-based Creation:**
   ```python
   # DEPRECATED - will trigger warnings  
   manager = create_websocket_manager(user_context)
   ```

3. **Legacy Imports:**
   ```python
   # DEPRECATED - will trigger warnings
   from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
   ```

### 📋 MIGRATION CHECKLIST:

- [ ] Replace factory.create_manager() with WebSocketManager.from_user_context()
- [ ] Update imports to use unified_manager.WebSocketManager
- [ ] Remove factory cleanup calls (SSOT auto-manages)
- [ ] Test with compatibility layer (Phase 1)
- [ ] Prepare for direct SSOT usage (Phase 2+)

### 🔧 VALIDATION:

```python
from netra_backend.app.websocket_core.compatibility_layer import validate_ssot_migration_readiness
print(validate_ssot_migration_readiness())
```
"""


if __name__ == "__main__":
    # Demonstration of compatibility layer
    print("=== WebSocket Manager SSOT Compatibility Layer ===")
    print(get_migration_guide())
    print("\n=== Migration Readiness Assessment ===")
    readiness = validate_ssot_migration_readiness()
    for key, value in readiness.items():
        print(f"{key}: {value}")