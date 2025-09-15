# JWT Configuration Crisis Test Plan (Issue #681)

**Created:** 2025-09-13  
**Issue:** #681 JWT Configuration Crisis Blocking $50K MRR WebSocket  
**Business Impact:** Validates fix for WebSocket authentication failures in staging environment  
**Test Strategy:** Fail-first validation proving issue exists, then confirming fix works

## Executive Summary

Comprehensive test plan for Issue #681 JWT Configuration Crisis that blocks $50K MRR WebSocket functionality in staging environment. Tests are designed to **FAIL initially** to prove the issue exists, then **PASS after fix** to confirm resolution.

### Key Test Components
1. **Unit Tests:** JWT secret resolution failures in staging environment
2. **Integration Tests:** WebSocket authentication blocked by missing JWT secrets  
3. **Staging Tests:** Real environment validation of JWT configuration
4. **Failing Proof Tests:** Business impact demonstration (designed to fail initially)

## Test Suite Architecture

### 1. Unit Tests (`tests/unit/jwt_config/test_jwt_secret_staging_crisis_unit.py`)
**Purpose:** Validate JWT secret resolution logic in isolation  
**Coverage:** JWT secret manager, unified secrets manager, validation logic  
**Test Count:** 10+ focused unit tests

**Key Test Cases:**
- `test_staging_jwt_secret_missing_all_sources_fails()` - Proves Issue #681 exists
- `test_unified_secrets_manager_delegates_to_jwt_manager()` - Tests middleware integration path
- `test_jwt_configuration_validation_detects_staging_issues()` - Configuration validation
- `test_gcp_secret_manager_integration_staging()` - Tests expected fix path

**Expected Initial Behavior:** FAIL with "JWT secret not configured for staging environment"
**Expected After Fix:** PASS with valid JWT secret resolution

### 2. Integration Tests (`tests/integration/test_websocket_jwt_auth_crisis_integration.py`)  
**Purpose:** Validate WebSocket authentication with real components (no Docker)  
**Coverage:** WebSocket manager, auth middleware, Golden Path flow  
**Test Count:** 8+ integration scenarios

**Key Test Cases:**
- `test_websocket_connection_fails_with_missing_jwt_secret()` - WebSocket initialization blocked
- `test_websocket_middleware_auth_fails_missing_jwt()` - Middleware path failure (line 696)
- `test_golden_path_websocket_flow_jwt_blockage()` - Complete user flow blocked
- `test_websocket_revenue_functionality_integration()` - $50K MRR impact validation

**Expected Initial Behavior:** FAIL with WebSocket authentication errors
**Expected After Fix:** PASS with successful WebSocket initialization

### 3. Staging Environment Tests (`tests/staging/test_jwt_config_staging_environment.py`)
**Purpose:** Validate JWT configuration in actual staging environment  
**Coverage:** Real staging deployment, environment variables, GCP integration  
**Test Count:** 8+ staging-specific tests

**Key Test Cases:**
- `test_staging_environment_jwt_secret_resolution()` - Real staging JWT secret resolution
- `test_staging_environment_variable_presence()` - Diagnostic environment variable check
- `test_staging_websocket_auth_middleware_initialization()` - Real middleware initialization
- `test_staging_golden_path_jwt_validation()` - Golden Path validation in staging

**Expected Initial Behavior:** FAIL due to missing JWT_SECRET_STAGING/JWT_SECRET_KEY
**Expected After Fix:** PASS with environment variables or GCP Secret Manager

### 4. Failing Proof Tests (`tests/failing_demonstration/test_jwt_crisis_failing_proof.py`)
**Purpose:** Prove business impact and demonstrate fix effectiveness  
**Coverage:** Business impact validation, deployment confidence  
**Test Count:** 6+ proof-of-concept tests

**Key Test Cases:**
- `test_FAILS_jwt_secret_resolution_staging_crisis()` - Core Issue #681 proof
- `test_FAILS_fifty_thousand_mrr_websocket_functionality()` - Revenue impact proof
- `test_FAILS_golden_path_blocked_by_jwt_crisis()` - User experience impact
- `test_FAILS_staging_deployment_confidence_blocked()` - Deployment blockage

