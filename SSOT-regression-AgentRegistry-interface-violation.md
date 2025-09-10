# SSOT-regression-AgentRegistry-interface-violation.md

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/215
**Status:** In Progress - Discovery Complete
**Priority:** CRITICAL - Golden Path Blocker

## Issue Summary
AgentRegistry interface violation between child and parent class causing WebSocket handshake race conditions that block Golden Path user flow (login → AI responses).

## Technical Details
- **File:** `netra_backend/app/agents/supervisor/agent_registry.py:263`
- **Class:** `class AgentRegistry(UniversalAgentRegistry)`
- **Method:** `set_websocket_manager()` (lines 631-675)
- **Violation:** Liskov Substitution Principle - passing WebSocketManager objects to parent expecting AgentWebSocketBridge objects

## Business Impact
- **Revenue Risk:** $500K+ ARR dependency on chat functionality
- **User Experience:** 5 business-critical WebSocket events fail to deliver
- **System Stability:** Race conditions in Cloud Run environments

## Discovery Phase Complete ✅
- [x] Identified critical SSOT violation in AgentRegistry
- [x] Created GitHub issue #215
- [x] Documented interface contract violation
- [x] Assessed Golden Path impact

## Test Discovery and Planning Phase Complete ✅
- [x] **Existing Test Inventory:** 26 AgentRegistry test files, 1,085+ WebSocket integration tests
- [x] **Critical Gap Found:** Primary unit test file has PLACEHOLDER TESTS ONLY (0% coverage)
- [x] **Test Strategy Planned:** 20% new SSOT tests, 60% existing test enhancement, 20% validation
- [x] **Interface Violation Reproduction:** Plan for tests that fail before fix, pass after
- [x] **Risk Assessment:** High-risk tests identified that will break during fix

## Key Test Files Discovered
- `test_agent_registry.py` - **CRITICAL:** All placeholder tests, 0% coverage
- `test_agent_registry_websocket_manager_integration.py` - 825 lines, good integration coverage
- `test_agent_registry_websocket_bridge.py` - 1,151 lines, designed to fail and expose gaps

## Test Execution Strategy
- **P0:** Create interface violation reproduction test (fail before fix, pass after)
- **P1:** Complete placeholder unit tests in `test_agent_registry.py`
- **P2:** Enhance integration tests with interface signature validation
- **Constraint:** No Docker tests, unit/integration (no docker)/E2E staging only

## Test Execution Phase Complete ✅
- [x] **Interface Violation Tests Created:** 3 new test files specifically targeting SSOT violations
- [x] **Tests FAIL as intended:** Reproducing exact interface contract violations
- [x] **Root Cause Confirmed:** Parameter type mismatch, constructor signature issues, LSP violations
- [x] **Test Files:** `test_agent_registry_interface_violation.py`, `test_ssot_interface_violations.py`, enhanced `test_agent_registry.py`

## Test Results Summary
- **✅ CRITICAL VIOLATION REPRODUCED:** `set_websocket_manager()` vs `set_websocket_bridge()` parameter type mismatch
- **✅ LSP VIOLATION DETECTED:** Constructor signature incompatibility prevents substitutability  
- **✅ INTERFACE CONTRACT BROKEN:** Child class cannot be used as parent class replacement
- **📊 Test Status:** All new SSOT tests FAIL (as intended) - ready for remediation validation

## Remediation Targets Identified
1. **P0:** Unify WebSocket interface - Create adapter between WebSocketManager and AgentWebSocketBridge
2. **P0:** Fix constructor signatures - Align parent and child constructor parameters
3. **P0:** Implement parent methods - Ensure proper interface method implementation

## Remediation Planning Phase Complete ✅
- [x] **Comprehensive analysis completed** of parent and child class interfaces
- [x] **Adapter pattern strategy designed** to bridge WebSocketManager ↔ AgentWebSocketBridge
- [x] **Backward compatibility preserved** - existing functionality maintained during transition
- [x] **Atomic implementation plan** - 4 phases with individual validation points
- [x] **Risk mitigation strategy** - rollback procedures and validation at each step

## Remediation Strategy Summary
- **✅ ADAPTER PATTERN:** Convert between WebSocketManager and AgentWebSocketBridge seamlessly
- **✅ INTERFACE UNIFICATION:** Implement both parent and child methods consistently
- **✅ CONSTRUCTOR FIX:** Proper parent class initialization with name parameter
- **✅ LSP COMPLIANCE:** Child class fully substitutable for parent class
- **🛡️ GOLDEN PATH PROTECTED:** All 5 critical WebSocket events preserved

## Implementation Phases Planned
1. **Phase 1:** Constructor signature alignment and parent initialization
2. **Phase 2:** WebSocket adapter implementation for type conversion
3. **Phase 3:** Interface method unification and delegation
4. **Phase 4:** Validation and cleanup of legacy patterns

## Next Steps
1. ~~DISCOVER AND PLAN TEST phase~~ ✅
2. ~~EXECUTE THE TEST PLAN phase~~ ✅
3. ~~PLAN REMEDIATION OF SSOT phase~~ ✅
4. EXECUTE THE REMEDIATION SSOT PLAN phase
5. ENTER TEST FIX LOOP phase
6. PR AND CLOSURE phase

## Progress Log
- **2025-01-09:** Discovery complete, identified interface violation as root cause
- **2025-01-09:** Test discovery complete, found 0% unit test coverage gap
- **2025-01-09:** Test execution complete, 3 test files created, all SSOT violations reproduced
- **2025-01-09:** Remediation planning complete, adapter pattern strategy designed