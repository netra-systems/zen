# SSOT-incomplete-migration-WebSocket Manager fragmentation blocking Golden Path

**GitHub Issue:** [#1036](https://github.com/netra-systems/netra-apex/issues/1036)  
**Progress Tracker:** SSOT-incomplete-migration-WebSocket Manager fragmentation blocking Golden Path.md  
**Status:** DISCOVERED - Step 0 Complete

## Issue Summary
- **Critical Legacy SSOT Violation:** WebSocket Manager fragmentation with multiple implementations
- **Business Impact:** $500K+ ARR at risk due to Golden Path blockage
- **Root Cause:** Incomplete migration to SSOT pattern, multiple aliases preventing proper factory pattern

## Discovery Results (Step 0) ✅
- **Multiple WebSocket Manager implementations found:**
  - `/netra_backend/app/websocket_core/websocket_manager.py` (Line 114)
  - `/netra_backend/app/websocket_core/unified_manager.py` (Private implementation)
  - Multiple compatibility aliases: `UnifiedWebSocketManager`, `WebSocketConnectionManager`

- **318 test files** dedicated to WebSocket manager issues indicate systemic fragmentation
- **Golden Path Impact:** WebSocket race conditions prevent reliable agent event delivery
- **Multi-User Security Risk:** Factory pattern violations cause user isolation failures

## Test Discovery and Planning (Step 1) - PENDING
### 1.1 Existing Tests to Discover:
- [ ] Find WebSocket manager tests protecting against breaking changes
- [ ] Identify tests for the 5 critical WebSocket events
- [ ] Locate multi-user isolation tests
- [ ] Find Golden Path integration tests

### 1.2 Test Plan to Create:
- [ ] Unit tests for single SSOT WebSocket manager
- [ ] Integration tests for factory pattern enforcement  
- [ ] E2E staging tests for all 5 WebSocket events
- [ ] Multi-user isolation validation tests

## Test Execution (Step 2) - PENDING
- [ ] Create new SSOT validation tests (20% of work)
- [ ] Run tests without Docker (unit, integration non-docker, e2e staging)
- [ ] Validate failing tests reproduce SSOT violations

## Remediation Planning (Step 3) - PENDING
- [ ] Plan elimination of WebSocket manager aliases
- [ ] Plan factory pattern enforcement strategy
- [ ] Plan migration of existing code to single SSOT

## Remediation Execution (Step 4) - PENDING
- [ ] Remove `UnifiedWebSocketManager` alias
- [ ] Remove `WebSocketConnectionManager` alias
- [ ] Consolidate to single WebSocket manager SSOT
- [ ] Enforce factory pattern for user isolation

## Test Fix Loop (Step 5) - PENDING
- [ ] Run all existing tests and ensure they pass
- [ ] Fix any breaking changes introduced
- [ ] Validate Golden Path functionality
- [ ] Run startup tests (non-Docker)

## PR Creation (Step 6) - PENDING
- [ ] Create pull request with SSOT improvements
- [ ] Link to issue #1036 for automatic closure
- [ ] Ensure all tests pass before PR creation

## Success Criteria
- [ ] Single WebSocket manager class with one import path
- [ ] Factory pattern enforced for user isolation  
- [ ] All 5 critical WebSocket events reliably delivered
- [ ] Golden Path user flow operational without race conditions
- [ ] 318 WebSocket-related test files consolidated or passing

## Notes
- Focus on Golden Path functionality - users login → get AI responses
- WebSocket events serve chat functionality (90% of platform value)
- Must maintain $500K+ ARR chat system reliability