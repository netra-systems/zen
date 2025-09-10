# SSOT WebSocket Manager Fragmentation - Golden Path Critical

**GitHub Issue:** #186 - [SSOT-recent-change] WebSocket manager fragmentation blocks golden path chat functionality  
**Status:** Discovery Complete - Moving to Test Planning  
**Priority:** P0 CRITICAL - Blocks Golden Path ($500K+ ARR Impact)

## Issue Summary
Multiple WebSocket manager implementations violating SSOT, causing authentication race conditions and chat functionality failures that block the core Golden Path (users login → get AI responses).

## Critical SSOT Violations Discovered

### 7 Different WebSocket Manager Classes Found:
1. `IsolatedWebSocketManager` (websocket_manager_factory.py)
2. `WebSocketManagerFactory` (websocket_manager_factory.py) 
3. `EmergencyWebSocketManager` (websocket_manager_factory.py)
4. `DegradedWebSocketManager` (websocket_manager_factory.py)
5. `UnifiedWebSocketManager` (unified_manager.py) - Claims to be SSOT
6. `WebSocketManagerAdapter` (migration_adapter.py) - Legacy
7. `WebSocketConnectionManager` (connection_manager.py) - Alias

### Primary File Paths:
- `/netra_backend/app/websocket_core/websocket_manager_factory.py` (PRIMARY VIOLATION)
- `/netra_backend/app/websocket_core/unified_manager.py` (INTENDED SSOT)
- `/netra_backend/app/websocket_core/migration_adapter.py` (LEGACY)
- `/netra_backend/app/websocket_core/connection_manager.py` (DUPLICATE)

### Golden Path Impact:
- **Authentication Race Conditions:** Multiple managers cause login failures
- **Agent Event Delivery Chaos:** 5 critical events delivered inconsistently
- **Silent WebSocket Failures:** User isolation broken
- **Chat Functionality:** 90% of business value at risk

## Process Status

### ✅ STEP 0: SSOT AUDIT COMPLETE
- P0 SSOT violation identified
- GitHub issue confirmed (#186)
- Local tracking document created

### ✅ STEP 1.1: DISCOVER EXISTING TESTS COMPLETE
**Comprehensive test discovery found extensive protection:**

**Mission Critical Tests (Business Value Protection):**
- `tests/mission_critical/test_websocket_agent_events_real.py` - All 5 WebSocket events with real services
- `tests/mission_critical/test_websocket_bridge_integration.py` - Bridge pattern integration
- `tests/mission_critical/test_websocket_integration_regression.py` - Regression protection

**SSOT Consolidation Tests (Interface Consistency):**
- `tests/unit/websocket_ssot/test_manager_interface_consistency.py` - Manager interface validation
- `tests/unit/websocket_ssot/test_manager_factory_consolidation.py` - Factory consolidation
- `tests/ssot/test_websocket_ssot_violations_reproduction.py` - SSOT violation reproduction

**Critical Tests That MUST Continue Passing:**
- All 5 WebSocket events delivered correctly
- Complete E2E chat flows preserved
- Multi-user isolation maintained
- Authentication integration working
- Performance benchmarks maintained

**Tests Expected to Initially Fail (by design):**
- Interface consistency tests (until unified)
- Factory consolidation tests (until consolidated)
- SSOT violation reproduction tests (until fixed)

### ✅ STEP 1.2: PLAN NEW SSOT TESTS COMPLETE
**Comprehensive test plan for 20% new SSOT validation tests:**

**Strategy:** 60% failing tests (prove violations), 40% stability tests (prove preservation)

**Phase 1 - Unit Tests (Proving Violations):**
1. `test_ssot_websocket_manager_single_source_truth.py` - FAIL→PASS (prove only 1 manager)
2. `test_websocket_manager_factory_consolidation_validation.py` - FAIL→PASS (unified factory)  
3. `test_websocket_manager_interface_unification.py` - FAIL→PASS (consistent interfaces)

**Phase 2 - Integration Tests (Regression Prevention):**
4. `test_websocket_ssot_regression_prevention.py` - FAIL→PASS (prevent future violations)
5. `test_websocket_manager_agent_integration_preservation.py` - PASS→PASS (preserve agent integration)
6. `test_websocket_manager_auth_integration_preservation.py` - PASS→PASS (preserve auth integration)

**Phase 3 - E2E Tests (Golden Path Protection):**
7. `test_websocket_golden_path_preservation.py` - PASS→PASS (preserve login→AI response flow)
8. `test_websocket_multi_user_isolation_preservation.py` - PASS→PASS (preserve user isolation)

**Execution Strategy:** NO DOCKER required - unit tests use static analysis, integration uses mocks, E2E uses staging GCP

### ⏳ UPCOMING STEPS:
- Step 2: Execute new SSOT test plan
- Step 3: Plan SSOT remediation 
- Step 4: Execute remediation
- Step 5: Test fix loop
- Step 6: PR and closure

## Technical Notes
- Root cause: Incomplete SSOT migration to UnifiedWebSocketManager
- Factory pattern violations creating multiple sources of truth
- 140+ tests affected across mission critical, integration, E2E categories
- Interface inconsistencies with up to 33 method differences

## Business Justification
- **Segment:** Platform/Enterprise (core infrastructure)
- **Goal:** Stability/Retention (prevent $500K+ ARR loss)
- **Value Impact:** Enables reliable chat functionality (90% of platform value)
- **Revenue Impact:** Prevents customer churn from broken core experience