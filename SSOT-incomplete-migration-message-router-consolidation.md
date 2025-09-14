# SSOT-incomplete-migration-message-router-consolidation

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/1125  
**Created:** 2025-09-14  
**Status:** DISCOVERY COMPLETE  
**Priority:** P0 - CRITICAL

## **SSOT Violation Summary**

### **Critical Issue: Multiple MessageRouter Implementations**
Three different MessageRouter implementations causing routing conflicts and blocking Golden Path:

1. **DEPRECATED:** `/netra_backend/app/core/message_router.py` 
2. **COMPATIBILITY:** `/netra_backend/app/services/message_router.py`
3. **CANONICAL SSOT:** `/netra_backend/app/websocket_core/handlers.py`

### **Business Impact**
- **Golden Path Blocked:** Users login but cannot get AI responses
- **Revenue Risk:** $500K+ ARR chat functionality affected
- **User Experience:** Infinite loading, no agent responses

### **Technical Problems**
- Import confusion across tests and components
- Multiple routers processing same message simultaneously  
- Agent event loss when messages routed to wrong handler
- Race conditions in message processing
- User isolation failures

### **Additional SSOT Violations Discovered**
1. **WebSocket Manager Import Path Fragmentation** (HIGH severity)
2. **Agent Message Handler Duplication** (MEDIUM severity)

## **Work Progress**

### ✅ Phase 0: DISCOVERY COMPLETE
- [x] SSOT audit for message routing violations
- [x] GitHub issue created: #1125
- [x] Progress tracker created
- [x] Critical violations identified and prioritized

### ⏳ Phase 1: DISCOVER AND PLAN TEST
- [ ] Find existing tests protecting MessageRouter functionality
- [ ] Identify tests that will break during SSOT consolidation
- [ ] Plan new SSOT tests to validate consolidated implementation
- [ ] Document test strategy for regression prevention

### 📋 Phase 2: EXECUTE TEST PLAN
- [ ] Create failing tests that reproduce SSOT violations
- [ ] Create passing tests for desired SSOT state
- [ ] Run tests to establish baseline

### 📋 Phase 3: PLAN REMEDIATION
- [ ] Plan MessageRouter consolidation strategy
- [ ] Plan import path migration approach
- [ ] Plan backward compatibility during transition

### 📋 Phase 4: EXECUTE REMEDIATION
- [ ] Consolidate MessageRouter to single SSOT implementation
- [ ] Update all imports to canonical path
- [ ] Remove deprecated compatibility layers
- [ ] Update tests to use SSOT imports

### 📋 Phase 5: TEST FIX LOOP
- [ ] Run all existing tests - ensure no regressions
- [ ] Run new SSOT tests - ensure violations resolved
- [ ] Fix any test failures
- [ ] Validate startup sequence integrity

### 📋 Phase 6: PR AND CLOSURE
- [ ] Create PR with SSOT consolidation
- [ ] Cross-link issue for auto-closure
- [ ] Document migration for other developers

## **SSOT Remediation Strategy**

### **Target Architecture**
```
CANONICAL IMPORT: from netra_backend.app.websocket_core.handlers import MessageRouter
```

### **Files to Modify**
- Remove: `/netra_backend/app/core/message_router.py`
- Remove: `/netra_backend/app/services/message_router.py`
- Update: All test files importing from deprecated paths
- Update: Any services using compatibility layer imports

### **Test Strategy**
- Focus on integration tests using MessageRouter
- Test WebSocket message routing end-to-end
- Test agent message handling workflows
- Validate no message loss during routing

### **Migration Safety**
- Maintain backward compatibility during transition
- Use feature flags if needed for gradual rollout
- Validate all existing tests continue passing
- Ensure no breaking changes to public APIs

## **Next Actions**
1. Spawn subagent for Phase 1: Discover and plan tests
2. Continue through systematic SSOT gardener process
3. Maintain focus on Golden Path protection