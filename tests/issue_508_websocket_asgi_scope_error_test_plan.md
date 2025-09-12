# Issue #508 WebSocket ASGI Scope Error Test Plan

**Issue:** GCP-regression-P0-websocket-asgi-scope-error  
**Error:** `'URL' object has no attribute 'query_params'`  
**Location:** middleware_setup.py around line 576  
**Business Impact:** $500K+ ARR at risk from WebSocket connection failures  
**Priority:** P0 (Critical)

---

## Business Value Justification (BVJ)

- **Segment:** All (Free/Early/Mid/Enterprise/Platform) - affects core chat functionality  
- **Business Goal:** Stability - prevent WebSocket failures affecting Golden Path user flow  
- **Value Impact:** Critical WebSocket functionality must work to deliver AI-powered interactions  
- **Revenue Impact:** $500K+ ARR protection - chat is 90% of platform value

---

## Test Strategy Overview

### Phase 1: Error Reproduction Tests (MUST FAIL INITIALLY)
These tests MUST initially fail to prove the bug exists, then pass after fix implementation.

### Phase 2: Fix Validation Tests (MUST PASS AFTER FIX)
These tests validate that the fix works correctly and doesn't introduce regressions.

### Phase 3: Regression Prevention Tests (ONGOING PROTECTION)
These tests ensure the issue doesn't reoccur and protect Golden Path functionality.

---

## Test Categories

### 1. Unit Tests - ASGI Scope Handling (`tests/unit/middleware/`)

#### Test File: `test_websocket_asgi_scope_validation.py`

**Purpose:** Test ASGI scope validation logic in isolation  
**Infrastructure:** None required  
**Expected Pattern:** FAIL initially (reproduces bug), PASS after fix

##### Test Cases:

1. **test_asgi_scope_url_object_attribute_error_reproduction**
   - **Goal:** Reproduce the exact `'URL' object has no attribute 'query_params'` error
   - **Method:** Create malformed ASGI scope with Starlette URL object instead of FastAPI Request
   - **Assertion:** Should initially raise AttributeError, then be handled gracefully after fix
   - **Business Value:** Reproduces exact production error condition

2. **test_websocket_scope_vs_http_scope_distinction**
   - **Goal:** Test middleware correctly distinguishes WebSocket vs HTTP scopes
   - **Method:** Create ASGI scopes for both WebSocket and HTTP requests
   - **Assertion:** WebSocket scopes should bypass middleware, HTTP should process normally
   - **Business Value:** Prevents middleware interference with WebSocket connections

3. **test_invalid_asgi_scope_protection**
   - **Goal:** Test middleware handles invalid or corrupted ASGI scopes
   - **Method:** Create malformed ASGI scopes with missing required fields
   - **Assertion:** Should return safe error response instead of crashing
   - **Business Value:** Prevents cascading failures from malformed requests

4. **test_asgi_scope_type_detection_edge_cases**
   - **Goal:** Test edge cases in ASGI scope type detection
   - **Method:** Create scopes with unexpected type values or missing type field
   - **Assertion:** Should handle gracefully with appropriate logging
   - **Business Value:** Robust middleware behavior prevents service instability

5. **test_middleware_exception_wrapping_fix**
   - **Goal:** Test that middleware exceptions are properly wrapped and don't leak
   - **Method:** Trigger various middleware errors and verify response handling
   - **Assertion:** All errors should result in proper HTTP responses, not crashes
   - **Business Value:** Maintains service availability during error conditions

#### Test File: `test_middleware_stack_asgi_integration.py`

**Purpose:** Test middleware stack ASGI integration  
**Infrastructure:** None required  
**Expected Pattern:** FAIL initially, PASS after fix

6. **test_middleware_stack_scope_passing**
   - **Goal:** Test proper ASGI scope passing through middleware stack
   - **Method:** Mock middleware stack with various scope types
   - **Assertion:** Scopes should be passed correctly without attribute errors
   - **Business Value:** Ensures middleware chain doesn't corrupt request processing

7. **test_websocket_exclusion_middleware_asgi_handling**
   - **Goal:** Test WebSocket exclusion middleware ASGI scope handling
   - **Method:** Create WebSocket ASGI scopes and verify bypass logic
   - **Assertion:** WebSocket scopes should bypass HTTP middleware completely
   - **Business Value:** WebSocket connections work without HTTP middleware interference

