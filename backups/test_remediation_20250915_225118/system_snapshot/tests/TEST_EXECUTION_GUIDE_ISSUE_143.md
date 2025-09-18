# Test Execution Guide for Issue #143: Golden Path P0 Critical Test Validation

**CRITICAL MISSION:** Reproduce and validate infrastructure gaps preventing Golden Path verification  
**BUSINESS IMPACT:** $500K+ MRR at risk due to unverified chat functionality  
**EXECUTION STATUS:** Ready for immediate implementation

## Quick Start Commands

### Phase 1: Reproduce Issues (Expected Failures)
```bash
# Run infrastructure validation tests - EXPECT FAILURES
python -m pytest tests/unit/infrastructure/test_health_check_url_validation.py -v --tb=short
python -m pytest tests/integration/test_jwt_configuration_validation.py -v  
python -m pytest tests/critical/test_infrastructure_validation_gaps_reproduction.py -v

# Full reproduction suite
python -m pytest -m "must_fail_initially" -v --tb=long
```

### Phase 2: Staging Environment Validation  
```bash
# Set up staging environment variables
export E2E_TEST_ENV="staging"
export STAGING_API_URL="https://api.staging.netrasystems.ai"
export STAGING_WEBSOCKET_URL="wss://api.staging.netrasystems.ai/ws"
export STAGING_AUTH_URL="https://auth.staging.netrasystems.ai"
export STAGING_FRONTEND_URL="https://app.staging.netrasystems.ai"

# Run E2E validation on staging
python -m pytest tests/e2e/test_golden_path_infrastructure_validation.py --env=staging -v
```

### Phase 3: Full Validation After Fixes
```bash
# Run all infrastructure validation tests after fixes - EXPECT SUCCESS
python -m pytest -m "infrastructure_validation" -v --tb=short --capture=no
```

## Test Categories Overview

| Category | Purpose | Environment | Expected Initial Result |
|----------|---------|-------------|------------------------|
| **Unit Tests** | Infrastructure component validation | Local only | MUST FAIL - prove issues exist |
| **Integration Tests** | Service communication validation | Local (no Docker) | MUST FAIL - show config issues |
| **E2E Tests** | Complete Golden Path on staging | GCP Staging | MUST FAIL - infrastructure broken |
| **Critical Tests** | Specific issue reproduction | Local/Staging | MUST FAIL - validate gaps |

## Detailed Test Execution Instructions

### 1. Unit Tests: Infrastructure Component Validation

**Location:** `tests/unit/infrastructure/test_health_check_url_validation.py`

**Purpose:** Validate URL parsing and health check logic without external dependencies

**Expected Failures:**
- "Request URL missing protocol" errors
- URL validation logic gaps  
- Health check URL construction issues

```bash
# Run unit tests with detailed output
python -m pytest tests/unit/infrastructure/ -v --tb=long

# Run specific test methods
python -m pytest tests/unit/infrastructure/test_health_check_url_validation.py::TestHealthCheckURLValidation::test_staging_url_protocol_missing_reproduction -v

# Run with coverage to see code paths
python -m pytest tests/unit/infrastructure/ --cov=netra_backend.app.core --cov-report=html
```

**Success Criteria (After Fixes):**
- All URL validation tests pass
- No "missing protocol" errors
- Health check URL construction works correctly

### 2. Integration Tests: JWT Configuration Validation

**Location:** `tests/integration/test_jwt_configuration_validation.py`

**Purpose:** Test JWT configuration synchronization between services (no Docker)

**Expected Failures:**
- JWT secret mismatches between services
- Environment variable inconsistencies
- Token format incompatibilities

```bash
# Run JWT configuration tests
python -m pytest tests/integration/test_jwt_configuration_validation.py -v

# Test specific JWT scenarios
python -m pytest tests/integration/test_jwt_configuration_validation.py::TestJWTConfigurationSynchronization::test_jwt_secret_synchronization_failure_reproduction -v

# Test with environment variable isolation
python -m pytest tests/integration/test_jwt_configuration_validation.py --capture=no
```

**Success Criteria (After Fixes):**
- JWT secrets synchronized across all services
- No JWT configuration warnings in logs
- Token validation works consistently

### 3. E2E Tests: Golden Path Staging Validation

**Location:** `tests/e2e/test_golden_path_infrastructure_validation.py`

**Purpose:** Validate complete Golden Path infrastructure works on real GCP staging

**Prerequisites:**
```bash
# Required environment variables
export STAGING_TEST_JWT_TOKEN="<your-staging-jwt-token>"
export E2E_BYPASS_KEY="<your-staging-bypass-key>"

# Verify staging access
curl -I https://api.staging.netrasystems.ai/health
curl -I https://auth.staging.netrasystems.ai/health
```

