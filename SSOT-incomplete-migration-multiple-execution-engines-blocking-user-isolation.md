# SSOT-incomplete-migration-multiple-execution-engines-blocking-user-isolation

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/182  
**Priority:** P0 - Critical Golden Path Blocker  
**Status:** In Progress - Step 0 Complete

## Issue Summary
7 duplicate execution engines causing user isolation failures and WebSocket chaos, blocking Golden Path reliability.

## Critical Files Identified
1. `/netra_backend/app/agents/supervisor/execution_engine.py` (1,571 lines) - DEPRECATED, global state
2. `/netra_backend/app/agents/supervisor/user_execution_engine.py` (1,128 lines) - Best isolation 
3. `/netra_backend/app/agents/supervisor/request_scoped_execution_engine.py`
4. `/netra_backend/app/agents/supervisor/mcp_execution_engine.py`
5. `/netra_backend/app/agents/execution_engine_consolidated.py`
6. `/netra_backend/app/agents/supervisor/execution_factory.py:434` (IsolatedExecutionEngine)
7. `/netra_backend/app/agents/base/executor.py:266` (BaseExecutionEngine)

## Business Impact
- $500K+ ARR at risk from chat functionality failures
- User isolation race conditions
- WebSocket event delivery chaos
- Memory leaks from inconsistent cleanup

## Step 1 Results: Test Discovery Complete ✅
**Test Inventory Found:** 25+ execution engine tests
- **Mission Critical:** 4 tests protecting $500K+ ARR WebSocket events
- **High Risk:** 8 tests requiring updates during SSOT consolidation  
- **Will Break:** 1 test (factory duplication validation)
- **Coverage Gaps:** SSOT transition compatibility tests needed

**Key Protected Behaviors:**
- WebSocket event delivery (all 5 critical events)
- User isolation and concurrency control
- Agent execution lifecycle and error handling
- Factory pattern creation and cleanup

## Process Status
- [x] Step 0: SSOT Audit Complete
- [x] Step 1: Discover and Plan Tests Complete  
- [ ] Step 2: Execute Test Plan (20% new SSOT tests)
- [ ] Step 3: Plan Remediation
- [ ] Step 4: Execute Remediation
- [ ] Step 5: Test Fix Loop
- [ ] Step 6: PR and Closure

## Next Action
Proceed to Step 2 - Execute test plan for 20% new SSOT transition tests