### 2. Integration Tests - WebSocket Middleware Integration (`tests/integration/middleware/`)

#### Test File: `test_websocket_asgi_middleware_integration.py`

**Purpose:** Test WebSocket connections with full middleware stack  
**Infrastructure:** Local services (no Docker required)  
**Expected Pattern:** FAIL initially, PASS after fix

##### Test Cases:

8. **test_websocket_connection_with_middleware_stack**
   - **Goal:** Test WebSocket connection establishment with full middleware
   - **Method:** Create WebSocket connection through complete middleware chain
   - **Assertion:** Connection should succeed without ASGI scope errors
   - **Business Value:** Core WebSocket functionality works with all middleware

9. **test_websocket_upgrade_request_asgi_scope_handling**
   - **Goal:** Test WebSocket upgrade request ASGI scope processing
   - **Method:** Simulate WebSocket upgrade requests with various headers
   - **Assertion:** Upgrade should succeed without middleware interference
   - **Business Value:** WebSocket handshake completes successfully

10. **test_session_middleware_websocket_exclusion**
    - **Goal:** Test SessionMiddleware properly excludes WebSocket requests
    - **Method:** Send WebSocket requests that would normally require sessions
    - **Assertion:** WebSocket requests should bypass session processing
    - **Business Value:** Prevents SessionMiddleware from corrupting WebSocket connections

11. **test_auth_middleware_websocket_path_exclusions**
    - **Goal:** Test authentication middleware WebSocket path exclusions (27+ paths)
    - **Method:** Test all excluded WebSocket paths from FastAPIAuthMiddleware
    - **Assertion:** All WebSocket paths should bypass auth middleware
    - **Business Value:** WebSocket authentication works without HTTP auth interference

12. **test_cors_middleware_websocket_upgrade_handling**
    - **Goal:** Test CORS middleware handling of WebSocket upgrade requests
    - **Method:** Send WebSocket upgrade with various CORS headers
    - **Assertion:** CORS should allow WebSocket upgrades appropriately
    - **Business Value:** Cross-origin WebSocket connections work correctly

#### Test File: `test_middleware_error_recovery_integration.py`

**Purpose:** Test middleware error recovery and graceful degradation  
**Infrastructure:** Local services  
**Expected Pattern:** FAIL initially, PASS after fix

13. **test_asgi_scope_error_recovery_integration**
    - **Goal:** Test system recovery from ASGI scope errors
    - **Method:** Trigger ASGI scope errors and verify system continues functioning
    - **Assertion:** System should recover and handle subsequent requests correctly
    - **Business Value:** Service remains available despite individual request errors

14. **test_websocket_middleware_fallback_mechanisms**
    - **Goal:** Test fallback mechanisms when middleware fails
    - **Method:** Cause middleware failures and verify WebSocket still works
    - **Assertion:** WebSocket connections should succeed even with middleware issues
    - **Business Value:** Core chat functionality maintains availability

### 3. E2E Tests - GCP Staging Validation (`tests/e2e/staging/`)

#### Test File: `test_gcp_staging_websocket_asgi_validation.py`

**Purpose:** Validate WebSocket functionality in GCP staging environment  
**Infrastructure:** GCP Staging environment  
**Expected Pattern:** FAIL initially, PASS after fix

##### Test Cases:

15. **test_staging_websocket_connection_golden_path**
    - **Goal:** Test complete Golden Path WebSocket flow in staging
    - **Method:** Execute full user login → WebSocket connect → agent request flow
    - **Assertion:** All 5 critical WebSocket events should be delivered successfully
    - **Business Value:** Validates $500K+ ARR Golden Path functionality

16. **test_staging_websocket_asgi_error_reproduction**
    - **Goal:** Reproduce exact ASGI scope error in staging environment
    - **Method:** Send requests that trigger the specific middleware_setup.py error
    - **Assertion:** Should initially reproduce error, then work after fix
    - **Business Value:** Validates fix works in production-like environment

