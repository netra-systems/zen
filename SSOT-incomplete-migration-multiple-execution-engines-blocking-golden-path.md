# SSOT-incomplete-migration-multiple-execution-engines-blocking-golden-path

**GitHub Issue:** https://github.com/netra-systems/netra-apex/issues/620  
**Priority:** P0 IMMEDIATE - Blocking golden path  
**Focus:** Agent execution and messaging SSOT consolidation  
**Status:** DISCOVERY COMPLETE

## Problem Summary
Multiple execution engine implementations exist with actual code instead of pure redirects, causing import confusion and potential runtime failures that block users from getting AI responses.

## Files Requiring Remediation
- `/netra_backend/app/agents/supervisor/execution_engine.py` (DEPRECATED but contains code)
- `/netra_backend/app/agents/execution_engine_consolidated.py` (DEPRECATED but contains code)  
- `/netra_backend/app/agents/supervisor/user_execution_engine.py` (SSOT - should be only one)
- `/netra_backend/app/agents/execution_engine_unified_factory.py` (Factory wrapper)
- `/netra_backend/app/agents/supervisor/execution_engine_factory.py` (Legacy factory)

## Business Impact
- **REVENUE RISK:** $500K+ ARR at risk due to agent execution failures
- **USER EXPERIENCE:** Broken chat functionality (90% of platform value)
- **GOLDEN PATH:** Users cannot get AI responses if wrong execution engine used

## Process Status

### ✅ Step 0: SSOT AUDIT COMPLETE
- [x] Critical SSOT violations discovered
- [x] P0 violation identified: Multiple execution engine implementations
- [x] GitHub issue #620 created
- [x] Progress tracker file created

### 🔄 Step 1: TEST DISCOVERY (IN PROGRESS)
- [ ] Discover existing tests protecting agent execution
- [ ] Plan test suite for SSOT consolidation validation
- [ ] Identify test gaps for execution engine flows

### ⏳ Step 2: NEW SSOT TESTS
- [ ] Create failing tests for SSOT violations
- [ ] Create passing tests for desired SSOT state
- [ ] Run tests to validate current failures

### ⏳ Step 3: PLAN REMEDIATION
- [ ] Plan execution engine SSOT consolidation
- [ ] Plan import redirect strategy
- [ ] Plan backwards compatibility approach

### ⏳ Step 4: EXECUTE REMEDIATION
- [ ] Convert deprecated files to import redirects
- [ ] Audit all execution engine imports
- [ ] Remove duplicate implementation code

### ⏳ Step 5: TEST FIX LOOP
- [ ] Run all related tests
- [ ] Fix any breaking changes
- [ ] Ensure golden path functionality intact

### ⏳ Step 6: PR AND CLOSURE
- [ ] Create pull request with changes
- [ ] Link to GitHub issue #620
- [ ] Verify all tests pass before merge

## Test Requirements

### Existing Tests to Validate
- Mission critical tests for agent execution
- WebSocket agent events suite
- Golden path user flow tests
- Integration tests for execution engines

### New Tests to Create (~20% of work)
- Tests that fail with current SSOT violations
- Tests that pass with proper SSOT consolidation
- Import validation tests for execution engines

## Notes
- Focus on minimal changes per atomic commit
- Ensure backwards compatibility during migration
- Prioritize system stability over speed
- All deprecated files should become pure import redirects

**Last Updated:** 2025-09-12  
**Next Action:** Step 1 - Discover and plan tests for execution engine SSOT consolidation