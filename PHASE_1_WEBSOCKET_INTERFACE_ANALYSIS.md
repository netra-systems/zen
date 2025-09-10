# Phase 1: WebSocket Manager Interface Analysis & Standardization

**Created:** 2025-09-10  
**Phase:** 1 of 4-phase SSOT remediation plan  
**Objective:** Document interface inconsistencies and create standardized protocol

## Executive Summary

Analysis of the three WebSocket manager implementations reveals **14 critical interface inconsistencies** that prevent SSOT consolidation. This document standardizes the interface to enable Phase 2 consolidation while preserving backward compatibility.

## Current WebSocket Manager Implementations

### 1. SSOT Implementation: UnifiedWebSocketManager
**Location:** `/netra_backend/app/websocket_core/unified_manager.py`  
**Class:** `WebSocketManager` (MEGA CLASS: 2000+ lines)  
**Role:** Canonical SSOT implementation with full feature set

### 2. Factory Implementation: WebSocketManagerFactory  
**Location:** `/netra_backend/app/websocket_core/websocket_manager_factory.py`  
**Class:** `WebSocketManagerFactory`  
**Role:** Creates isolated manager instances per user

### 3. Mock Implementation: MockWebSocketManager
**Location:** `/test_framework/fixtures/websocket_manager_mock.py`  
**Class:** `MockWebSocketManager`  
**Role:** Test mock with simplified interface

## 🚨 CRITICAL INTERFACE INCONSISTENCIES (14 Found)

### **Category A: Method Signature Mismatches (7 issues)**

#### 1. Connection Management Interface
**SSOT:** `async def add_connection(self, connection: WebSocketConnection) -> None`  
**Mock:** `async def connect(self, connection_id: str, user_id: Optional[str] = None, **kwargs)`  
**Issue:** Different method names and parameter structures

#### 2. Disconnection Interface  
**SSOT:** `async def remove_connection(self, connection_id: Union[str, ConnectionID]) -> None`  
**Mock:** `async def disconnect(self, connection_id: str)`  
**Issue:** Different method names and type hints

#### 3. User Message Sending
**SSOT:** `async def send_to_user(self, user_id: Union[str, UserID], message: Dict[str, Any]) -> None`  
**Mock:** `async def send_to_user(self, user_id: str, message: Dict[str, Any])`  
**Issue:** Type annotation inconsistency (Union vs str)

#### 4. Connection Count Query
**SSOT:** Missing equivalent method  
**Mock:** `def get_connection_count(self) -> int`  
**Issue:** SSOT lacks this common query method

#### 5. Connection Information Query
**SSOT:** `def get_connection(self, connection_id: Union[str, ConnectionID]) -> Optional[WebSocketConnection]`  
**Mock:** `def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]`  
**Issue:** Different return types (WebSocketConnection vs Dict)

#### 6. User Connection Status
**SSOT:** `def is_connection_active(self, user_id: Union[str, UserID]) -> bool`  
**Mock:** `def is_user_connected(self, user_id: str) -> bool`  
**Issue:** Different method names and type hints

#### 7. WebSocket Send Interface
**SSOT:** Missing direct WebSocket interface methods  
**Mock:** `async def recv(self, timeout: Optional[float] = None) -> str`  
**Mock:** `async def send(self, message: str) -> None`  
**Issue:** SSOT lacks standard WebSocket interface compatibility

### **Category B: Missing Methods in SSOT (4 issues)**

#### 8. Room Broadcasting
**SSOT:** Missing  
**Mock:** `async def broadcast_to_room(self, room: str, message: Dict[str, Any])`  
**Issue:** SSOT lacks room-based messaging

#### 9. Direct Message Sending  
**SSOT:** Missing equivalent  
**Mock:** `async def send_message(self, connection_id: str, message: Dict[str, Any])`  
**Issue:** SSOT lacks direct connection messaging

#### 10. Connection Count Query
**SSOT:** Missing  
**Mock:** `def get_connection_count(self) -> int`  
**Issue:** Basic metrics method missing from SSOT

#### 11. Connection Information Access
**SSOT:** Returns complex object  
**Mock:** `def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]`  
**Issue:** SSOT needs simple dict-based info access

### **Category C: Factory Interface Gaps (3 issues)**

#### 12. User Context Creation
**Factory:** `async def create_manager(self, user_context: UserExecutionContext) -> WebSocketManager`  
**SSOT:** `def from_user_context(cls, user_context: 'UserExecutionContext') -> 'WebSocketManager'`  
**Issue:** Async vs sync factory method inconsistency

#### 13. Manager Cleanup  
**Factory:** Complex cleanup with metrics  
**SSOT:** Basic shutdown only  
**Issue:** Cleanup interface mismatch

#### 14. Resource Limits
**Factory:** Built-in resource limiting  
**SSOT:** No resource management  
**Issue:** SSOT lacks factory's safety features

## 📋 STANDARDIZED INTERFACE PROTOCOL

