# Issue #1176 Phase 2: Canonical Import Mapping

**Date:** 2025-09-15
**Purpose:** Define SSOT import paths to resolve 15+ WebSocket import coordination gaps
**Status:** Remediation Plan

## Canonical Import Mapping (SSOT)

### 1. WebSocket Manager Classes (Current: 15 paths → Target: 1 canonical path)

**CANONICAL PATH:** `netra_backend.app.websocket_core.websocket_manager`

```python
# CANONICAL (SSOT)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager

# COMPATIBLE (SSOT)
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager

# DEPRECATED (Remove in Phase 2)
from netra_backend.app.websocket_core import WebSocketManager  # Remove
from netra_backend.app.websocket_core.handlers import WebSocketManager  # Remove
```

**Classes to Consolidate:**
- `WebSocketManager` → Keep in `websocket_manager.py` (CANONICAL)
- `UnifiedWebSocketManager` → Keep in `unified_manager.py` (COMPATIBLE)
- `_UnifiedWebSocketManagerImplementation` → Internal only
- `_WebSocketManagerFactory` → Internal only
- Remove from: `handlers.py`, `__init__.py` direct exports

### 2. Protocol Classes (Current: 6 paths → Target: 1 canonical path)

**CANONICAL PATH:** `netra_backend.app.websocket_core.protocols`

```python
# CANONICAL (SSOT)
from netra_backend.app.websocket_core.protocols import (
    WebSocketManagerProtocol,
    WebSocketProtocol,
    WebSocketManagerProtocolValidator,
    WebSocketProtocolValidator
)

# DEPRECATED (Remove)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManagerProtocol  # Remove
from netra_backend.app.websocket_core import WebSocketManagerProtocol  # Remove
```

### 3. Emitter Classes (Current: 9+ paths → Target: 1 canonical path)

**CANONICAL PATH:** `netra_backend.app.websocket_core.unified_emitter`

```python
# CANONICAL (SSOT)
from netra_backend.app.websocket_core.unified_emitter import (
    UnifiedWebSocketEmitter,
    WebSocketEmitterFactory,
    WebSocketEmitterPool
)

# COMPATIBLE ALIASES (Backward compatibility)
WebSocketEventEmitter = UnifiedWebSocketEmitter
IsolatedWebSocketEventEmitter = UnifiedWebSocketEmitter
UserWebSocketEmitter = UnifiedWebSocketEmitter
```

### 4. Types and Enums (Current: Multiple paths → Target: 1 canonical path)

**CANONICAL PATH:** `netra_backend.app.websocket_core.types`

```python
# CANONICAL (SSOT)
from netra_backend.app.websocket_core.types import (
    WebSocketConnection,
    WebSocketManagerMode,
    WebSocketMessage,
    ConnectionInfo,
    MessageType,
    ServerMessage,
    ErrorMessage,
    WebSocketStats,
    WebSocketConfig,
    AuthInfo
)
```

### 5. Handlers and Routing (Current: Multiple paths → Target: 1 canonical path)

**CANONICAL PATH:** `netra_backend.app.websocket_core.handlers`

```python
# CANONICAL (SSOT)
from netra_backend.app.websocket_core.handlers import (
    MessageRouter,
    UserMessageHandler,
    get_message_router
)

# Remove WebSocketManager export from handlers.py
```

## Remediation Actions

### Phase 2A: Clean Up `__init__.py` Exports

1. **Remove duplicate manager exports:**
   - Remove `WebSocketManager` from `__init__.py` direct exports
   - Keep canonical imports from specific modules

2. **Remove duplicate protocol exports:**
   - Remove `WebSocketManagerProtocol` from `__init__.py` direct exports
   - Use canonical import from `protocols.py`

3. **Standardize emitter exports:**
   - Export only `UnifiedWebSocketEmitter` with backward compatibility aliases

### Phase 2B: Update Individual Modules

1. **websocket_manager.py:**
   - Keep as canonical source for `WebSocketManager`
   - Remove protocol exports (use canonical from `protocols.py`)

2. **handlers.py:**
   - Remove `WebSocketManager` export
   - Keep only handler-related classes

3. **protocols.py:**
   - Keep as canonical source for all protocol classes
   - Remove duplicates from other modules

### Phase 2C: Update Import Consistency

1. **Core module imports:**
   - Eliminate mixed import patterns
   - Use either direct module imports OR `__init__.py` exports, not both

2. **Canonical import validation:**
   - Each class has exactly one canonical import path
   - All other paths either alias or are removed

## Expected Test Results After Remediation

After implementing this mapping:

1. **`test_websocket_manager_ssot_import_consolidation`** → PASS
   - Import paths reduced from 15 to 1-2 canonical paths

2. **`test_websocket_protocol_import_fragmentation_detection`** → PASS
   - Protocol paths reduced from 6 to 3 (within acceptable limit)

3. **`test_websocket_emitter_import_path_standardization`** → PASS
   - Emitter paths reduced from 9+ to 1-2 (UnifiedWebSocketEmitter + legacy alias)

4. **`test_websocket_core_module_import_consistency`** → PASS
   - Eliminate mixed import patterns, use consistent strategy

5. **`test_canonical_import_path_validation`** → PASS
   - All classes have single canonical import path

## SSOT Compliance Validation

After remediation:
- ✅ Single canonical source for each WebSocket component
- ✅ Backward compatibility maintained through aliases
- ✅ No duplicate class definitions or exports
- ✅ Consistent import patterns across codebase
- ✅ Golden Path functionality maintained

**Business Impact:** Resolves coordination gaps that could cause WebSocket race conditions affecting chat functionality (90% of platform value).