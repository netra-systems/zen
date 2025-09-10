# SSOT-incomplete-migration: ToolExecutorFactory vs UnifiedToolDispatcher duplication blocks golden path

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/219  
**Status:** In Progress  
**Created:** 2025-01-09  

## Problem Summary
🚨 **BLOCKING GOLDEN PATH** - Users login → get AI responses fails due to tool execution routing conflicts

**Critical SSOT Violation:** Two competing tool execution systems create unpredictable routing and WebSocket event loss.

## Files Affected
1. **Primary:** `/netra_backend/app/agents/tool_executor_factory.py`
2. **Competing:** `/netra_backend/app/core/tools/unified_tool_dispatcher.py`
3. **Related WebSocket Adapters:** Multiple implementations

## SSOT Violations Identified
1. **Duplicate Responsibility:** Both systems manage tool execution
2. **WebSocket Adapter Proliferation:** 3 different adapter implementations  
3. **Tool Registry Duplication:** Each dispatcher creates own registry
4. **Factory Pattern Inconsistency:** Half-migrated enforcement with bypasses

## Business Impact
- **$500K+ ARR chat functionality unreliable**
- Inconsistent AI responses depending on execution path
- WebSocket events lost when wrong dispatcher used
- User experience degraded in core chat functionality

## Work Progress

### Step 0: SSOT AUDIT ✅ COMPLETE
- [x] Comprehensive audit of ToolExecutorFactory SSOT violations
- [x] Identified 4 major violations blocking golden path
- [x] GitHub issue created: #219
- [x] Local tracking file created

### Step 1: DISCOVER AND PLAN TEST ✅ COMPLETE  
- [x] 1.1: Find existing tests protecting against breaking changes
  - **FOUND:** 500+ related test files with extensive coverage
  - **CRITICAL:** `/tests/mission_critical/test_websocket_agent_events_suite.py` must pass
  - **EXISTING SSOT TEST:** `/tests/integration/factory_ssot/test_factory_ssot_tool_dispatcher_violations.py`
  - **IMPORT UPDATES:** 36 files need UnifiedToolDispatcher import changes
- [x] 1.2: Plan new tests for SSOT refactor validation
  - **TEST STRATEGY:** 60% existing protection, 20% new SSOT tests, 20% stability verification
  - **FAILING TESTS:** Design tests to reproduce SSOT violation (before fix)
  - **SUCCESS TESTS:** Validate consolidated execution path (after fix)
  - **BUSINESS VALUE:** All 5 WebSocket events must deliver (agent_started → agent_completed)

### Step 2: EXECUTE TEST PLAN (20% new SSOT tests)
- [ ] Create failing tests that reproduce SSOT violation
- [ ] Run unit/integration tests (non-docker)

### Step 3: PLAN REMEDIATION
- [ ] Plan SSOT consolidation approach
- [ ] Design migration path from UnifiedToolDispatcher to ToolExecutorFactory

### Step 4: EXECUTE REMEDIATION
- [ ] Implement redirect pattern (Phase 1)
- [ ] Update all callers (Phase 2) 
- [ ] Remove duplicate system (Phase 3)

### Step 5: TEST FIX LOOP
- [ ] Prove stability maintained
- [ ] All tests pass
- [ ] No new breaking changes

### Step 6: PR AND CLOSURE
- [ ] Create Pull Request
- [ ] Cross-link with issue #219

## Proposed Solution
**Phase 1:** Redirect UnifiedToolDispatcher calls to ToolExecutorFactory  
**Phase 2:** Migrate all callers to use ToolExecutorFactory directly  
**Phase 3:** Remove UnifiedToolDispatcher entirely

## Test Strategy
- Focus on existing test protection (60%)
- New SSOT validation tests (20%)  
- Stability verification (20%)
- **NO DOCKER TESTS** - unit, integration (no docker), e2e staging only

## Notes
- Stay on develop-long-lived branch
- Follow atomic commit pattern
- Minimize scope per cycle
- Ensure system stability throughout