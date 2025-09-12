# WebSocket V3 SSOT Developer Guide

**Status**: ✅ V3 Migration Complete - V2 Legacy Cleanup Finished  
**Issue**: #447 - Remove V2 Legacy WebSocket Handler Pattern  
**Date**: 2025-09-12

---

## Quick Start - Using V3 WebSocket Patterns

### For New Development

**Always use the V3 SSOT patterns:**

```python
# ✅ CORRECT - V3 SSOT Import
from netra_backend.app.routes.websocket_ssot import (
    websocket_endpoint,
    websocket_health_check,
    get_websocket_config
)

# ✅ CORRECT - V3 Authentication
from netra_backend.app.websocket_core.unified_websocket_auth import (
    authenticate_websocket_ssot,
    get_websocket_authenticator
)

# ✅ CORRECT - V3 WebSocket Core
from netra_backend.app.websocket_core import (
    WebSocketManager,
    MessageRouter,
    get_websocket_manager
)
```

### Architecture Overview

**V3 SSOT Consolidation** - Single route replaces 4 competing implementations:

1. **websocket_ssot.py** - Main SSOT implementation (2,000+ lines)
   - Consolidates: websocket.py (3,166 lines), websocket_factory.py (615 lines), 
   - websocket_isolated.py (410 lines), websocket_unified.py (15 lines)
   - **Modes**: main, factory, isolated, legacy (via query parameters)

2. **Backward Compatibility** - Old routes redirect to SSOT:
   - `websocket.py` → `websocket_ssot.py` (main mode)  
   - `websocket_isolated.py` → `websocket_ssot.py` (isolated mode)
   - `websocket_factory.py` → `websocket_ssot.py` (factory mode)

---

## Critical Business Requirements (Non-Negotiable)

### Golden Path Preservation
- **Users login → get AI responses** - Complete end-to-end flow functional
- **5 Critical WebSocket Events** - ALL must be sent:
  1. `agent_started` - User sees agent began
  2. `agent_thinking` - Real-time reasoning display  
  3. `tool_executing` - Tool usage transparency
  4. `tool_completed` - Tool results display
  5. `agent_completed` - Response completion signal

### Security & Isolation
- **User Isolation** - Factory patterns prevent cross-user data leakage
- **Connection Scoping** - Each WebSocket connection isolated 
- **Authentication** - JWT validation on all WebSocket connections
- **Event Filtering** - Users only receive their own events

---

## Development Patterns

### WebSocket Route Usage

**Main Route (Default)**:
```python
# Handles majority of production traffic
GET /ws?mode=main&user_id={user_id}&thread_id={thread_id}
```

**Factory Mode (User Isolation)**:
```python
# For high-isolation requirements  
GET /ws?mode=factory&user_id={user_id}&isolation_level=strict
```

**Isolated Mode (Connection Scoped)**:
```python
# For maximum security
GET /ws?mode=isolated&connection_scope=true
```

### Authentication Integration

```python
from netra_backend.app.websocket_core.unified_websocket_auth import authenticate_websocket_ssot

async def your_websocket_handler(websocket: WebSocket):
    # V3 authentication (handles all modes)
    auth_result = await authenticate_websocket_ssot(
        websocket=websocket,
        mode="main",  # or "factory", "isolated", "legacy" 
        user_context=user_context
    )
```

### Event Emission

```python
from netra_backend.app.websocket_core import get_websocket_manager

async def emit_agent_events(user_context):
    ws_manager = get_websocket_manager(user_context)  # V3 factory pattern
    
    # Critical events (ALL required for business value)
    await ws_manager.emit_event("agent_started", {"message": "AI processing begun"})
    await ws_manager.emit_event("agent_thinking", {"thoughts": "Analyzing request..."})
    await ws_manager.emit_event("tool_executing", {"tool": "data_analyzer", "status": "running"})
    await ws_manager.emit_event("tool_completed", {"tool": "data_analyzer", "result": "..."})
    await ws_manager.emit_event("agent_completed", {"response": "Final AI response", "complete": True})
```

