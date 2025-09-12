# SSOT Gardener Work in Progress: WebSocket Event Delivery SSOT Violations

**Issue**: [#567 SSOT-agent-execution-websocket-event-delivery-duplication-blocking-golden-path](https://github.com/netra-systems/netra-apex/issues/567)
**Priority**: P0 (MISSION CRITICAL)
**Status**: Step 0 COMPLETE - SSOT Audit Complete
**Created**: 2025-09-12
**Focus**: Agent events and execution SSOT violations blocking Golden Path

## Business Impact Summary
- **Revenue Risk**: $500K+ ARR dependent on reliable WebSocket agent events
- **Platform Impact**: 90% of business value depends on chat functionality  
- **Golden Path Status**: BLOCKED - Users cannot reliably receive AI responses
- **Critical Events at Risk**: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed

## SSOT Violations Discovered

### 1. 🚨 Duplicate WebSocket Notifier Implementations (P0)
- **SSOT**: `netra_backend/app/services/agent_websocket_bridge.py:3209` → class WebSocketNotifier
- **DUPLICATE**: `scripts/websocket_notifier_rollback_utility.py:21` → class WebSocketNotifier  
- **Impact**: Race conditions, missing agent events

### 2. 🚨 Execution Engine Factory Proliferation (P0)  
- **SSOT**: `netra_backend/app/agents/supervisor/execution_engine_factory.py`
- **DUPLICATE**: `netra_backend/app/core/managers/execution_engine_factory.py` (compatibility)
- **DUPLICATE**: `netra_backend/app/agents/execution_engine_unified_factory.py` (migration)
- **Impact**: Inconsistent agent execution contexts, user isolation failures

### 3. 🚨 WebSocket Bridge Factory Fragmentation (P0)
- **DEPRECATED**: `netra_backend/app/services/websocket_bridge_factory.py` 
- **SSOT ATTEMPT**: `netra_backend/app/factories/websocket_bridge_factory.py`
- **Impact**: Event delivery failures, bridge adapter inconsistencies

### 4. 🚨 WebSocket Manager Interface Duplication (P0)
- **SSOT**: `netra_backend/app/websocket_core/unified_manager.py`
- **LEGACY**: `netra_backend/app/websocket_core/websocket_manager.py` (compatibility)
- **LEGACY**: `netra_backend/app/websocket_core/manager.py` (legacy)
- **Impact**: Connection state fragmentation, WebSocket event loss

## Process Steps Completed

### ✅ Step 0: SSOT AUDIT - COMPLETE
- [x] SSOT violations discovered and prioritized
- [x] Business impact assessed 
- [x] GitHub issue #567 created with P0 priority
- [x] Progress tracker (this file) created

### ✅ Step 1: DISCOVER AND PLAN TEST - COMPLETE
- [x] 1.1: Discover existing tests protecting WebSocket agent events
  - **Found**: 120+ mission critical tests inventoried and categorized
  - **Coverage**: Complete inventory of WebSocket, agent event, and execution tests
  - **Commands**: 16 immediate test execution commands (no Docker dependencies)
- [x] 1.2: Plan new tests for SSOT consolidation validation  
  - **Planned**: 24 targeted SSOT consolidation tests
  - **Strategy**: 20% new tests focusing on SSOT factory validation
  - **Expected**: Clear failing/passing states mapped to consolidation progress
  - **Scope**: Unit, integration (non-docker), E2E staging GCP validation

### ✅ Step 2: EXECUTE TEST PLAN (20% NEW TESTS) - COMPLETE
- [x] 2.1: Audit existing mission critical WebSocket tests - Baseline established
- [x] 2.2: Create new SSOT validation tests - 12 new tests created in 3 files
- [x] 2.3: Execute validation tests - **2 P0 SSOT violations confirmed**
- [x] 2.4: Document test execution report - Results captured
- **Key Findings**: WebSocket bridge factory fragmentation confirmed blocking Golden Path
- **Test Files Created**: 
  - `tests/unit/ssot_validation/test_duplicate_websocket_notifier_detection.py`
  - `tests/unit/ssot_validation/test_execution_engine_factory_ssot_validation.py`
  - `tests/unit/ssot_validation/test_websocket_bridge_factory_consolidation.py`

### 🔄 Step 3: PLAN REMEDIATION OF SSOT - PENDING  

### ⏳ Step 4: EXECUTE REMEDIATION PLAN - PENDING

### ⏳ Step 5: ENTER TEST FIX LOOP - PENDING

### ⏳ Step 6: PR AND CLOSURE - PENDING

## Success Criteria
- [ ] Single WebSocketNotifier implementation (SSOT)
- [ ] Single execution engine factory (SSOT)  
- [ ] Single WebSocket bridge factory (SSOT)
- [ ] Single WebSocket manager interface (SSOT)
- [ ] All 5 critical events reliably delivered
- [ ] Golden Path user flow functional: login → AI responses
- [ ] Mission critical tests passing

## Test Requirements
- Must validate WebSocket agent events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
- Must verify user execution context isolation
- Must test Golden Path end-to-end flow
- No Docker-dependent tests (unit, integration non-docker, e2e staging GCP only)

## Related Documentation
- Golden Path: `docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md`
- WebSocket Architecture: `SPEC/learnings/websocket_agent_integration_critical.xml`
- SSOT Guidelines: `CLAUDE.md` sections 5.1, 2.1

---
**Next Action**: Spawn sub-agent for Step 1 - Discover and Plan Test