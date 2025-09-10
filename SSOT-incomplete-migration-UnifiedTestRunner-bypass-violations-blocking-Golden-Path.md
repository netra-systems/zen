# SSOT-incomplete-migration-UnifiedTestRunner bypass violations blocking Golden Path

**GitHub Issue:** [#227](https://github.com/netra-systems/netra-apex/issues/227)  
**Created:** 2025-09-10  
**Priority:** P0 - Critical  
**Status:** Investigation Phase  

## Issue Summary
150+ SSOT violations in test execution bypassing UnifiedTestRunner threaten Golden Path stability. Mission-critical auth and WebSocket validation lacks proper orchestration.

## SSOT Violations Found
- **P0 Critical:** 32+ mission-critical test bypasses
- **Auth Service:** All tests use direct pytest.main() instead of SSOT
- **CI/CD Risk:** Production pipelines bypass UnifiedTestRunner coordination  
- **Golden Path:** Race condition tests missing resource management

## Business Impact
$500K+ ARR chat functionality lacks consistent validation due to fragmented test execution patterns.

## Technical Details
- **Main Issue:** Multiple test execution paths bypassing `/tests/unified_test_runner.py`
- **Root Cause:** Incomplete migration from legacy pytest patterns to SSOT UnifiedTestRunner
- **Impact:** Inconsistent Docker orchestration, resource conflicts, missed failures
- **Priority:** P0 - Blocks reliable Golden Path validation

## Work Progress

### Phase 0: Discovery (COMPLETED)
- ✅ Comprehensive SSOT audit completed
- ✅ 150+ violations identified across 7 categories
- ✅ GitHub issue #227 created
- ✅ Progress tracking document created

### Next: Phase 1 - Test Discovery and Planning
- [ ] Discover existing tests protecting SSOT refactor
- [ ] Plan new tests for SSOT validation
- [ ] Focus on 60% existing + 20% new + 20% validation

## Critical Files Affected
- `/tests/unified_test_runner.py` - SSOT test execution
- Mission critical tests bypassing SSOT patterns
- Auth service test execution
- CI/CD workflow test execution

## Success Criteria
- All critical test paths use UnifiedTestRunner SSOT
- Golden Path validation has consistent orchestration
- No regression in test reliability or coverage