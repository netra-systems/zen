# SSOT Incomplete Migration: Message Router Fragmentation Blocking Golden Path

**GitHub Issue:** [#1056](https://github.com/netra-systems/netra-apex/issues/1056)
**Created:** 2025-09-14
**Priority:** P0 - CRITICAL Golden Path Blocker
**Status:** DISCOVERY COMPLETE - Moving to Test Planning

## 🎯 Mission Critical Business Impact
- **Golden Path Blocked:** Users cannot reliably receive AI responses
- **Revenue Risk:** $500K+ ARR dependent on reliable agent communication
- **Business Function:** Message routing fragmentation preventing chat functionality

## 🔍 SSOT Violation Discovery (COMPLETED)

### Primary Evidence Found
**Three MessageRouter Implementations Discovered:**
1. **Compatibility Layer:** `netra_backend/app/agents/message_router.py`
2. **Test Implementation:** `netra_backend/app/core/message_router.py`
3. **Canonical Expected:** `netra_backend/app/websocket_core/handlers.py`

### Impact Analysis
- **Routing Ambiguity:** Multiple routers handling same message types differently
- **Import Path Violations:** Tests importing from incompatible locations
- **Test Infrastructure Confusion:** Different routers in different contexts
- **Golden Path Blocking:** No clear authority for agent communication routing

### Code Evidence
```python
# File 1: Compatibility bridge pattern
from netra_backend.app.websocket_core.handlers import MessageRouter

# File 2: Full duplicate implementation
class MessageRouter:
    def __init__(self):
        self.routes: Dict[str, List[Callable]] = {}
        # Entire routing logic duplicated
```

## 📋 Progress Tracking

### ✅ Step 0: SSOT AUDIT (COMPLETED)
- [x] Discovered message router fragmentation
- [x] Created GitHub Issue #1056
- [x] Created progress tracking file
- [x] Initial commit completed

### 🔄 Step 1: DISCOVER AND PLAN TESTS (IN PROGRESS)
- [ ] Find existing tests protecting MessageRouter functionality
- [ ] Plan new SSOT validation tests
- [ ] Identify test gaps for message routing consolidation
- [ ] Document test execution strategy (non-docker only)

### ⏳ Step 2: EXECUTE TEST PLAN (PENDING)
- [ ] Create 20% new SSOT tests
- [ ] Run failing tests to prove violation
- [ ] Validate test coverage for routing consolidation

### ⏳ Step 3: PLAN REMEDIATION (PENDING)
- [ ] Design SSOT MessageRouter consolidation
- [ ] Plan import path standardization
- [ ] Define compatibility layer approach

### ⏳ Step 4: EXECUTE REMEDIATION (PENDING)
- [ ] Implement single canonical MessageRouter
- [ ] Update all import paths
- [ ] Create compatibility adapters

### ⏳ Step 5: TEST FIX LOOP (PENDING)
- [ ] Run all affected tests
- [ ] Fix any breaking changes
- [ ] Ensure system stability

### ⏳ Step 6: PR AND CLOSURE (PENDING)
- [ ] Create pull request
- [ ] Link to close issue #1056
- [ ] Final validation

## 🎯 SSOT Solution Design

### Target Architecture
- **Single Canonical:** `netra_backend/app/websocket_core/handlers.py` (MessageRouter)
- **Import Standardization:** All consumers use same import path
- **Test Unification:** Single MessageRouter for all test contexts
- **Backward Compatibility:** Adapter pattern for migration safety

### Success Criteria
- [ ] Single MessageRouter implementation (SSOT compliance)
- [ ] All Golden Path message routing tests passing
- [ ] No duplicate routing logic
- [ ] Unified import paths across codebase
- [ ] Test infrastructure alignment complete

## 📚 Documentation References
- **Primary:** CLAUDE.md Golden Path Priority #1
- **Architecture:** SSOT Import Registry for canonical paths
- **Testing:** Non-docker testing strategy (unit, integration, e2e staging)
- **Business:** WebSocket agent integration critical for chat value

---
**Next Actions:** Spawn subagent for Step 1 - Discover and Plan Tests