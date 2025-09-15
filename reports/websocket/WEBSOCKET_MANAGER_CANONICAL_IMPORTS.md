# WebSocket Manager Canonical Import Paths

**Issue #824: WebSocket Manager Fragmentation Consolidation - Phase 1 Documentation**

This document provides the canonical (preferred) import paths for WebSocket Manager components after SSOT consolidation.

## Summary of Changes

The WebSocket Manager has been consolidated into a Single Source of Truth (SSOT) architecture while maintaining backward compatibility. All import paths now resolve to the same `UnifiedWebSocketManager` implementation.

## Canonical Import Paths (PREFERRED)

### Primary WebSocket Manager

```python
# PREFERRED: Canonical import path
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# Usage
context = UserExecutionContext(...)
manager = WebSocketManager(user_context=context)
```

### Protocol Interface

```python
# PREFERRED: Protocol interface for type checking
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol

# Usage for type hints
def process_manager(manager: WebSocketManagerProtocol) -> None:
    # Your code here
    pass
```

### Factory Pattern (for compatibility)

```python
# PREFERRED: Direct instantiation
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
manager = WebSocketManager(user_context=context)

# COMPATIBILITY: Factory pattern (if needed for legacy code)
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager
manager = await create_websocket_manager(user_context=context)
```

### SSOT Implementation (advanced usage)

```python
# ADVANCED: Direct access to SSOT implementation
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# Note: This is the same as WebSocketManager, use WebSocketManager import instead
```

## Legacy Import Paths (DEPRECATED BUT WORKING)

These import paths continue to work but show deprecation warnings:

```python
# DEPRECATED: Shows deprecation warning
from netra_backend.app.websocket_core import WebSocketManager

# DEPRECATED: Legacy factory imports (working but discouraged)
from netra_backend.app.websocket_core import create_websocket_manager
```

## Migration Guide

### For New Code

```python
# NEW CODE: Use canonical imports
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.services.user_execution_context import UserExecutionContext

async def setup_websocket(user_context: UserExecutionContext):
    manager = WebSocketManager(user_context=user_context)
    return manager
```

### For Existing Code

No immediate changes required. Existing imports will continue to work with deprecation warnings. Update imports when convenient:

```python
# OLD (working with deprecation warning)
from netra_backend.app.websocket_core import WebSocketManager

# NEW (no warning)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
```

## Import Path Reference

| Component | Canonical Path | Legacy Path | Status |
|-----------|---------------|-------------|---------|
| WebSocketManager | `netra_backend.app.websocket_core.websocket_manager` | `netra_backend.app.websocket_core` | ✅ Both work |
| WebSocketManagerProtocol | `netra_backend.app.websocket_core.protocols` | N/A | ✅ New |
| create_websocket_manager | `netra_backend.app.websocket_core.websocket_manager_factory` | `netra_backend.app.websocket_core` | ✅ Both work |
| UnifiedWebSocketManager | `netra_backend.app.websocket_core.unified_manager` | N/A | ✅ SSOT |

## Validation

You can validate your imports are correct by running:

```python
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# These should be the same class
assert WebSocketManager == UnifiedWebSocketManager
print("✅ Imports are using SSOT implementation")
```

## Key Benefits of Canonical Imports

1. **Clear Intent**: Import path shows exactly what you're importing
2. **No Warnings**: Canonical paths don't show deprecation warnings
3. **Future-Proof**: Will continue to work as SSOT consolidation progresses
4. **Type Safety**: Better IDE support and type checking
5. **Performance**: Direct imports are slightly more efficient

## Business Value Protection

These canonical import paths protect **$500K+ ARR** by ensuring:
- Consistent WebSocket Manager behavior across all services
- No breaking changes during SSOT migration
- Clear upgrade path for developers
- Maintained backward compatibility

## Next Steps

1. **Phase 1 Complete**: Interface standardization with canonical imports
2. **Phase 2 Upcoming**: Import unification across codebase
3. **Phase 3 Future**: Legacy import path removal (with sufficient notice)
4. **Phase 4 Final**: Test consolidation and final validation

## Questions?

For questions about WebSocket Manager imports or SSOT consolidation:
- Check the WebSocket Manager Protocol: `netra_backend.app.websocket_core.protocols`
- Review compatibility validation: Run validation scripts in project root
- Reference this documentation for canonical patterns

---

**Generated**: 2025-09-13 as part of Issue #824 WebSocket Manager SSOT consolidation
**Status**: Phase 1 Complete - Interface Standardization