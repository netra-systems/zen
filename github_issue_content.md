## Business Impact
WebSocket import fragmentation blocks Golden Path - users unable to receive real-time AI responses ($500K+ ARR impact).

## Technical Problem  
25+ files using deprecated websocket_manager_factory pattern causing race conditions and initialization failures in production.

## Files Affected
- netra_backend/app/services/agent_websocket_bridge.py (CRITICAL - Line 3229)
- netra_backend/app/factories/websocket_bridge_factory.py
- netra_backend/app/factories/tool_dispatcher_factory.py
- netra_backend/app/admin/corpus/compatibility.py
- netra_backend/app/services/websocket/quality_validation_handler.py

## Proposed Solution
**Phase 1:** Replace deprecated factory imports
```python
# ❌ VIOLATION (Deprecated)
from netra_backend.app.websocket_core.websocket_manager_factory import create_websocket_manager

# ✅ CORRECT (SSOT Canonical)  
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
```

**Phase 2:** Validate SSOT compliance across all WebSocket integrations
**Phase 3:** Remove deprecated factory module entirely

## Success Criteria
- [ ] Zero files using websocket_manager_factory imports
- [ ] All WebSocket manager access through canonical SSOT path
- [ ] Mission critical WebSocket tests passing: python tests/mission_critical/test_websocket_agent_events_suite.py
- [ ] Golden Path user flow operational end-to-end