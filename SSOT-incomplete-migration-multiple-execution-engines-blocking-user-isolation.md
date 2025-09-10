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

## Process Status
- [x] Step 0: SSOT Audit Complete
- [ ] Step 1: Discover and Plan Tests
- [ ] Step 2: Execute Test Plan  
- [ ] Step 3: Plan Remediation
- [ ] Step 4: Execute Remediation
- [ ] Step 5: Test Fix Loop
- [ ] Step 6: PR and Closure

## Next Action
Proceed to Step 1 - Discover existing tests protecting agent execution