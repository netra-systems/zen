# SSOT-incomplete-migration-WebSocket-Manager-Fragmentation-Blocks-Golden-Path

**GitHub Issue:** [#824](https://github.com/netra-systems/netra-apex/issues/824)
**Priority:** P0 CRITICAL
**Status:** 🔍 DISCOVERING & PLANNING TESTS
**Created:** 2025-01-13

## Problem Summary
Multiple WebSocketManager implementations create race conditions and initialization failures in the Golden Path user flow, causing silent failures of critical WebSocket events.

**Business Impact:** Blocks $500K+ ARR Golden Path functionality (users login → AI responses)

## Affected Files
- `/netra_backend/app/websocket_core/unified_manager.py:294` - UnifiedWebSocketManager (SSOT implementation)
- `/netra_backend/app/websocket_core/websocket_manager_factory.py:516` - WebSocketManagerFactory (Compatibility layer)
- `/netra_backend/app/websocket_core/protocols.py:606` - LegacyWebSocketManagerAdapter
- `/netra_backend/app/agents/supervisor/agent_registry.py:64` - WebSocketManagerAdapter

## Progress Tracking

### ✅ COMPLETED: Step 0 - SSOT Audit Discovery
- [x] Identified P0 critical WebSocket Manager fragmentation
- [x] Created GitHub issue #824 with proper P0/SSOT labels
- [x] Created progress tracking document (this file)
- [x] Initial analysis shows 4 different WebSocket manager implementations

### 🔄 IN PROGRESS: Step 1 - Discover & Plan Tests

#### 1.1 - DISCOVER EXISTING (In Progress)
**Goal:** Find existing tests protecting against breaking changes from SSOT refactor

**Test Discovery Status:**
- [ ] Locate existing WebSocket tests in test suite
- [ ] Identify tests covering Golden Path WebSocket event flow
- [ ] Document tests that must continue to pass after SSOT consolidation
- [ ] Find tests covering user isolation in WebSocket connections

**Key Test Files to Locate:**
- Mission critical: `tests/mission_critical/test_websocket_agent_events_suite.py`
- WebSocket state: `netra_backend/tests/critical/test_websocket_state_regression.py`
- E2E WebSocket: `tests/e2e/test_websocket_dev_docker_connection.py`
- Silent failures: `netra_backend/tests/integration/critical_paths/test_websocket_silent_failures.py`

#### 1.2 - PLAN ONLY (Pending)
**Goal:** Plan update/creation of unit, integration, e2e GCP staging tests

**Test Plan Strategy:**
- ~20% new SSOT validation tests
- ~60% existing test updates for compatibility
- ~20% new tests for SSOT violation reproduction (failing tests!)

**Test Categories to Plan:**
- [ ] Unit tests for WebSocketManager SSOT consolidation
- [ ] Integration tests (non-docker) for factory pattern consistency
- [ ] E2E GCP staging tests for Golden Path event delivery
- [ ] Failing tests to reproduce the SSOT violation

### 📋 UPCOMING STEPS
- [ ] Step 2: Execute Test Plan (20% NEW SSOT tests)
- [ ] Step 3: Plan SSOT Remediation
- [ ] Step 4: Execute SSOT Remediation
- [ ] Step 5: Test Fix Loop (Proof of Stability)
- [ ] Step 6: PR & Closure

## Remediation Plan Summary

### Phase 1: Consolidate to Single Factory Pattern (1-2 days)
- Establish `unified_manager.py` as ONLY WebSocketManager implementation
- Remove duplicate implementations in `protocols.py` and `agent_registry.py`
- Update imports to: `from netra_backend.app.websocket_core.websocket_manager import WebSocketManager`

### Phase 2: Eliminate Factory Redundancy (1 day)
- Remove `websocket_manager_factory.py` compatibility shim
- Remove `WebSocketManagerAdapter` classes
- Update Golden Path tests for direct instantiation

## Success Criteria
- [ ] All 5 critical WebSocket events deliver correctly (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- [ ] User isolation works in multi-user scenarios
- [ ] Golden Path user flow works reliably
- [ ] Tests pass: `python tests/mission_critical/test_websocket_agent_events_suite.py`
- [ ] SSOT compliance increases from current 84.4%
- [ ] No silent WebSocket failures in Golden Path

## Notes
- Focus on ATOMIC changes - one logical unit per commit
- Maintain backward compatibility during migration phases
- Use feature flags for gradual rollout if needed
- All changes must pass existing tests or update tests appropriately

---
*Last Updated: 2025-01-13 - Initial creation and Step 0 completion*