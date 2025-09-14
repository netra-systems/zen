# SSOT-AGENTS-ExecutionEngineFactory-Duplication

**GitHub Issue**: [#917](https://github.com/netra-systems/netra-apex/issues/917)
**Priority**: P0 - Critical Golden Path Blocking
**Status**: DISCOVERY COMPLETE

## Progress Tracking

### ✅ STEP 0: DISCOVER NEXT SSOT ISSUE (COMPLETED)
- **Issue Created**: GitHub Issue #917
- **Priority**: P0 - Critical system failure blocking Golden Path
- **Root Cause**: Multiple ExecutionEngineFactory implementations causing agent instantiation conflicts

### Critical SSOT Violation Details
**Files Involved**:
- `netra_backend/app/agents/supervisor/execution_engine_factory.py` (Primary implementation)
- `netra_backend/app/core/managers/execution_engine_factory.py` (Compatibility layer)

**Impact**:
- Golden Path BLOCKED: Users login → Agent creation uses inconsistent factories
- $500K+ ARR at Risk: Core chat functionality reliability compromised
- 156+ files affected: System-wide impact on agent instantiation

**Violation Type**: Agent factory duplication preventing consistent agent instantiation

### Resolution Requirements
1. Consolidate to single ExecutionEngineFactory in canonical location
2. Remove compatibility layer in core/managers
3. Update all 156+ files to import from single source
4. Validate WebSocket bridge integration consistency
5. Ensure user isolation patterns remain intact
6. Maintain agent execution context consistency

### Next Steps
- [ ] STEP 1: DISCOVER AND PLAN TEST (Pending)
- [ ] STEP 2: EXECUTE THE TEST PLAN (Pending)
- [ ] STEP 3: PLAN REMEDIATION OF SSOT (Pending)
- [ ] STEP 4: EXECUTE THE REMEDIATION SSOT PLAN (Pending)
- [ ] STEP 5: ENTER TEST FIX LOOP (Pending)
- [ ] STEP 6: PR AND CLOSURE (Pending)

## Working Notes
**Date**: 2025-09-13
**Focus Area**: agents
**SSOT Gardener Process**: Step 0 Complete - Issue Discovery and Creation
**Safety Status**: Ready for test discovery phase

## Test Strategy Planning
**Test Categories Required**:
- Unit tests: ExecutionEngineFactory instantiation patterns
- Integration tests: Agent creation through factory (non-docker)
- E2E tests: Golden Path validation on staging GCP
- Mission critical: Agent WebSocket event delivery

**Coverage Requirements**:
- 60% existing tests (validation + updates)
- 20% new SSOT violation tests (failing)
- 20% post-fix validation tests