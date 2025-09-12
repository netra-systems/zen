# SSOT-incomplete-migration-WebSocket Manager Factory Pattern Fragmentation Blocking Golden Path

**GitHub Issue**: [#514](https://github.com/netra-systems/netra-apex/issues/514)  
**Priority**: P0 - CRITICAL  
**Status**: IN PROGRESS - Step 0 Complete  
**Created**: 2025-09-12

## SSOT Violation Summary

### Issue Description
WebSocket management system has fragmented into multiple competing patterns with deprecated factory methods causing critical Golden Path failures blocking users from receiving AI responses.

### Business Impact
- 🚨 **BLOCKING**: Users cannot receive AI responses due to WebSocket connection failures  
- ⚠️ **STAGING WARNINGS**: Deprecated factory pattern causing GCP deployment warnings
- 🔒 **USER ISOLATION**: Factory inconsistencies breaking multi-tenant security
- ⚡ **RACE CONDITIONS**: Multiple initialization paths causing 1011 handshake errors

### Files Requiring SSOT Consolidation
- `/netra_backend/app/websocket_core/websocket_manager.py` (SSOT target)
- `/netra_backend/app/websocket_core/unified_manager.py` (Implementation)  
- `/netra_backend/app/websocket_core/websocket_manager_factory.py` (DEPRECATED)
- `/netra_backend/app/websocket_core/manager.py` (Compatibility layer)

## Progress Tracking

### ✅ Step 0: SSOT AUDIT - COMPLETE
- [x] Conducted comprehensive SSOT audit of websockets, auth, application
- [x] Identified TOP 3 critical SSOT violations
- [x] Prioritized WebSocket Manager Factory Pattern as P0 critical
- [x] Created GitHub Issue #514
- [x] Created progress tracking file (this document)

### 🔄 Step 1: DISCOVER AND PLAN TEST - IN PROGRESS
- [ ] 1.1 DISCOVER EXISTING: Find collection of existing tests protecting against WebSocket SSOT breaking changes
- [ ] 1.2 PLAN ONLY: Plan for update/creation of unit, integration, e2e tests focused on SSOT refactor

### ⏳ Step 2: EXECUTE TEST PLAN - PENDING
- [ ] Execute 20% new SSOT tests for WebSocket manager consolidation

### ⏳ Step 3: PLAN REMEDIATION - PENDING
- [ ] Plan SSOT remediation implementation

### ⏳ Step 4: EXECUTE REMEDIATION - PENDING
- [ ] Execute SSOT consolidation plan

### ⏳ Step 5: TEST FIX LOOP - PENDING
- [ ] Prove changes maintain system stability
- [ ] Run and fix all test cases
- [ ] Complete up to 10 cycles until all tests pass

### ⏳ Step 6: PR AND CLOSURE - PENDING
- [ ] Create Pull Request
- [ ] Cross-link to close issue #514

## SSOT Consolidation Plan

### Phase 1: Eliminate Deprecated Factory Usage
**Target**: Remove `get_websocket_manager_factory()` usage
- Identify all current usage locations
- Replace with unified pattern
- Update imports to use SSOT pattern

### Phase 2: Consolidate Creation Pattern  
**Target**: All creation through `get_websocket_manager()`
- Standardize creation interface
- Remove competing patterns
- Ensure user context isolation

### Phase 3: Remove Compatibility Layers
**Target**: Enforce single SSOT pattern
- Remove deprecated factory methods
- Clean up compatibility wrappers
- Update documentation

### Phase 4: Validation
**Target**: Verify fixes
- Test user isolation maintained
- Verify race conditions resolved
- Confirm staging warnings eliminated

## Success Criteria  
- ✅ Zero staging deployment warnings
- ✅ Single WebSocket creation pattern enforced
- ✅ User isolation maintained across all operations
- ✅ Golden Path functionality: Login → AI response works consistently

## Next Actions
1. Spawn subagent for Step 1.1 - Discover existing WebSocket tests
2. Spawn subagent for Step 1.2 - Plan test strategy for SSOT consolidation