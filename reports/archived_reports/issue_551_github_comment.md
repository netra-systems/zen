# Issue #551 TEST PLAN: Integration Test Import Failures

## 🎯 TEST PLAN SUMMARY

**Root Cause Confirmed:** Missing `setup_test_path()` calls in integration test files  
**Scope:** 1,508 integration test files, ~1,458 missing the fix  
**Business Impact:** P1 - Golden Path validation blocking ($500K+ ARR)  

## ✅ ISSUE REPRODUCTION CONFIRMED

**Failing Example:**
```bash
# FAILS with ModuleNotFoundError: No module named 'test_framework'
python analytics_service/tests/integration/service_integration/test_analytics_service_integration.py
```

**Working Example:**
```python
# analytics_service/tests/integration/test_api_integration.py - HAS FIX
from test_framework import setup_test_path
setup_test_path()  # CRITICAL: Must be before project imports
```

## 🧪 3-PHASE TEST STRATEGY

### Phase 1: Unit Tests - Path Resolution Validation
- Test `setup_test_path()` function behavior 
- Validate import resolution before/after pattern
- Document pytest vs direct Python execution differences

### Phase 2: Integration Tests - Systematic Validation (Non-Docker)
- Scan 1,508 integration test files for missing pattern
- Prove sample files fail without setup_test_path()
- Validate pattern application restores functionality
- Cross-service impact analysis (analytics, auth, backend, shared)

### Phase 3: Staging GCP E2E Tests - Golden Path Protection  
- Validate Golden Path reliability with fixed imports
- Test $500K+ ARR functionality protection
- Ensure WebSocket integration tests work in staging

## 📋 TEST EXECUTION COMMANDS

```bash
# Phase 1: Unit tests for path resolution  
python tests/unified_test_runner.py --category unit --pattern "*setup_test_path*"

# Phase 2: Integration tests (non-Docker) for pattern validation
python tests/unified_test_runner.py --category integration --pattern "*integration_test_import*" --no-docker

# Phase 3: Staging GCP E2E tests for Golden Path
python tests/unified_test_runner.py --category e2e --pattern "*golden_path_integration_imports*" --env staging
```

## ✅ SUCCESS CRITERIA

**Tests FAIL initially (proving issue exists):**
- Integration test direct execution fails with import errors
- 1,458+ files identified missing setup_test_path()

**Tests PASS after applying pattern:**  
- Direct Python execution works with setup_test_path()
- Golden Path reliability restored in staging environment
- Integration test suite executes successfully

## 🎯 EXPECTED RESULTS

**Before Fix:** `ModuleNotFoundError: No module named 'test_framework'`  
**After Fix:** Imports succeed, tests executable, Golden Path reliable

## 📁 DETAILED TEST PLAN

Full test plan with test suites, fixtures, and implementation details: [`ISSUE_551_TEST_PLAN.md`](./ISSUE_551_TEST_PLAN.md)

---

**Next Steps:** Execute Phase 1 unit tests to validate setup_test_path() behavior and confirm the solution approach before systematic remediation.