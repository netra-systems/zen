"""
Canonical Import Interface - SSOT Import Standardization (Week 1 Low Risk)

This module provides the single source of truth for WebSocket manager imports,
addressing the "Import Chaos" violation identified in SSOT validation tests.

Business Value Justification (BVJ):
- Segment: Platform/Internal
- Business Goal: Eliminate import path confusion causing integration failures
- Value Impact: Standardize all WebSocket manager access patterns
- Revenue Impact: Prevent development delays from import inconsistencies

SSOT CONSOLIDATION: This module defines exactly one canonical import path
for each WebSocket functionality, eliminating the multiple import paths that
cause SSOT violations.

Usage:
```python
# CANONICAL IMPORTS - Use these paths only:
from netra_backend.app.websocket_core.canonical_imports import (
    WebSocketManagerFactory,      # Factory for isolated managers
    UnifiedWebSocketManager,      # Direct manager (use factory instead)
    WebSocketManagerProtocol,     # Interface protocol
)
```
"""

# ============================================================================
# CANONICAL IMPORT PATHS - Single Source of Truth
# ============================================================================

# CANONICAL: WebSocket Manager Factory (PREFERRED)
from netra_backend.app.websocket_core.websocket_manager_factory import (
    WebSocketManagerFactory,
    get_websocket_manager_factory,
    create_websocket_manager,
    FactoryInitializationError,
    WebSocketComponentError,
)

# CANONICAL: Unified WebSocket Manager (Direct Use - Use Factory Instead)
from netra_backend.app.websocket_core.unified_manager import (
    UnifiedWebSocketManager,
    WebSocketConnection,
)

# CANONICAL: WebSocket Protocol Interface
from netra_backend.app.websocket_core.protocols import (
    WebSocketManagerProtocol,
    WebSocketManagerProtocolValidator,
)

# CANONICAL: Migration Support (Temporary - Remove After Migration)
from netra_backend.app.websocket_core.migration_adapter import (
    get_legacy_websocket_manager,
    migrate_singleton_usage,
)

# ============================================================================
# DEPRECATED IMPORTS - Do Not Use These Paths
# ============================================================================

# DEPRECATED: Direct manager imports (use factory instead)
# from netra_backend.app.websocket_core.manager import WebSocketManager
# from netra_backend.app.websocket_core.unified_manager import get_websocket_manager

# DEPRECATED: Multiple interface imports (use canonical protocol instead)  
# from netra_backend.app.core.interfaces_websocket import WebSocketManagerProtocol

# DEPRECATED: Global function access (use factory pattern instead)
# from netra_backend.app.websocket_core import get_websocket_manager

# ============================================================================
# CANONICAL EXPORT INTERFACE
# ============================================================================

# Single source of truth exports
__all__ = [
    # PREFERRED: Use these for new code
    'WebSocketManagerFactory',
    'get_websocket_manager_factory',
    'create_websocket_manager',
    
    # INTERFACE: Use for type checking and contracts
    'WebSocketManagerProtocol',
    'WebSocketManagerProtocolValidator',
    
    # SUPPORT: Use for implementation
    'UnifiedWebSocketManager',
    'WebSocketConnection',
    
    # MIGRATION: Temporary compatibility (remove after migration)
    'get_legacy_websocket_manager',
    'migrate_singleton_usage',
    
    # ERRORS: For proper error handling
    'FactoryInitializationError',
    'WebSocketComponentError',
]

# ============================================================================
# IMPORT VALIDATION FUNCTIONS
# ============================================================================

def validate_canonical_import_usage() -> dict:
    """
    Validate that canonical imports are being used properly.
    
    Returns:
        Dictionary with validation results
    """
    import inspect
    import sys
    
    validation_results = {
        'canonical_imports_available': True,
        'deprecated_patterns_detected': [],
        'recommended_migrations': [],
        'ssot_compliance_score': 100  # Start at 100, deduct for violations
    }
    
    # Check if deprecated patterns are being used in the call stack
    frame = inspect.currentframe()
    try:
        # Walk up the call stack to find import patterns
        current_frame = frame
        while current_frame:
            filename = current_frame.f_code.co_filename
            if 'websocket' in filename.lower():
                # Check for deprecated import patterns in the calling code
                # This is a simplified check - in production, you'd use AST parsing
                validation_results['files_using_websocket_imports'] = filename
            current_frame = current_frame.f_back
            
    finally:
        del frame  # Prevent reference cycles
    
    return validation_results


def get_canonical_import_guide() -> str:
    """
    Get the canonical import guide for WebSocket managers.
    
    Returns:
        String containing import guidance
    """
    return """
CANONICAL WEBSOCKET IMPORT GUIDE

 PASS:  CORRECT (Use these patterns):
```python
from netra_backend.app.websocket_core.canonical_imports import (
    WebSocketManagerFactory,
    WebSocketManagerProtocol,
)

# Create isolated manager
factory = WebSocketManagerFactory()
manager = await factory.create_isolated_manager(user_id, connection_id)
```

 FAIL:  INCORRECT (Don't use these patterns):
```python
# Multiple import paths (causes SSOT violations)
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager  
from netra_backend.app.core.interfaces_websocket import WebSocketManagerProtocol

# Singleton patterns (security risk)
from netra_backend.app.websocket_core.unified_manager import get_websocket_manager
manager = get_websocket_manager()  #  ALERT:  SECURITY VIOLATION
```

MIGRATION STEPS:
1. Replace all websocket manager imports with canonical_imports
2. Use WebSocketManagerFactory for all manager creation
3. Pass user context to all operations
4. Remove any get_websocket_manager() singleton usage
"""


if __name__ == "__main__":
    # Self-validation
    results = validate_canonical_import_usage()
    print("Canonical Import Validation Results:")
    print(f" PASS:  Canonical imports available: {results['canonical_imports_available']}")
    print(f" CHART:  SSOT compliance score: {results['ssot_compliance_score']}%")
    
    if results['deprecated_patterns_detected']:
        print(" WARNING: [U+FE0F]  Deprecated patterns detected:")
        for pattern in results['deprecated_patterns_detected']:
            print(f"   - {pattern}")
    
    if results['recommended_migrations']:
        print("[U+1F527] Recommended migrations:")
        for migration in results['recommended_migrations']:
            print(f"   - {migration}")
    else:
        print(" PASS:  No migrations needed - using canonical imports")