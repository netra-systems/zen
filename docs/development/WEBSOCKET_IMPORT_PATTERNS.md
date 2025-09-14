# WebSocket Manager Import Patterns - Developer Guide

**Created:** 2025-09-14
**Purpose:** Clear guidance for developers on correct WebSocket manager import patterns
**Issue:** #996 WebSocket Manager Import Chaos - Cleanup remediation

## 🎯 **PREFERRED PATTERN (Canonical SSOT)**

### ✅ **Use This Import Pattern:**
```python
# CANONICAL: Preferred for all new code
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
from netra_backend.app.websocket_core.websocket_manager import get_websocket_manager
```

**Why This Pattern:**
- ✅ **SSOT Compliant**: Direct path to single source implementation
- ✅ **No Deprecation Warnings**: Clean import without warning messages
- ✅ **Clear Intent**: Explicit about which module provides the functionality
- ✅ **Future-Safe**: Will remain stable as architecture evolves

## ⚠️ **DEPRECATED PATTERNS (Still Work)**

### 🟡 **Legacy Pattern (Generates Warnings):**
```python
# DEPRECATED: Still works but generates deprecation warnings
from netra_backend.app.websocket_core import WebSocketManager
# WARNING: "Use canonical path 'from netra_backend.app.websocket_core.websocket_manager import WebSocketManager' instead."
```

**Issues with This Pattern:**
- ⚠️ **Deprecation Warnings**: Creates noise in logs
- ⚠️ **Maintenance Burden**: May be removed in future major versions
- ⚠️ **Developer Confusion**: Less clear about source of implementation

### 🔴 **Problematic Patterns (Avoid):**
```python
# PROBLEMATIC: Uses internal unified_manager path
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# PROBLEMATIC: Factory imports may cause initialization issues
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory
```

**Problems:**
- 🚨 **Import Failures**: May not work in all contexts
- 🚨 **Architecture Violations**: Bypasses SSOT patterns
- 🚨 **Multi-User Issues**: May cause user isolation problems

## 🛠️ **Migration Guide**

### **For Test Files:**
```python
# OLD (Deprecated)
from netra_backend.app.websocket_core import WebSocketManager

# NEW (Canonical)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
```

### **For Application Code:**
```python
# OLD (Legacy factory pattern)
from netra_backend.app.websocket_core import get_websocket_manager
websocket_manager = await get_websocket_manager(user_context)

# NEW (Direct instantiation with user context)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
websocket_manager = WebSocketManager(user_context=user_context)
```

### **For Backward Compatibility:**
```python
# If you need both patterns temporarily during migration
from netra_backend.app.websocket_core.websocket_manager import (
    WebSocketManager,
    get_websocket_manager,  # Backward compatibility function
    UnifiedWebSocketManager  # Alias for WebSocketManager
)
```

## 📋 **Quick Reference**

### **Common Import Statements:**
```python
# Core WebSocket manager
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# WebSocket connection management
from netra_backend.app.websocket_core.websocket_manager import WebSocketConnection

# Message serialization utilities
from netra_backend.app.websocket_core.websocket_manager import _serialize_message_safely

# Manager modes and configuration
from netra_backend.app.websocket_core.websocket_manager import WebSocketManagerMode
```

### **Type Checking:**
```python
# For type hints and protocol checking
from netra_backend.app.websocket_core.protocols import WebSocketManagerProtocol
```

## 🔍 **Validation**

### **Test Your Imports:**
```bash
# Quick test to verify import works
cd /path/to/netra-apex
python -c "from netra_backend.app.websocket_core.websocket_manager import WebSocketManager; print('✅ Import successful')"
```

### **Check for Deprecation Warnings:**
- If you see deprecation warnings in your logs, update your imports to the canonical pattern
- All deprecation warnings will point to the correct canonical import path

## 🚀 **Best Practices**

1. **Always Use Canonical Imports**: Start with `from netra_backend.app.websocket_core.websocket_manager import ...`

2. **User Context Required**: Always provide `user_context` when creating WebSocket managers:
   ```python
   # CORRECT: With user context
   manager = WebSocketManager(user_context=user_execution_context)

   # INCORRECT: Without user context (will fail)
   manager = WebSocketManager()  # ❌ Raises ValueError
   ```

3. **Prefer Direct Instantiation**: Use `WebSocketManager(user_context=...)` instead of factory functions for new code

4. **Import at Module Level**: Import WebSocket classes at module level, instantiate per-request
   ```python
   # Module level
   from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

   # Per-request instantiation
   async def handle_request(user_context):
       websocket_manager = WebSocketManager(user_context=user_context)
   ```

## 🔄 **Migration Checklist**

When updating WebSocket imports:

- [ ] Replace deprecated import paths with canonical paths
- [ ] Verify no deprecation warnings in logs
- [ ] Test that WebSocket functionality still works
- [ ] Ensure user context is properly provided
- [ ] Run relevant tests to verify no regressions

## 📚 **Related Documentation**

- [`SSOT_IMPORT_REGISTRY.md`](../SSOT_IMPORT_REGISTRY.md) - Complete import reference
- [`USER_CONTEXT_ARCHITECTURE.md`](USER_CONTEXT_ARCHITECTURE.md) - User context requirements
- [Issue #996](https://github.com/netra-systems/netra-apex/issues/996) - Import chaos remediation

---

**Last Updated:** 2025-09-14
**Maintained by:** Development Team
**Review Cadence:** Update when WebSocket architecture changes