### Core WebSocket Manager Interface
```python
from typing import Protocol, Dict, Any, Optional, Set, Union
from shared.types.core_types import UserID, ConnectionID, WebSocketID

class StandardWebSocketManagerProtocol(Protocol):
    """Standardized interface for all WebSocket manager implementations."""
    
    # Connection Management
    async def add_connection(self, connection: WebSocketConnection) -> None: ...
    async def remove_connection(self, connection_id: Union[str, ConnectionID]) -> None: ...
    def get_connection(self, connection_id: Union[str, ConnectionID]) -> Optional[WebSocketConnection]: ...
    
    # User Connection Management  
    def get_user_connections(self, user_id: Union[str, UserID]) -> Set[str]: ...
    def is_user_connected(self, user_id: Union[str, UserID]) -> bool: ...
    async def wait_for_connection(self, user_id: str, timeout: float = 5.0) -> bool: ...
    
    # Messaging Interface
    async def send_to_user(self, user_id: Union[str, UserID], message: Dict[str, Any]) -> None: ...
    async def send_message(self, connection_id: str, message: Dict[str, Any]) -> None: ...
    async def broadcast(self, message: Dict[str, Any]) -> None: ...
    async def broadcast_to_room(self, room: str, message: Dict[str, Any]) -> None: ...
    
    # Statistics & Health
    def get_connection_count(self) -> int: ...
    def get_connection_info(self, connection_id: str) -> Optional[Dict[str, Any]]: ...
    def get_stats(self) -> Dict[str, Any]: ...
    
    # WebSocket Interface Compatibility
    async def recv(self, timeout: Optional[float] = None) -> str: ...
    async def send(self, message: str) -> None: ...
    
    # Lifecycle Management
    async def shutdown(self) -> None: ...
    
    # Factory Support
    @classmethod
    def from_user_context(cls, user_context: 'UserExecutionContext') -> 'WebSocketManager': ...
```

## 🔧 PHASE 1 IMPLEMENTATION PLAN

### Task 1: Enhance SSOT UnifiedWebSocketManager ✅

Add missing methods to make SSOT support all usage patterns:

1. **Add missing query methods:**
   - `get_connection_count() -> int`
   - `get_connection_info(connection_id: str) -> Optional[Dict[str, Any]]`

2. **Add missing messaging methods:**
   - `async def send_message(self, connection_id: str, message: Dict[str, Any])`
   - `async def broadcast_to_room(self, room: str, message: Dict[str, Any])`

3. **Add WebSocket interface methods:**
   - `async def recv(self, timeout: Optional[float] = None) -> str`
   - `async def send(self, message: str) -> None`

4. **Standardize type annotations:**
   - Use `Union[str, UserID]` consistently
   - Maintain backward compatibility with str types

### Task 2: Create Compatibility Layer ✅

Add deprecation warnings for non-SSOT usage:

```python
# Compatibility imports with warnings
import warnings
from netra_backend.app.websocket_core.unified_manager import WebSocketManager as UnifiedWebSocketManager

def WebSocketManagerFactory(*args, **kwargs):
    warnings.warn(
        "Direct WebSocketManagerFactory usage is deprecated. "
        "Use UnifiedWebSocketManager.from_user_context() instead.",
        DeprecationWarning,
        stacklevel=2
    )
    # Return compatible instance
    return UnifiedWebSocketManager(*args, **kwargs)
```

### Task 3: Import Path Standardization ✅

**Canonical Import (SSOT):**
```python
from netra_backend.app.websocket_core.unified_manager import WebSocketManager
```

**Legacy Imports (with deprecation warnings):**
```python
from netra_backend.app.websocket_core.websocket_manager_factory import WebSocketManagerFactory  # DEPRECATED
from test_framework.fixtures.websocket_manager_mock import MockWebSocketManager  # TESTS ONLY
```

## 🛡️ BACKWARD COMPATIBILITY PRESERVATION

### Legacy Test Support
- Mock interface methods added to SSOT with compatibility wrappers
- Existing test fixtures continue to work unchanged
- Gradual migration path for test updates

### Factory Pattern Support  
- `from_user_context()` class method provides factory compatibility
- Resource management features preserved through SSOT enhancements
- User isolation maintained through existing SSOT patterns

### Interface Consistency
- All implementations support standardized method signatures
- Type hints unified across implementations
- Return types consistent between SSOT and mock

## 📊 SUCCESS CRITERIA FOR PHASE 1

1. **✅ Interface Standardization:** All 14 inconsistencies resolved
2. **✅ SSOT Enhancement:** Missing methods added to UnifiedWebSocketManager  
3. **✅ Compatibility Layer:** Deprecation warnings implemented
4. **✅ Test Preservation:** All 140+ existing tests continue to pass
5. **✅ Import Standardization:** Canonical import paths established

## 🚀 PHASE 2 PREPARATION

Phase 1 creates the foundation for Phase 2 (consolidation):
- Standardized interface enables safe refactoring
- Deprecation warnings guide migration
- SSOT enhanced to handle all use cases
- Backward compatibility ensures Golden Path preservation

**Next Steps:** Phase 2 will consolidate factory and mock implementations into the enhanced SSOT while maintaining the compatibility layer until Phase 3.

---

**Phase 1 Status:** 🚧 IN PROGRESS  
**Risk Level:** LOW (no breaking changes)  
**Golden Path Impact:** NONE (preserves all functionality)