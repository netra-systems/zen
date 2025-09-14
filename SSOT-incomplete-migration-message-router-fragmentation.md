# SSOT Gardener Progress: Message Router Fragmentation

**GitHub Issue**: [#1077](https://github.com/netrasystems/netra-apex/issues/1077)
**Focus Area**: Message routing SSOT consolidation  
**Priority**: P0 - Golden Path blocker
**Session**: 2025-09-14 SSOT Gardener

## Issue Summary
4 separate MessageRouter implementations causing routing conflicts and blocking Golden Path (user login → AI responses).

### Critical Files Identified
- **SSOT TARGET**: `/netra_backend/app/websocket_core/handlers.py:1208` - Primary MessageRouter
- **DUPLICATE**: `/netra_backend/app/services/websocket/quality_message_router.py:36` - QualityMessageRouter  
- **DUPLICATE**: `/netra_backend/app/core/message_router.py:55` - Core MessageRouter
- **ALIAS**: `/netra_backend/app/agents/message_router.py:1-12` - Import alias

## Business Impact
- $500K+ ARR at risk from Golden Path failures
- Message routing conflicts blocking user chat functionality
- Cross-user event leakage security risk
- Agent response failures due to routing competition

## Process Progress

### ✅ Step 0: SSOT Audit Complete
- [x] Identified top 3 critical MessageRouter SSOT violations
- [x] Created/updated GitHub issue #1077  
- [x] Created local tracking file

### 🔄 Step 1: Discover and Plan Test (IN PROGRESS)
- [ ] 1.1: Discover existing tests protecting MessageRouter functionality
- [ ] 1.2: Plan test suite for SSOT consolidation validation

### ⏳ Upcoming Steps  
- [ ] Step 2: Execute new test plan (20% new SSOT tests)
- [ ] Step 3: Plan SSOT remediation 
- [ ] Step 4: Execute SSOT remediation
- [ ] Step 5: Test fix loop until all pass
- [ ] Step 6: PR and closure

## Notes
- Focus on atomic changes maintaining system stability
- All tests must pass before proceeding
- Use non-docker tests only (unit, integration, e2e staging)
- Keep changes minimal for one atomic commit unit

## Next Action
Spawn sub-agent for Step 1: Discover existing tests and plan SSOT test coverage.