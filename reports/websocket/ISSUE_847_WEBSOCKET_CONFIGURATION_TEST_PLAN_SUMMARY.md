# Issue #847 WebSocket Configuration Test Plan - Executive Summary

**Issue:** #847 - WebSocket Connection Configuration Issue  
**Status:** TEST PLAN COMPLETE - Ready for Implementation  
**Business Impact:** Blocks WebSocket agent events (90% of platform value)  

## 🚨 Root Cause Identified

**Configuration Variable Mapping Gap:**
- Docker backend exposed on port **8002** (`ALPINE_TEST_BACKEND_PORT=8002`)
- Tests hardcoded to **8000** in 100+ locations  
- `TestContext` reads `BACKEND_URL` but test environment sets `TEST_BACKEND_URL`
- Staging fallback exists but variable mapping prevents utilization

## 📋 Test Plan Created

**File:** `/Users/anthony/Desktop/netra-apex/ISSUE_847_WEBSOCKET_CONFIGURATION_TEST_PLAN.md`

### Test Categories:
1. **Unit Tests** - Environment variable resolution (12 tests planned)
2. **Integration Tests** - Service discovery and fallback (8 tests planned) 
3. **TestContext Tests** - Configuration loading validation (4 tests planned)
4. **Gap Demonstration** - Failing tests that prove the issue (2 tests planned)

### Expected Results:
- **Before Fix**: 14/26 tests pass (configuration gap causes failures)
- **After Fix**: 26/26 tests pass (all configuration scenarios work)

## 🔧 Key Files to Fix

**Primary Issue Location:**
- `/test_framework/test_context.py:152` - `BACKEND_URL` hardcoded, needs mapping

**Docker Port Configuration:**
- `/docker/docker-compose.alpine-test.yml:171` - Maps to port 8002

**Staging Fallback:**
- `/.env.staging.e2e` - Contains staging URLs but not utilized

## 🚀 Implementation Strategy

1. **Create failing tests** that demonstrate the configuration gap
2. **Implement variable mapping** `TEST_BACKEND_URL` → `BACKEND_URL` in TestContext
3. **Add staging fallback integration** when Docker unavailable
4. **Verify all tests pass** after configuration fix

## 📊 Business Value Protection

- **Revenue at Risk**: $500K+ ARR dependent on WebSocket functionality
- **User Impact**: Chat experience (90% of platform value) affected
- **Resolution Time**: Test-driven approach ensures comprehensive fix

---

**Next Steps:**
1. ✅ **Test Plan Complete** - Comprehensive plan created
2. 🔄 **Implementation Phase** - Create failing tests first
3. ⏳ **Fix Implementation** - Address variable mapping gap
4. ⏳ **Validation** - All tests pass confirming issue resolved

**Test Execution:**
```bash
# Run configuration tests (should initially fail)
python tests/unified_test_runner.py --file-pattern "*websocket_configuration*"
```