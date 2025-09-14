# SSOT-critical-agent-websocket-bridge-bypass-violation

**GitHub Issue:** [#1070](https://github.com/netra-systems/netra-apex/issues/1070)
**Priority:** P0 Golden Path Blocker
**Business Impact:** $500K+ ARR - Real-time chat functionality reliability
**SSOT Focus:** WebSocket manager proliferation and agent bridge bypassing

## Problem Summary

10+ agent files are directly importing WebSocket managers instead of using the SSOT agent-websocket bridge pattern, causing:

1. **Multi-user isolation failures** - cross-user data contamination
2. **Race conditions** - WebSocket 1011 errors in Cloud Run environment
3. **Golden Path disruption** - users not receiving real-time AI responses
4. **Business risk** - core chat functionality reliability compromised

## Files Violating SSOT Bridge Pattern

- `netra_backend/app/agents/supervisor/agent_registry.py`
- `netra_backend/app/agents/supervisor/mcp_execution_engine.py`
- `netra_backend/app/agents/supervisor/pipeline_executor.py`
- `netra_backend/app/agents/tool_dispatcher_execution.py`
- `netra_backend/app/agents/supervisor/agent_instance_factory.py`
- Plus 5 additional agent files identified

## SSOT Bridge Pattern Requirements

**CORRECT PATTERN:**
```python
# Through AgentRegistry bridge (SSOT)
registry = AgentRegistry.get_instance()
registry.send_websocket_event(user_id, event_data)
```

**VIOLATION PATTERN:**
```python
# Direct WebSocket manager access (VIOLATES SSOT)
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager
manager = WebSocketManager()
manager.send_agent_update(...)
```

## Root Cause Analysis

The agents bypass the factory-based isolation architecture by directly instantiating WebSocket managers instead of accessing them through the AgentRegistry bridge pattern.

## Progress Tracking

### Phase 0: Discovery and Planning ✅ COMPLETE
- [x] SSOT audit completed - identified 10+ violating agent files
- [x] GitHub issue #1070 created
- [x] Local tracking file created
- [x] Business impact assessment: $500K+ ARR risk

### Phase 1: Test Discovery and Planning 🔄 IN PROGRESS
- [ ] Discover existing WebSocket bridge tests
- [ ] Identify tests protecting against SSOT violations
- [ ] Plan new SSOT validation tests (~20% of work)
- [ ] Plan test updates for existing coverage (~60% of work)

### Phase 2: New SSOT Test Creation 🔄 PENDING
- [ ] Create failing tests reproducing bridge bypass violations
- [ ] Implement SSOT bridge pattern validation tests
- [ ] Run tests to confirm they fail with current violations

### Phase 3: SSOT Remediation Planning 🔄 PENDING
- [ ] Plan migration from direct imports to bridge pattern
- [ ] Identify agent files requiring updates
- [ ] Plan AgentRegistry bridge enforcement

### Phase 4: SSOT Remediation Execution 🔄 PENDING
- [ ] Execute remediation plan
- [ ] Update agent files to use bridge pattern
- [ ] Eliminate direct WebSocket manager imports

### Phase 5: Test Fix Loop 🔄 PENDING
- [ ] Run and fix all test cases
- [ ] Ensure system stability maintained
- [ ] Verify no new breaking changes introduced
- [ ] Run startup tests (non-docker)

### Phase 6: PR and Closure 🔄 PENDING
- [ ] Create pull request
- [ ] Cross-link with issue #1070
- [ ] Verify tests passing before merge

## SSOT Compliance Goals

- ✅ **Detection**: SSOT violation identified and documented
- ⏳ **Prevention**: Create tests preventing future violations
- ⏳ **Remediation**: Migrate agents to use bridge pattern exclusively
- ⏳ **Validation**: Ensure all WebSocket events go through SSOT bridge

## Test Strategy

Focus on **non-docker tests only**:
- Unit tests for bridge pattern compliance
- Integration tests for AgentRegistry WebSocket integration
- E2E tests on staging GCP for Golden Path validation

**NO DOCKER TESTS** - focusing on unit, integration (no docker), and e2e staging GCP only.

## Business Value Protection

This SSOT remediation directly protects:
- **Golden Path reliability**: Users login → get real AI responses
- **Real-time chat experience**: 90% of platform value
- **Multi-user security**: Enterprise compliance for user isolation
- **System stability**: Elimination of WebSocket race conditions

---

**Status:** 🔄 Phase 1 In Progress - Test Discovery and Planning
**Last Updated:** 2025-01-14
**Next Action:** Spawn sub-agent for test discovery phase