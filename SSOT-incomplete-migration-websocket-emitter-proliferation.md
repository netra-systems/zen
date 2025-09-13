# SSOT-incomplete-migration-websocket-emitter-proliferation.md

**GitHub Issue**: https://github.com/netra-systems/netra-apex/issues/679
**Priority**: P0 CRITICAL  
**Status**: DISCOVERY COMPLETE - PLANNING TESTS

## Problem Summary
Multiple WebSocket emitter implementations causing Golden Path failures:
- Events lost or delivered to wrong users
- Race conditions in Cloud Run WebSocket handshake  
- Silent chat failures breaking core business value ($500K+ ARR risk)

## SSOT Violation Details
Found 4 competing WebSocket emitter implementations:

1. **UserWebSocketEmitter** - `/netra_backend/app/services/websocket_bridge_factory.py:343`
2. **UserWebSocketEmitter** - `/netra_backend/app/agents/supervisor/agent_instance_factory.py:55`  
3. **UnifiedWebSocketEmitter** - `/netra_backend/app/websocket_core/unified_emitter.py:53` ← **SSOT TARGET**
4. **UserWebSocketEmitter** - `/netra_backend/app/services/user_websocket_emitter.py:32`

## Phase 0: Discovery ✅ COMPLETE

## Phase 1: Test Discovery & Planning 🔄 IN PROGRESS

### 1.1 DISCOVER EXISTING: Collection of existing tests protecting WebSocket functionality ✅ COMPLETE
- [x] **180+ WebSocket-related test files** discovered protecting $500K+ ARR
- [x] **Primary Mission Critical**: `tests/mission_critical/test_websocket_agent_events_suite.py` (140KB comprehensive suite)
- [x] **Emitter-Specific Tests**: 6 dedicated tests in `tests/mission_critical/websocket_emitter_consolidation/`
- [x] **Integration Tests**: 60+ files covering service coordination  
- [x] **E2E Tests**: 40+ files covering Golden Path validation
- [x] **Unit Tests**: 30+ files for component testing
- [x] **Real Services**: All mission critical tests use real WebSocket connections (no mocks)
- [x] **Business Protection**: All 5 business-critical events covered (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)

### 1.2 PLAN ONLY: Required test updates and new tests
- [ ] Plan failing tests to reproduce SSOT violation
- [ ] Design tests for SSOT consolidation validation
- [ ] Plan post-refactor test validation

## Phase 2: Execute Test Plan (20% new SSOT tests)
- [ ] Create failing tests demonstrating SSOT violation
- [ ] Implement WebSocket emitter SSOT validation tests
- [ ] Run non-docker tests only

## Phase 3: Plan SSOT Remediation 
- [ ] Plan migration to UnifiedWebSocketEmitter
- [ ] Plan removal of duplicate implementations
- [ ] Plan backwards compatibility strategy

## Phase 4: Execute SSOT Remediation
- [ ] Migrate all usage to UnifiedWebSocketEmitter
- [ ] Remove duplicate emitter implementations
- [ ] Update imports and dependencies

## Phase 5: Test Fix Loop
- [ ] Run all tests in tracking document
- [ ] Fix any breaking changes
- [ ] Ensure system stability maintained

## Phase 6: PR and Closure
- [ ] Create PR with SSOT consolidation
- [ ] Link to close issue #679
- [ ] Validate Golden Path works end-to-end

## Notes
- Focus on UnifiedWebSocketEmitter as the SSOT implementation
- Must maintain chat functionality during migration
- Priority: Golden Path user flow must work