**Expected Failures:**
- WebSocket 1011 internal errors on staging
- Authentication failures in GCP Load Balancer  
- Service dependency timeout failures
- Complete Golden Path user flow broken

```bash
# Run complete staging validation
python -m pytest tests/e2e/test_golden_path_infrastructure_validation.py --env=staging -v --tb=long

# Run specific Golden Path test
python -m pytest tests/e2e/test_golden_path_infrastructure_validation.py::TestGoldenPathInfrastructureValidation::test_complete_golden_path_user_flow_staging -v

# Run WebSocket-specific staging tests
python -m pytest tests/e2e/test_golden_path_infrastructure_validation.py::TestGoldenPathInfrastructureValidation::test_websocket_authentication_staging_infrastructure -v
```

**Success Criteria (After Fixes):**
- Complete Golden Path user flow works on staging
- WebSocket connections establish successfully  
- All 5 critical WebSocket events delivered
- No infrastructure-level failures

### 4. Critical Tests: Infrastructure Gap Reproduction

**Location:** `tests/critical/test_infrastructure_validation_gaps_reproduction.py`

**Purpose:** Reproduce specific infrastructure validation gaps from issue #143

**Expected Failures:**
- Deployment health check failures reproduced exactly
- GCP Load Balancer header stripping detected
- Cloud Run race conditions reproduced
- Test infrastructure systematic failures demonstrated

```bash
# Run critical reproduction tests
python -m pytest tests/critical/test_infrastructure_validation_gaps_reproduction.py -v

# Run specific reproduction scenarios
python -m pytest tests/critical/test_infrastructure_validation_gaps_reproduction.py::TestInfrastructureValidationGapsReproduction::test_deployment_health_check_failure_reproduction -v

python -m pytest tests/critical/test_infrastructure_validation_gaps_reproduction.py::TestInfrastructureValidationGapsReproduction::test_gcp_load_balancer_header_stripping_detection -v
```

**Success Criteria (After Fixes):**
- All reproduction tests pass (no longer reproduce issues)
- Deployment health checks work correctly
- Load balancer forwards headers properly
- No race conditions in Cloud Run

## Test Execution Workflow

### Step 1: Validate Test Setup
```bash
# Check Python environment
python --version  # Should be 3.11+
pip install -r requirements.txt
pip install -r test-requirements.txt

# Check test discovery
python -m pytest --collect-only -m "infrastructure_validation"

# Verify test infrastructure
python -c "from shared.isolated_environment import get_env; print('Environment setup OK')"
```

### Step 2: Execute Reproduction Tests (Phase 1)
```bash
# Run all reproduction tests - EXPECT FAILURES
python -m pytest -m "must_fail_initially" -v --tb=short | tee reproduction_results.log

# Analyze failures
grep -E "FAILED|ERROR" reproduction_results.log
```

**Expected Results:**
- Multiple test failures demonstrating infrastructure issues
- Clear error messages showing validation gaps
- Specific reproduction of "Request URL missing protocol" errors

### Step 3: Infrastructure Fixes (Implementation Phase)
Based on test failures, implement fixes:

1. **URL Protocol Issues:** Fix URL construction logic in health checks
2. **JWT Configuration:** Synchronize JWT secrets across services  
3. **GCP Load Balancer:** Update Terraform configuration for header forwarding
4. **WebSocket Authentication:** Fix authentication flow on staging

### Step 4: Validation After Fixes (Phase 2)
```bash
# Run same tests after fixes - EXPECT SUCCESS
python -m pytest -m "infrastructure_validation" -v --tb=short | tee validation_results.log

# Verify all tests pass
grep -c "PASSED" validation_results.log
grep -c "FAILED" validation_results.log  # Should be 0
```

### Step 5: Staging End-to-End Validation
```bash
# Full Golden Path validation on staging
python -m pytest tests/e2e/test_golden_path_infrastructure_validation.py \
    --env=staging \
    -v \
    --tb=long \
    --capture=no | tee staging_validation_results.log

# Verify Golden Path success
grep "Golden Path.*success" staging_validation_results.log
```

## Test Results Interpretation

### Failure Analysis Pattern

**Phase 1 (Expected Failures):**
```
EXPECTED FAILURE PATTERN:
✗ test_staging_url_protocol_missing_reproduction - "Request URL missing protocol"  
✗ test_jwt_secret_synchronization_failure_reproduction - "JWT secrets don't match"
✗ test_complete_golden_path_user_flow_staging - "WebSocket 1011 internal error"
✗ test_deployment_health_check_failure_reproduction - "URL protocol missing"

Status: GOOD - Issues properly reproduced and identified
```

