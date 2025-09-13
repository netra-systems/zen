# SSOT-incomplete-migration-multiple-execution-engines

**GitHub Issue**: [#759](https://github.com/netra-systems/netra-apex/issues/759)
**Priority**: P0 (Golden Path Critical)
**Status**: Step 0 Complete - Issue Created
**Branch**: develop-long-lived

## Problem Statement

Multiple execution engine implementations exist despite SSOT consolidation claims, creating race conditions and potential user context leakage that directly impacts users getting AI responses.

## Critical Evidence

### Multiple Execution Engines Found:
1. **UserExecutionEngine** - Claimed SSOT
2. **RequestScopedExecutionEngine** - 619 lines, full duplicate implementation
3. **ExecutionEngine** - Multiple redirects/adapters
4. **SupervisorExecutionEngineAdapter**
5. **ConsolidatedExecutionEngineWrapper**
6. **MCPEnhancedExecutionEngine**
7. **IsolatedExecutionEngine**

### Multiple Supervisor Agent Implementations:
- **SupervisorAgent** in `supervisor_ssot.py` (claimed SSOT)
- **SupervisorAgent** in `supervisor_consolidated.py` (duplicate class name)
- **ChatOrchestrator** extending SupervisorAgent
- Multiple workflow orchestrators

### WebSocket Event Delivery Duplication:
- **AgentWebSocketBridge** - 3,800+ lines with full event implementation
- **UnifiedWebSocketEmitter** - Another full implementation
- Multiple `notify_agent_*` methods in different classes

## Golden Path Impact

1. **User Context Isolation Failures**: Multiple execution engines could leak user data
2. **Race Conditions**: Different execution paths causing users to not receive AI responses
3. **Event Delivery Inconsistencies**: Multiple WebSocket implementations causing silent failures
4. **Response Delivery Failures**: Agents execute but responses never reach users

## Progress Tracking

- [x] **Step 0 Complete**: SSOT Audit - Critical P0 violation identified and issue created
- [ ] **Step 1**: Discover existing tests protecting agent execution flow
- [ ] **Step 2**: Execute test plan for new SSOT tests
- [ ] **Step 3**: Plan SSOT remediation strategy
- [ ] **Step 4**: Execute SSOT remediation plan
- [ ] **Step 5**: Test fix loop - validate system stability
- [ ] **Step 6**: Create PR and close issue

## Test Plan (TBD)

### Existing Tests to Validate:
- [ ] TBD - Agent execution tests
- [ ] TBD - WebSocket event delivery tests
- [ ] TBD - User context isolation tests

### New Tests Needed:
- [ ] TBD - SSOT execution engine validation
- [ ] TBD - Response delivery consistency
- [ ] TBD - Multi-user isolation

## Remediation Plan (TBD)

1. **Consolidate Execution Engines**: Eliminate duplicates, redirect to single SSOT
2. **Unify Supervisor Agents**: Remove duplicate implementations
3. **Single WebSocket Event System**: Consolidate event delivery
4. **User Context Validation**: Ensure isolation across all paths

## Files Requiring Changes (TBD)

- Execution engines in `/netra_backend/app/agents/supervisor/`
- Supervisor implementations in `/netra_backend/app/agents/`
- WebSocket bridges in `/netra_backend/app/services/` and `/netra_backend/app/websocket_core/`

---
*Last Updated*: 2025-01-13 | *Next Update*: Step 1 completion