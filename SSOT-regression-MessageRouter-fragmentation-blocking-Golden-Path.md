# SSOT-regression-MessageRouter-fragmentation-blocking-Golden-Path

**GitHub Issue**: [#1143](https://github.com/netra-systems/netra-apex/issues/1143)  
**Status**: DISCOVERING AND PLANNING  
**Priority**: P0 - CRITICAL GOLDEN PATH BLOCKER  
**Created**: 2025-09-14

## Executive Summary
MessageRouter SSOT fragmentation across 3 import paths causing Golden Path failures - users cannot reliably get AI responses due to message routing confusion and race conditions.

## SSOT Violation Analysis

### Critical Files Affected
1. **`netra_backend/app/core/message_router.py`** - Proxy implementation (DEPRECATED)
2. **`netra_backend/app/services/message_router.py`** - Compatibility layer (RE-EXPORT ONLY)  
3. **`netra_backend/app/websocket_core/handlers.py`** - Canonical SSOT (2000+ lines)

### Import Path Fragmentation
```python
# VIOLATION: Three different import paths for same functionality
from netra_backend.app.core.message_router import MessageRouter        # Proxy
from netra_backend.app.services.message_router import MessageRouter    # Re-export  
from netra_backend.app.websocket_core.handlers import MessageRouter    # SSOT Source
```

### Golden Path Impact
- User messages routed to wrong handlers
- Agent responses lost or misdirected  
- WebSocket events (agent_started, agent_thinking, etc.) fail to reach users
- Race conditions breaking real-time chat experience

## Process Status

### ✅ COMPLETED
- [x] 0) DISCOVER NEXT SSOT ISSUE - MessageRouter fragmentation identified as #1 priority
- [x] GitHub issue created: #1143
- [x] Progress tracker created

### 🔄 IN PROGRESS  
- [ ] 1) DISCOVER AND PLAN TEST

### 📋 TODO
- [ ] 1.1) DISCOVER EXISTING tests protecting MessageRouter functionality
- [ ] 1.2) PLAN NEW SSOT tests for post-remediation validation
- [ ] 2) EXECUTE THE TEST PLAN (20% new SSOT tests)
- [ ] 3) PLAN REMEDIATION OF SSOT
- [ ] 4) EXECUTE THE REMEDIATION SSOT PLAN  
- [ ] 5) ENTER TEST FIX LOOP
- [ ] 6) PR AND CLOSURE

## Business Impact
- **Revenue Risk**: $500K+ ARR chat functionality compromised
- **User Experience**: Real-time messaging degradation
- **Security Risk**: Potential message routing to wrong users

## Technical Details

### SSOT Target Architecture
- **Single Source**: `netra_backend.app.websocket_core.handlers.MessageRouter`
- **Remove**: Proxy implementations in core/ and services/
- **Update**: All import statements to use canonical path
- **Maintain**: User isolation and factory patterns

### Affected Components
- WebSocket event delivery system
- Agent execution message routing
- Tool execution response routing  
- Cross-service message coordination

## Next Steps
1. Spawn sub-agent to discover existing tests
2. Plan comprehensive test coverage for remediation
3. Execute SSOT consolidation with test validation

---
*Last Updated: 2025-09-14*  
*SSOT Gardener Progress Tracker*