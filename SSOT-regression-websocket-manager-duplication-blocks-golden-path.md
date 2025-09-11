# SSOT Remediation: WebSocket Manager Duplication Blocks Golden Path

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/243
**Created:** 2025-09-10
**Status:** DISCOVERY COMPLETE

## Problem Summary
WebSocket manager SSOT breakdown with multiple conflicting implementations blocking golden path user flow (users login → get AI responses).

## Key Files Affected
- `netra_backend/app/websocket_core/manager.py` (Lines 3-4)
- `netra_backend/app/websocket_core/websocket_manager.py` (Line 37) 
- `netra_backend/app/websocket_core/unified_manager.py`

## SSOT Violation Details
1. **Circular Imports:** `manager.py` imports both `WebSocketManager` and `UnifiedWebSocketManager`
2. **Conflicting Aliases:** `websocket_manager.py` creates `WebSocketManager = UnifiedWebSocketManager`
3. **Race Conditions:** WebSocket handshake failures in Cloud Run environments

## Business Impact
- **BLOCKS:** Real-time agent communication events
- **PREVENTS:** Chat experience delivery (90% of platform value)
- **AFFECTS:** $500K+ ARR dependency on reliable chat functionality

## Process Status
- [x] 0) DISCOVER SSOT Issue - COMPLETE
- [x] 1) DISCOVER AND PLAN TEST - COMPLETE
- [x] 2) EXECUTE TEST PLAN - COMPLETE
- [ ] 3) PLAN REMEDIATION
- [ ] 4) EXECUTE REMEDIATION
- [ ] 5) TEST FIX LOOP
- [ ] 6) PR AND CLOSURE

## Test Discovery Results
- **2,722 total test files** containing WebSocket patterns
- **89 mission critical tests** protecting core functionality
- **95+ integration tests** for service coordination (no Docker)
- **48+ E2E tests** for complete workflow validation on GCP staging

## Test Strategy Plan (60% + 20% + 20%)
- **60% Existing Tests:** Update 45 key tests for SSOT compliance
- **20% New SSOT Tests:** Create 11 failing tests to catch regressions  
- **20% Validation Tests:** Create 11 tests proving SSOT fixes maintain stability

## Current SSOT Violations Confirmed
1. Multiple import paths: `manager.py`, `websocket_manager.py`, `unified_manager.py`
2. Alias confusion: `WebSocketManager = UnifiedWebSocketManager`
3. Inconsistent test patterns across 2,722 test files
4. Factory bypass in some test implementations

## New SSOT Test Creation Results
- **Target:** 11 new tests (20% of effort)
- **Delivered:** 18 new test methods across 7 test files (164% of goal)
- **Status:** Tests FAILING as expected (detecting current violations)

### Test Files Created:
- `tests/ssot/test_websocket_ssot_import_violations.py` (3 tests)
- `tests/ssot/test_websocket_ssot_factory_violations.py` (3 tests)
- `tests/ssot/test_websocket_ssot_integration_violations.py` (3 tests)
- `tests/ssot/test_websocket_ssot_regression_prevention.py` (2 tests)
- `tests/ssot/test_websocket_ssot_connection_lifecycle.py` (3 tests)
- `tests/ssot/test_websocket_ssot_event_ordering.py` (2 tests)
- `tests/ssot/test_websocket_ssot_configuration_violations.py` (2 tests)

### Key Violations Detected:
- 3+ different import paths for WebSocket managers work simultaneously
- Multiple factory patterns exist for creating managers
- Configuration drift across multiple sources
- Integration inconsistencies between WebSocket and agent systems

## Next Action
Plan SSOT remediation strategy for WebSocket manager consolidation.