17. **test_staging_websocket_concurrent_connections**
    - **Goal:** Test multiple concurrent WebSocket connections in staging
    - **Method:** Establish multiple WebSocket connections simultaneously
    - **Assertion:** All connections should succeed without ASGI scope conflicts
    - **Business Value:** Validates multi-user WebSocket functionality

18. **test_staging_websocket_middleware_stack_complete**
    - **Goal:** Test complete middleware stack with WebSocket in staging
    - **Method:** Execute requests through all 7+ middleware layers with WebSocket
    - **Assertion:** WebSocket should work correctly through entire stack
    - **Business Value:** Full system integration validation

#### Test File: `test_gcp_staging_websocket_performance.py`

**Purpose:** Validate WebSocket performance after fix  
**Infrastructure:** GCP Staging environment  
**Expected Pattern:** Performance should improve after fix

19. **test_staging_websocket_response_time_improvement**
    - **Goal:** Validate WebSocket response times improve after ASGI fix
    - **Method:** Measure WebSocket connection and message processing times
    - **Assertion:** Response times should improve after fixing ASGI overhead
    - **Business Value:** Better user experience through faster WebSocket performance

20. **test_staging_websocket_error_rate_reduction**
    - **Goal:** Validate WebSocket error rates decrease after fix
    - **Method:** Monitor WebSocket connection success/failure rates
    - **Assertion:** Error rates should decrease significantly after fix
    - **Business Value:** More reliable chat functionality

### 4. Mission Critical Tests - Golden Path Protection (`tests/mission_critical/`)

#### Test File: `test_websocket_asgi_scope_golden_path_protection.py`

**Purpose:** Protect Golden Path from WebSocket ASGI scope regressions  
**Infrastructure:** Full Docker stack  
**Expected Pattern:** MUST ALWAYS PASS (deployment blocked if fails)

##### Test Cases:

21. **test_golden_path_websocket_asgi_scope_stability**
    - **Goal:** Ensure ASGI scope handling never breaks Golden Path
    - **Method:** Execute complete Golden Path flow with ASGI scope validation
    - **Assertion:** Golden Path must complete successfully with proper WebSocket events
    - **Business Value:** Protects 90% of platform business value

22. **test_websocket_asgi_regression_detection**
    - **Goal:** Detect any ASGI scope-related regressions immediately
    - **Method:** Execute WebSocket scenarios that previously triggered errors
    - **Assertion:** No ASGI scope errors should occur in any scenario
    - **Business Value:** Prevents regression of $500K+ ARR functionality

---

## Test Execution Strategy

### Phase 1: Reproduction Phase
1. Run all tests - expect 15+ failures (proves bug exists)
2. Document exact failure patterns and error messages
3. Verify reproduction matches production error logs

### Phase 2: Fix Implementation Phase  
1. Implement ASGI scope fixes in middleware_setup.py
2. Run tests iteratively during development
3. Validate fixes address root cause, not just symptoms

### Phase 3: Validation Phase
1. Run all tests - expect 22+ passes
2. Execute staging tests to validate production-like behavior
3. Run mission critical tests - must pass for deployment

### Phase 4: Regression Prevention
1. Add tests to CI/CD pipeline
2. Mission critical tests run on every commit
3. Staging tests run before every deployment

---

## Test Infrastructure Requirements

### Non-Docker Tests (Unit + Integration)
- **Advantages:** Fast execution, no infrastructure overhead
- **Requirements:** Python test environment, mock ASGI scopes
- **Execution:** `python tests/unified_test_runner.py --category unit integration --no-docker`

### Staging Tests (E2E)
- **Advantages:** Production-like environment, real error reproduction
- **Requirements:** GCP staging environment access, real WebSocket connections
- **Execution:** `python tests/unified_test_runner.py --category e2e --env staging --real-services`

### Mission Critical Tests
- **Advantages:** Deployment protection, Golden Path validation
- **Requirements:** Full Docker stack, real WebSocket infrastructure
- **Execution:** `python tests/mission_critical/test_websocket_asgi_scope_golden_path_protection.py`

---

## Success Criteria

### Reproduction Success (Phase 1)
- [ ] All reproduction tests initially FAIL with expected error patterns
- [ ] Error messages match production logs exactly
- [ ] Tests reproduce the specific `'URL' object has no attribute 'query_params'` error