---

## What Changed from V2 → V3

### ✅ Preserved (No Changes Needed)
- **Business Logic** - All chat functionality works identically
- **Client Integration** - Frontend WebSocket connections unchanged  
- **Authentication Flow** - JWT validation preserved
- **Event Structure** - All 5 critical events maintain same format
- **User Experience** - No user-visible changes

### 🔄 Updated (Internal Architecture)
- **Route Consolidation** - 4 routes → 1 SSOT route with modes
- **Import Paths** - Old imports redirect to V3 SSOT automatically
- **Factory Patterns** - Enhanced user isolation implementation 
- **Authentication** - Unified auth pipeline supports all patterns
- **Error Handling** - Consolidated error patterns and recovery

### 🗑️ Removed (V2 Legacy)
- **V2 Migration Scripts** - Archived to `scripts/archived/`
- **V2 Test Patterns** - Obsolete tests moved to `tests/archived/`
- **Duplicate Code** - Eliminated SSOT violations (4,206 → 2,000 lines)

---

## Testing V3 WebSocket Functionality

### Mission Critical Tests
```bash
# Core business functionality validation
python tests/mission_critical/test_websocket_agent_events_suite.py
```

### Integration Testing  
```python
import pytest
from netra_backend.app.routes.websocket_ssot import websocket_endpoint

@pytest.mark.asyncio
async def test_v3_websocket_functionality():
    # Test all modes: main, factory, isolated
    # Verify all 5 critical events are emitted
    # Validate user isolation works
    pass
```

### Performance Validation
- **Latency**: < 100ms for event emission
- **Concurrent Users**: Support 10+ concurrent WebSocket connections
- **Resource Usage**: No memory leaks or connection buildup

---

## Migration Status & Archive

### ✅ Completed V2 → V3 Migration
- **Core Migration** - All production systems using V3 patterns  
- **Business Continuity** - $500K+ ARR chat functionality preserved
- **SSOT Compliance** - 99%+ SSOT violations resolved
- **Legacy Cleanup** - V2 references cleaned, migration scripts archived

### Archive Locations
- **Migration Scripts**: `scripts/archived/migrate_websocket_v2_*`
- **Legacy Tests**: `tests/archived/v2_legacy_validation.py`  
- **Documentation**: V2 references updated to reflect V3 completion

---

## Troubleshooting

### Common Issues

**"WebSocket connection failed"**:
- Check V3 authentication is configured correctly
- Ensure JWT tokens are valid and not expired
- Verify WebSocket mode parameter is correct

**"Missing WebSocket events"**: 
- Confirm all 5 critical events are being emitted in sequence
- Check user_context is properly passed to WebSocket manager
- Validate event filtering is not blocking events

**"User isolation not working"**:
- Use factory mode for high isolation requirements  
- Ensure UserExecutionContext includes correct user_id
- Check connection scoping configuration

### Debug Tools

```python
# V3 WebSocket health check
GET /ws/health

# V3 WebSocket configuration
GET /ws/config  

# V3 WebSocket statistics
GET /ws/stats
```

---

## Support & Maintenance

### Key Contacts
- **WebSocket V3 Architecture**: See `netra_backend/app/routes/websocket_ssot.py`
- **Authentication**: See `netra_backend/app/websocket_core/unified_websocket_auth.py` 
- **Issue Tracking**: GitHub Issue #447 (Complete)

### Documentation
- **V3 Implementation**: `netra_backend/app/routes/websocket_ssot.py` (comprehensive docs)
- **Migration Guide**: `docs/MIGRATION_PATHS_CONSOLIDATED.md`
- **Test Reports**: `docs/V2_LEGACY_WEBSOCKET_TEST_EXECUTION_REPORT.md`

**Status**: ✅ V3 WebSocket SSOT implementation is production-ready and fully operational.