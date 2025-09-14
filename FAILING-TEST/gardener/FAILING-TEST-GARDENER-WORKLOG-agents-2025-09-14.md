# Failing Test Gardener Worklog - Agents Focus - 2025-09-14

## Test Focus: Agent Tests
**Created:** 2025-09-14  
**Scope:** Agent-related unit, integration, and E2E tests  
**Goal:** Identify and catalog failing agent tests for GitHub issue creation/updates  

## Discovered Issues

### Test Execution Log

#### 1. Mission Critical WebSocket Agent Events Suite - 3 FAILURES
**File:** `tests/mission_critical/test_websocket_agent_events_suite.py`  
**Run Time:** 2025-09-14 06:43:28  
**Status:** 39 collected, 36 passed, 3 FAILED  

**Failures:**
1. **`test_agent_started_event_structure`**
   - **Error:** `AssertionError: agent_started event structure validation failed`
   - **Issue:** Event structure validation fails for agent_started events
   - **Severity:** P1 - High (breaks core chat functionality)
   - **Category:** failing-test-regression-high

2. **`test_tool_executing_event_structure`** 
   - **Error:** `AssertionError: tool_executing missing tool_name`
   - **Issue:** tool_executing events are missing required `tool_name` field
   - **Severity:** P1 - High (breaks tool transparency for users)
   - **Category:** failing-test-regression-high

3. **`test_tool_completed_event_structure`**
   - **Error:** `AssertionError: tool_completed missing results`
   - **Issue:** tool_completed events are missing required `results` field
   - **Severity:** P1 - High (breaks tool results display)
   - **Category:** failing-test-regression-high

**Context:** These are mission critical tests protecting $500K+ ARR chat functionality. All failures relate to WebSocket event structure validation which is essential for real-time user experience.

#### 2. Agent Factory Tests - 10 FAILURES, 4 ERRORS
**File:** `netra_backend/tests/unit/test_agent_factory.py`  
**Run Time:** 2025-09-14 06:44:46  
**Status:** 13 collected, 6 failed, 3 passed, 4 errors  

**Errors (Setup Issues):**
4. **`TestUserWebSocketEmitter` Setup Errors** (4 tests affected)
   - **Error:** `TypeError: UnifiedWebSocketEmitter.__init__() got an unexpected keyword argument 'thread_id'`
   - **Issue:** WebSocket emitter API changed, tests using deprecated `thread_id` parameter
   - **Severity:** P2 - Medium (test infrastructure outdated)
   - **Category:** uncollectable-test-api-change-medium

**Failures:**
5. **`test_factory_initialization_validates_dependencies`**
   - **Error:** `Failed: DID NOT RAISE <class 'netra_backend.app.agents.supervisor.execution_engine_factory.ExecutionEngineFactoryError'>`
   - **Issue:** Expected exception not raised during factory initialization
   - **Severity:** P2 - Medium (validation logic not working)
   - **Category:** failing-test-regression-medium

6. **`test_execution_engine_creation_with_context`**
   - **Error:** `AttributeError: <ExecutionEngineFactory object> does not have the attribute '_create_user_execution_engine'`
   - **Issue:** Test expects method that no longer exists in ExecutionEngineFactory
   - **Severity:** P2 - Medium (test out of sync with implementation)
   - **Category:** failing-test-api-change-medium

7. **`test_engine_lifecycle_management`**
   - **Error:** Similar AttributeError for missing `_create_user_execution_engine`
   - **Severity:** P2 - Medium
   - **Category:** failing-test-api-change-medium

8. **`test_concurrent_engine_creation`**
   - **Error:** Similar AttributeError for missing `_create_user_execution_engine`
   - **Severity:** P2 - Medium
   - **Category:** failing-test-api-change-medium

9. **`test_websocket_emitter_binding_per_agent`**
   - **Error:** Same TypeError with `thread_id` parameter
   - **Severity:** P2 - Medium
   - **Category:** failing-test-api-change-medium

10. **`test_factory_error_recovery_patterns`**
   - **Error:** Same TypeError with `thread_id` parameter
   - **Severity:** P2 - Medium
   - **Category:** failing-test-api-change-medium

#### 3. Agent State Tests - 2 FAILURES
**File:** `netra_backend/tests/unit/test_agent_state.py`  
**Run Time:** 2025-09-14 06:45:02  
**Status:** 17 collected, 2 failed, 15 passed  

**Failures:**
11. **`test_set_state_valid_transition_pending_to_running`**
   - **Error:** `AssertionError: assert 'transitioning from pending to running' in 'state_test_agent transitioning from subagentlifecycle.pending to subagentlifecycle.running'`
   - **Issue:** Log message format changed, test expects old format
   - **Severity:** P3 - Low (cosmetic log format change)
   - **Category:** failing-test-format-change-low

12. **`test_execution_timing_under_threshold`**
   - **Error:** `AssertionError: Metric 'pending_to_running_transition' was not recorded`
   - **Issue:** Expected metric not being recorded during state transitions
   - **Severity:** P2 - Medium (metrics/monitoring system issue)
   - **Category:** failing-test-monitoring-medium

#### 4. Agent Orchestration Test - IMPORT ERROR
**File:** `tests/run_agent_orchestration_tests.py`  
**Run Time:** 2025-09-14 06:44:35  
**Status:** ERROR - Cannot execute  

**Import Error:**
13. **Module Import Error**
   - **Error:** `ModuleNotFoundError: No module named 'shared'`
   - **Issue:** Python path or import structure issue preventing test execution
   - **Severity:** P2 - Medium (test infrastructure misconfigured)
   - **Category:** uncollectable-test-import-error-medium

#### 5. Critical Agent Tests - RESOURCE ERROR  
**File:** `scripts/run_critical_agent_tests.py`  
**Run Time:** 2025-09-14 06:44:32  
**Status:** ERROR - Insufficient memory  

**Resource Error:**
14. **Memory Pre-flight Check Failed**
   - **Error:** `INSUFFICIENT MEMORY: Available 6.5GB < Required 8.0GB`
   - **Issue:** Test requires more memory than available on system
   - **Severity:** P3 - Low (resource constraint, not code issue)
   - **Category:** failing-test-resource-constraint-low

## Summary

**Total Issues Discovered:** 14 issues across 5 test suites  
**Priority Breakdown:**
- **P1 (High):** 3 issues - Mission critical WebSocket events failing
- **P2 (Medium):** 8 issues - Agent factory API changes, state monitoring, import errors  
- **P3 (Low):** 3 issues - Log format changes, resource constraints

**Business Impact:**
- **HIGH:** $500K+ ARR at risk from WebSocket event structure validation failures
- **MEDIUM:** Developer productivity impact from outdated test infrastructure
- **LOW:** Cosmetic and resource constraint issues

**Action Required:**
Each issue will be processed through sub-agents to:
1. Search for existing GitHub issues
2. Create new issues or update existing ones with current logs
3. Apply appropriate priority tags and categorization
4. Link related issues and documentation

**Next Steps:** Process all 14 issues through GitHub issue management sub-agents.