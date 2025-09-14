# SSOT-message-router-fragmentation

**GitHub Issue**: #1077  
**Priority**: P0 - Golden Path Blocker  
**Business Impact**: $500K+ ARR at Risk  
**Status**: STEP 0 COMPLETE - DISCOVERY PHASE DONE  

## Problem Summary
4 separate MessageRouter implementations causing routing conflicts and blocking Golden Path user flow (users login → get AI responses).

## Critical SSOT Violations Discovered

### 1. MOST CRITICAL: Multiple MessageRouter Implementations
**Files**:
- `/netra_backend/app/websocket_core/handlers.py:1208` - **SSOT TARGET**
- `/netra_backend/app/services/websocket/quality_message_router.py:36` - DUPLICATE
- `/netra_backend/app/core/message_router.py:55` - DUPLICATE

### 2. WebSocket Broadcast Function Triplication
**Files**:
- `/netra_backend/app/services/websocket_event_router.py:198` - `broadcast_to_user()` (singleton)
- `/netra_backend/app/services/user_scoped_websocket_event_router.py:234` - `broadcast_to_user()` (scoped)
- `/netra_backend/app/services/user_scoped_websocket_event_router.py:607` - `broadcast_user_event()` (standalone)

**POSITIVE**: SSOT solution exists: `/netra_backend/app/services/websocket_broadcast_service.py`

### 3. Tool Dispatcher Fragmentation
**Files**:
- `/netra_backend/app/core/tools/unified_tool_dispatcher.py` - **SSOT TARGET**
- `/netra_backend/app/tools/enhanced_dispatcher.py` - DUPLICATE
- Multiple other implementations

## Golden Path Impact
1. **Message Router Conflicts**: Users send chat → multiple routers compete → messages lost/duplicated
2. **Broadcast Fragmentation**: Agent responses → wrong broadcast → events reach wrong users
3. **Tool Dispatcher Race Conditions**: Agent tools → multiple dispatchers → tools fail

## Success Metrics
- [ ] 99.5%+ Golden Path reliability restored
- [ ] Zero cross-user event leakage  
- [ ] All 5 critical WebSocket events functional

## Process Status
- [x] Step 0: DISCOVERY COMPLETE
- [x] Step 1: Test Discovery and Planning - **COMPLETE**
- [ ] Step 2: Execute Test Plan
- [ ] Step 3: Plan SSOT Remediation
- [ ] Step 4: Execute Remediation
- [ ] Step 5: Test Fix Loop
- [ ] Step 6: PR and Closure

## STEP 1 RESULTS: Test Discovery and Planning ✅

### Existing Test Inventory (141 Tests Found)
**Mission Critical Tests**:
- `test_message_router_ssot_enforcement.py` - Primary SSOT enforcement 
- `test_websocket_agent_events_suite.py` - $500K+ ARR protection
- `test_message_router_ssot_compliance.py` - **BROKEN** (needs repair)

**Test Categories**:
- **Unit Tests**: 60+ tests covering core MessageRouter functionality
- **Integration Tests**: 25+ tests covering service integration  
- **E2E Tests**: 15+ tests covering Golden Path validation
- **SSOT Detection Tests**: Designed to FAIL initially, PASS after consolidation

### Test Update Plan
- **High Priority**: Fix broken SSOT compliance test
- **Updates Required**: ~25 tests need import/mock updates for SSOT consolidation
- **New Tests Needed**: ~25 tests (20% strategy) for SSOT validation

### Test Execution Strategy (Non-Docker)
- **Unit**: `python tests/unified_test_runner.py --category unit --no-docker`
- **Integration**: `python tests/unified_test_runner.py --category integration --no-docker --real-services`  
- **E2E Staging**: `python -m pytest tests/e2e/staging/ -k "message_router"`

**Key Insight**: Comprehensive test coverage protects $500K+ ARR chat functionality during SSOT consolidation.

---
**Last Updated**: 2025-09-14 Step 1 Complete