### Fix Validation Success (Phase 2)
- [ ] All 22+ tests PASS after fix implementation
- [ ] No new errors introduced during fix
- [ ] WebSocket connections work reliably in all test scenarios

### Business Value Protection
- [ ] Golden Path user flow works end-to-end
- [ ] All 5 critical WebSocket events delivered successfully
- [ ] No regression in chat functionality performance
- [ ] $500K+ ARR functionality validated operational

### Deployment Readiness
- [ ] Mission critical tests pass 100%
- [ ] Staging environment validation successful
- [ ] No ASGI scope errors in production logs after deployment

---

## Test File Structure

```
tests/
├── unit/middleware/
│   ├── test_websocket_asgi_scope_validation.py (Tests 1-5)
│   └── test_middleware_stack_asgi_integration.py (Tests 6-7)
├── integration/middleware/
│   ├── test_websocket_asgi_middleware_integration.py (Tests 8-12)
│   └── test_middleware_error_recovery_integration.py (Tests 13-14)
├── e2e/staging/
│   ├── test_gcp_staging_websocket_asgi_validation.py (Tests 15-18)
│   └── test_gcp_staging_websocket_performance.py (Tests 19-20)
└── mission_critical/
    └── test_websocket_asgi_scope_golden_path_protection.py (Tests 21-22)
```

---

## Implementation Notes

### Test Framework Integration
- Use `SSotBaseTestCase` for all tests (SSOT compliance)
- Use `IsolatedEnvironment` for environment management
- Follow `TEST_CREATION_GUIDE.md` patterns
- All tests must include Business Value Justification

### Mock Strategy
- **Unit Tests:** Mock ASGI scopes and middleware components
- **Integration Tests:** Use real services, minimal mocking
- **E2E Tests:** No mocks, real GCP staging environment
- **Mission Critical:** Real services only, no bypassing allowed

### Error Detection Patterns
- **ASGI Scope Errors:** `'URL' object has no attribute 'query_params'`
- **WebSocket Failures:** Connection timeouts, 1011 errors
- **Middleware Conflicts:** `WebSocketDisconnect(1000)` during upgrade
- **Authentication Issues:** 403/401 errors on WebSocket upgrade

### Performance Monitoring
- Track WebSocket connection times
- Monitor error rates before/after fix
- Validate chat response times don't degrade
- Measure middleware processing overhead

---

## Execution Commands

### Development Testing
```bash
# Run reproduction tests (expect failures initially)
python tests/unified_test_runner.py --category unit --pattern "*asgi*" --expect-failures

# Run integration tests with staging
python tests/unified_test_runner.py --category integration --env staging --real-services

# Run E2E staging validation
python tests/unified_test_runner.py --category e2e --env staging --real-websockets
```

### Fix Validation Testing
```bash
# Run all Issue #508 tests after fix implementation
python tests/unified_test_runner.py --pattern "*508*" --real-services

# Run mission critical protection
python tests/mission_critical/test_websocket_asgi_scope_golden_path_protection.py

# Run complete validation suite
python tests/unified_test_runner.py --categories unit integration e2e --env staging --real-services --no-fast-fail
```

### CI/CD Integration
```bash
# Pre-deployment validation
python tests/unified_test_runner.py --mission-critical --env staging
python tests/unified_test_runner.py --category e2e --env staging --websocket-validation
```

---

## Expected Timeline

### Phase 1: Test Creation (2-3 days)
- Day 1: Unit tests (Tests 1-7)
- Day 2: Integration tests (Tests 8-14)  
- Day 3: E2E and Mission Critical tests (Tests 15-22)

### Phase 2: Error Reproduction (1 day)
- Execute all tests, verify failures match expected patterns
- Document exact error conditions and reproduction steps

### Phase 3: Fix Implementation (2-3 days)
- Implement ASGI scope fixes based on test feedback
- Iterate on tests during development
- Validate fix addresses root cause completely

### Phase 4: Validation & Deployment (1-2 days)
- Execute full test suite, verify all passes
- Staging environment validation
- Production deployment with monitoring

**Total Estimated Time:** 6-9 days for complete test plan execution and fix validation

---

*This test plan follows CLAUDE.md principles: Business Value First, Real Services Over Mocks, Golden Path Protection, and SSOT Compliance.*