**Phase 2 (After Fixes):**
```
SUCCESS PATTERN:
✓ test_staging_url_protocol_missing_reproduction - All URLs have proper protocols
✓ test_jwt_secret_synchronization_failure_reproduction - JWT configuration synchronized  
✓ test_complete_golden_path_user_flow_staging - Golden Path works end-to-end
✓ test_deployment_health_check_failure_reproduction - Deployment health checks pass

Status: SUCCESS - All infrastructure issues resolved
```

### Performance Metrics

**Test Execution Time Targets:**
- Unit Tests: <30 seconds total
- Integration Tests: <2 minutes total  
- E2E Tests: <10 minutes total
- Critical Tests: <1 minute total

**Infrastructure Validation Metrics:**
- URL validation success rate: 100%
- JWT configuration synchronization: 100%
- WebSocket connection success rate: >99%
- Golden Path completion rate: 100%

## Troubleshooting Common Issues

### Test Environment Issues

**Issue:** Import errors for test modules
```bash
# Solution: Add project root to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python -m pytest tests/unit/infrastructure/ -v
```

**Issue:** Missing staging environment variables
```bash
# Solution: Set required variables
export STAGING_API_URL="https://api.staging.netrasystems.ai"
export STAGING_WEBSOCKET_URL="wss://api.staging.netrasystems.ai/ws"
export STAGING_AUTH_URL="https://auth.staging.netrasystems.ai"
```

**Issue:** Staging services not accessible
```bash
# Check connectivity
curl -I https://api.staging.netrasystems.ai/health
nslookup api.staging.netrasystems.ai

# Check authentication
curl -H "Authorization: Bearer $STAGING_TEST_JWT_TOKEN" \
     https://api.staging.netrasystems.ai/api/health
```

### Test Execution Issues

**Issue:** Tests not failing as expected in Phase 1
```
Cause: Infrastructure issues may already be partially fixed
Solution: Review test scenarios and adjust expectations
Action: Focus on tests that do fail and analyze their patterns
```

**Issue:** Staging E2E tests timeout
```
Cause: Staging environment may be unavailable or slow
Solution: Increase timeouts and verify service health
Action: Run staging connectivity test first
```

**Issue:** JWT configuration tests pass unexpectedly
```  
Cause: JWT secrets may already be synchronized
Solution: Verify current configuration state
Action: Check environment variables across services
```

## Success Criteria Validation

### Complete Success Checklist

**Infrastructure Validation:**
- [ ] All URL protocol validation tests pass
- [ ] JWT configuration synchronized across services
- [ ] No "Request URL missing protocol" errors in any logs
- [ ] Health check endpoints return 200 OK for all services

**Golden Path Validation:**
- [ ] Complete user flow works end-to-end on staging
- [ ] WebSocket connections establish successfully (no 1011 errors)
- [ ] All 5 critical WebSocket events delivered reliably
- [ ] Agent execution completes with actionable results
- [ ] Response time <60 seconds for complete flow

**Test Infrastructure Validation:**
- [ ] All tests execute without false positives
- [ ] No test infrastructure systematic failures
- [ ] Real service testing works properly
- [ ] Staging environment fully accessible

**Business Value Validation:**
- [ ] $500K+ MRR chat functionality verified operational
- [ ] User experience transparent with real-time updates
- [ ] AI responses contain actionable insights
- [ ] No silent failures masking issues

## Next Steps After Test Execution

### If Tests Fail as Expected (Phase 1)
1. **Document Failure Patterns:** Capture exact error messages and scenarios
2. **Prioritize Fixes:** Start with infrastructure issues (URL protocols, JWT config)  
3. **Implement Solutions:** Fix identified validation gaps systematically
4. **Re-run Validation:** Execute Phase 2 testing to verify fixes

### If Tests Pass Unexpectedly (Phase 1)
1. **Investigate Pre-Existing Fixes:** Check if issues were already resolved
2. **Validate Test Scenarios:** Ensure tests properly reproduce expected issues
3. **Focus on Remaining Gaps:** Identify any remaining infrastructure issues
4. **Proceed to Staging:** Move to E2E validation on staging environment

### After All Tests Pass (Phase 2)
1. **Deploy to Production:** Infrastructure validation complete
2. **Monitor Golden Path:** Set up monitoring for continued validation
3. **Update Documentation:** Document resolved infrastructure issues
4. **Establish CI/CD Validation:** Include tests in deployment pipeline

## Conclusion

This test execution guide provides a systematic approach to reproducing, validating, and resolving the infrastructure validation gaps identified in issue #143. The failure-first testing approach ensures that we properly identify and fix the actual issues preventing Golden Path verification.

**Key Success Indicator:** When all tests pass and the Golden Path user flow works reliably on staging with consistent delivery of all 5 critical WebSocket events, the $500K+ MRR at risk will be protected through verified infrastructure functionality.