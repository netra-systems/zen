# Failing Test Gardener Worklog - Agents Test Focus
**Generated:** 2025-09-14 15:46 UTC  
**Test Focus:** agents (agent-related tests across all categories)  
**Total Agent Test Files Found:** 1,161 files  

## Executive Summary

Initial discovery identified several critical issues in agent-related testing:

1. **Mission Critical Agent WebSocket Tests:** 2 ERROR failures in end-to-end agent conversation flow
2. **Test Runner Command Line:** Argument parsing issue with `--fast-fail=false`
3. **SSOT Violations:** WebSocket Manager SSOT violations during test startup
4. **Test Collection:** Need to investigate unit test collection for agent tests

## Discovered Issues

### 1. Mission Critical Agent WebSocket Test Failures (P1 - High Priority)
**File:** `tests/mission_critical/test_websocket_agent_events_suite.py`  
**Status:** ERROR  
**Tests Affected:**
- `TestRealE2EWebSocketAgentFlow::test_real_e2e_agent_conversation_flow`
- `TestRealE2EWebSocketAgentFlow::test_real_websocket_resilience_and_recovery`

**Symptoms:**
- Tests showing ERROR status instead of PASS/FAIL
- Tests were terminated/interrupted during execution
- Other WebSocket tests in same suite are passing

**Business Impact:** HIGH - These are mission critical tests protecting $500K+ ARR agent conversation functionality

### 2. Test Runner Argument Parsing Issue (P3 - Low Priority)
**Command:** `python3 tests/unified_test_runner.py --category unit --pattern "*agent*" --no-coverage --fast-fail=false`  
**Error:** `unified_test_runner.py: error: argument --fast-fail: ignored explicit argument 'false'`

**Issue:** The unified test runner expects `--fast-fail` as a flag, not `--fast-fail=false`

### 3. SSOT WebSocket Manager Violations (P2 - Medium Priority)
**During Test Startup:**
```
SSOT WARNING: Found other WebSocket Manager classes: [
  'netra_backend.app.websocket_core.websocket_manager.WebSocketManagerMode', 
  'netra_backend.app.websocket_core.websocket_manager.WebSocketManagerProtocol', 
  'netra_backend.app.websocket_core.unified_manager.WebSocketManagerMode', 
  'netra_backend.app.websocket_core.protocols.WebSocketManagerProtocol', 
  'netra_backend.app.websocket_core.protocols.WebSocketManagerProtocolValidator'
]
```

**Impact:** SSOT consolidation violations that may affect test reliability

### 4. Agent Test Collection Issues (P2 - Medium Priority)
**Files to Investigate:**
- 1,161 agent test files found
- Need to check unit test collection success rate
- Potential for uncollectable tests

**Key Test Categories Found:**
- Unit tests: `tests/unit/agents/*` (20+ files)
- Integration tests: Agent registry, WebSocket bridge tests
- SSOT validation tests: Agent execution tracker, instance factory tests
- Security tests: DeepAgentState security violations

## Next Steps for Investigation

1. **Run individual failing tests** to get detailed error messages
2. **Check test collection** for unit tests specifically  
3. **Investigate WebSocket Manager SSOT** violations
4. **Search existing GitHub issues** for related problems

## Test Files Requiring Investigation

### High Priority
- `tests/mission_critical/test_websocket_agent_events_suite.py` (ERROR failures)
- `tests/unit/agents/test_agent_instance_factory_*` (User isolation tests)
- `tests/unit/test_deepagentstate_security_violations.py` (Security)

### Medium Priority  
- `tests/unit/agents/test_agent_registry_*` (Registry conflicts)
- `tests/unit/ssot_validation/test_agent_execution_*` (SSOT compliance)
- `tests/integration/agents/*` (If exists)

### WebSocket Integration
- All agent WebSocket bridge integration tests
- Agent message processing tests
- Agent execution timeout tests

## Environment Context
- **Python Version:** 3.13.7
- **Test Runner:** tests/unified_test_runner.py
- **WebSocket Backend:** Staging environment wss://netra-backend-staging-pnovr5vsba-uc.a.run.app
- **SSOT Status:** Active consolidation with known violations

---
*This worklog will be updated as issues are investigated and resolved.*