# SSOT-incomplete-migration-multiple-execution-engine-implementations

**GitHub Issue:** [#686](https://github.com/netra-systems/netra-apex/issues/686)
**Priority:** P0 - Golden Path Blocking
**Status:** Discovery Complete
**Created:** 2025-09-12

## 🚨 CRITICAL SSOT VIOLATION: Multiple ExecutionEngine Implementations

### Business Impact
- **Revenue Risk:** $500K+ ARR at risk
- **Golden Path:** BLOCKED - Users login but can't get AI responses
- **Security Risk:** User isolation compromised

### SSOT Violations Discovered

#### 1. Multiple ExecutionEngine Classes (P0)
**Files:**
- `netra_backend/app/agents/supervisor/execution_engine.py` (deprecated redirect)
- `netra_backend/app/agents/supervisor/user_execution_engine.py` (SSOT implementation)
- `netra_backend/app/agents/unified_tool_execution.py:119` (UnifiedToolExecutionEngine)
- `netra_backend/app/agents/tool_dispatcher_execution.py:23` (ToolExecutionEngine)

**Violation:** Multiple execution engine implementations violate SSOT principle

**Impact:**
- Execution engine confusion blocks agent responses
- WebSocket user isolation vulnerabilities
- Context contamination between concurrent users

#### 2. Shared Agent Registry State (P0)
**Files:**
- `netra_backend/app/agents/supervisor/agent_registry.py` (lines 28-31, 1801-1815)

**Violation:** Global registry pattern sharing state across users

#### 3. WebSocket Context Factory Issues (P0)
**Files:**
- `netra_backend/app/websocket_core/websocket_manager_factory.py` (lines 39-42, 311-315)

**Violation:** Singleton factory with shared state

#### 4. Agent Context Contamination (P1)
**Files:**
- `netra_backend/app/agents/supervisor/execution_factory.py` (lines 76-84, 100-130)

**Violation:** User execution context isolation violations

#### 5. Workflow Orchestrator Shared State (P1)
**Files:**
- `netra_backend/app/agents/supervisor/workflow_orchestrator.py` (lines 34-38, 71-88)

**Violation:** Shared WebSocket manager across users

## Process Status

### ✅ Step 0: Discovery Complete
- [x] SSOT Audit conducted by sub-agent
- [x] Critical violations identified and prioritized
- [x] GitHub issue #686 created
- [x] Local progress tracker created

### ✅ Step 1: Test Discovery & Planning Complete
- [x] Discover existing tests protecting against breaking changes
- [x] Plan new tests for SSOT refactor validation
- [x] Focus on unit/integration tests (no docker required)
- [x] 680+ test files with ExecutionEngine references found
- [x] Test strategy: 20% new SSOT tests, 60% existing test updates, 20% coverage gaps

### ✅ Step 2: Execute Test Plan Complete
- [x] Create new SSOT validation tests
- [x] Run tests to establish baseline
- [x] Focus on 20% new SSOT enforcement tests
- [x] 3 new test files created that FAIL with current violations
- [x] Tests prove ExecutionEngine SSOT violations exist

### ✅ Step 3: Plan SSOT Remediation Complete
- [x] Plan ExecutionEngine consolidation strategy
- [x] Plan Agent Registry isolation fixes
- [x] Plan WebSocket Factory SSOT compliance
- [x] 3-phase atomic remediation strategy designed
- [x] Risk mitigation and rollback plans created

### ⏳ Step 4: Execute SSOT Remediation (CURRENT)
- [ ] Phase 1: ExecutionEngine consolidation (lowest risk)
- [ ] Phase 2: Agent Registry isolation fixes (medium risk)
- [ ] Phase 3: WebSocket Factory SSOT compliance (highest risk)
- [ ] Ensure atomic changes and backward compatibility

### ⏳ Step 5: Test Fix Loop
- [ ] Validate all tests pass
- [ ] Iterate until stability achieved

### ⏳ Step 6: PR & Closure
- [ ] Create pull request
- [ ] Link to issue for closure

## Technical Notes

### Current SSOT Compliance: 60%
### Target SSOT Compliance: 95%
### Golden Path Readiness: Currently BLOCKED

### Test Strategy
- Focus on non-docker tests (unit, integration, e2e staging)
- ~20% new SSOT validation tests
- ~60% existing test validation/updates
- ~20% new coverage tests

### Remediation Approach
1. **Phase 1 (P0):** ExecutionEngine consolidation, Agent Registry isolation, WebSocket Factory fixes
2. **Phase 2 (P1):** Context isolation hardening

## References
- [SSOT Import Registry](SSOT_IMPORT_REGISTRY.md)
- [Definition of Done Checklist](reports/DEFINITION_OF_DONE_CHECKLIST.md)
- [Claude.md Instructions](CLAUDE.md)