**Expected Initial Behavior:** DESIGNED TO FAIL - proves issue severity
**Expected After Fix:** PASS - proves issue resolution

## Test Execution Strategy

### Phase 1: Prove Issue Exists (Run BEFORE Fix)
```bash
# 1. Failing proof tests (should fail initially)
python -m pytest tests/failing_demonstration/test_jwt_crisis_failing_proof.py -v

# 2. Unit tests (should fail on staging JWT resolution)
python -m pytest tests/unit/jwt_config/test_jwt_secret_staging_crisis_unit.py -v

# 3. Integration tests (should fail on WebSocket auth)
python -m pytest tests/integration/test_websocket_jwt_auth_crisis_integration.py -v

# 4. Staging tests (should fail in real staging environment)
ENVIRONMENT=staging python -m pytest tests/staging/test_jwt_config_staging_environment.py -v
```

### Phase 2: Validate Fix Works (Run AFTER Fix)
```bash
# Run same test suite - should now PASS
python -m pytest tests/failing_demonstration/ tests/unit/jwt_config/ tests/integration/test_websocket_jwt_auth_crisis_integration.py -v

# Staging validation
ENVIRONMENT=staging python -m pytest tests/staging/test_jwt_config_staging_environment.py -v
```

## Fix Implementation Validation

### Expected Fix Approaches
1. **Environment Variables:** Set `JWT_SECRET_STAGING` or `JWT_SECRET_KEY` in GCP staging
2. **GCP Secret Manager:** Configure JWT secret via GCP Secret Manager
3. **Deployment Scripts:** Update `deploy_to_gcp.py` to inject JWT secrets

### Validation Criteria
- [ ] All failing proof tests now PASS
- [ ] Unit tests resolve JWT secrets successfully
- [ ] Integration tests initialize WebSocket authentication
- [ ] Staging tests validate real environment configuration
- [ ] No "JWT secret not configured for staging environment" errors
- [ ] WebSocket functionality operational in staging
- [ ] Golden Path user flow validated in staging

## Business Value Validation

### Revenue Protection ($50K MRR)
- [ ] WebSocket authentication works in staging
- [ ] Agent events can be sent via WebSocket
- [ ] Golden Path user flow (login → AI responses) operational
- [ ] No WebSocket 403 authentication failures

### Deployment Confidence
- [ ] Staging environment validates JWT configuration
- [ ] Golden Path can be tested in staging before production
- [ ] Production deployment confidence restored
- [ ] No JWT-related staging deployment failures

## Test Infrastructure Compliance

### SSOT Test Patterns
- All tests use `SSotBaseTestCase` and `SSotAsyncTestCase`
- No forbidden mocks in integration tests
- Real service integration where appropriate
- Environment isolation through `IsolatedEnvironment`

### Architecture Alignment
- Tests follow CLAUDE.md principles
- Business value justification (BVJ) documented
- Golden Path priority maintained
- WebSocket events validation included

## Success Metrics

### Technical Metrics
- **Test Pass Rate:** 100% after fix implementation
- **JWT Resolution:** Successful in all environments
- **WebSocket Auth:** No authentication failures
- **Configuration Validation:** All validation checks pass

### Business Metrics  
- **WebSocket Functionality:** $50K MRR features operational
- **Golden Path:** Complete user flow validated
- **Staging Confidence:** Deployment validation successful
- **Production Readiness:** No JWT-related blockers

## Maintenance and Evolution

### Test Maintenance
- Update tests if JWT secret manager logic changes
- Add new test cases for additional fix approaches
- Maintain staging environment test compatibility
- Keep business impact validation current

### Documentation Updates
- Update test execution guide with JWT crisis tests
- Document JWT configuration validation process
- Maintain test plan with fix implementation details
- Update business impact metrics as system evolves

---

**Test Plan Status:** COMPLETE  
**Next Steps:** Execute Phase 1 tests to prove issue, implement fix, execute Phase 2 to validate
**Expected Outcome:** Issue #681 resolution with full WebSocket functionality restoration