# SSOT-incomplete-migration-MessageRouter-critical-violations

**GitHub Issue:** [#217](https://github.com/netra-systems/netra-apex/issues/217)  
**Status:** STEP 0 - SSOT AUDIT COMPLETED  
**Priority:** CRITICAL - Blocking Golden Path  
**Business Impact:** $500K+ ARR chat functionality reliability

## SSOT Audit Results (COMPLETED)

### CRITICAL Violations Identified:
1. **Multiple MessageRouter Implementations** - 4 different router classes
2. **Incomplete Migration** - 15+ test files with REMOVED_SYNTAX_ERROR comments  
3. **Interface Inconsistencies** - Incompatible APIs between routers
4. **Broken Test Infrastructure** - Partially migrated tests failing

### Files Requiring Immediate Attention:
- **CANONICAL SSOT:** `/netra_backend/app/websocket_core/handlers.py:1030-1344`
- **COMPATIBILITY LAYER:** `/netra_backend/app/agents/message_router.py:8-12`
- **COMPETING ROUTERS:** QualityMessageRouter, WebSocketEventRouter, SupervisorAgentRouter
- **135 files** with inconsistent MessageRouter import patterns
- **15+ test files** with commented-out MessageRouter imports

## Process Status:
- [x] Step 0: SSOT AUDIT - ✅ COMPLETED
- [ ] Step 1: DISCOVER AND PLAN TEST
- [ ] Step 2: EXECUTE TEST PLAN (20% new SSOT tests)
- [ ] Step 3: PLAN REMEDIATION OF SSOT
- [ ] Step 4: EXECUTE REMEDIATION SSOT PLAN
- [ ] Step 5: ENTER TEST FIX LOOP
- [ ] Step 6: PR AND CLOSURE

## Next Action:
**SPAWN SUBAGENT TASK (SNST)** for Step 1: DISCOVER AND PLAN TEST

## Key Metrics to Track:
- Number of REMOVED_SYNTAX_ERROR comments eliminated
- Test pass rate improvement
- Router class consolidation progress
- Golden path functionality restoration