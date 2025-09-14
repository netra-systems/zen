# Issue #1037: Service-to-Service Authentication Regression - Comprehensive Test Plan

> **Issue Status:** P0 Critical - Service authentication regression causing 403 errors
> **Root Cause:** SERVICE_SECRET configuration inconsistency between auth service (uses SECRET_KEY) and backend (expects SERVICE_SECRET)
> **Business Impact:** $500K+ ARR at risk - Complete service communication breakdown
> **Test Strategy:** Create FAILING tests that reproduce exact 403 authentication patterns, then validate fixes

## Executive Summary

Based on analysis of Issue #1037 and recent E2E test results showing WebSocket service reporting 503 "service_not_ready", this comprehensive test plan creates targeted tests to reproduce the authentication regression. The core issue is a configuration mismatch where:

- **Auth service** expects and uses `SECRET_KEY` for service authentication
- **Backend service** expects and sends `SERVICE_SECRET` for authentication
- This mismatch results in 403 "Not authenticated" errors in service-to-service communication

### Test Strategy Principles

1. **FAILING TESTS FIRST** - All tests must fail initially to prove the regression exists
2. **NO DOCKER DEPENDENCIES** - Focus on unit, integration (non-Docker), and E2E staging tests only
3. **REAL AUTHENTICATION FLOWS** - Test actual service-to-service authentication mechanisms
4. **SSOT COMPLIANCE** - Follow established test patterns from TEST_CREATION_GUIDE.md and CLAUDE.md
5. **SERVICE SECRET FOCUS** - Target the specific SERVICE_SECRET vs SECRET_KEY configuration inconsistency

## Test Categories & Implementation Plan

### 1. Unit Tests - SERVICE_SECRET Configuration Validation

**Goal:** Test the core configuration inconsistency at the component level
**Infrastructure:** None required
**Expected Result:** All tests FAIL initially, demonstrating the configuration mismatch

#### Test File: `tests/unit/auth/test_service_secret_configuration_mismatch.py`

**Purpose:** Reproduce the exact SERVICE_SECRET vs SECRET_KEY configuration inconsistency

```python
class TestServiceSecretConfigurationMismatch(SSotBaseTestCase):
    def test_auth_service_expects_secret_key_not_service_secret(self):
        """MUST FAIL: Auth service configuration expects SECRET_KEY, not SERVICE_SECRET"""
        # This test reproduces the core configuration mismatch

    def test_backend_sends_service_secret_not_secret_key(self):
        """MUST FAIL: Backend sends SERVICE_SECRET but auth service expects SECRET_KEY"""

    def test_service_authentication_header_mismatch(self):
        """MUST FAIL: Service headers use SERVICE_SECRET but auth service validates against SECRET_KEY"""
```

#### Test File: `tests/unit/auth/test_jwt_validation_secret_inconsistency.py`

**Purpose:** Test JWT validation with mismatched secrets

```python
class TestJWTValidationSecretInconsistency(SSotBaseTestCase):
    def test_jwt_signed_with_service_secret_validated_with_secret_key(self):
        """MUST FAIL: JWT signed with SERVICE_SECRET cannot be validated with SECRET_KEY"""

    def test_service_token_generation_validation_mismatch(self):
        """MUST FAIL: Service token generation uses different secret than validation"""
```

### 2. Integration Tests - Service Communication Failures (Non-Docker)

**Goal:** Test complete service-to-service authentication flows that reproduce 403 errors
**Infrastructure:** Local services running (no Docker containers)
**Expected Result:** Reproduce exact 403 authentication failure patterns

#### Test File: `tests/integration/auth/test_service_secret_authentication_regression.py`

**Purpose:** Reproduce exact authentication regression in service communication

```python
class TestServiceSecretAuthenticationRegression(BaseIntegrationTest):
    @pytest.mark.integration
    @pytest.mark.auth_regression_reproduction
    async def test_backend_auth_service_403_reproduction(self):
        """MUST FAIL: Reproduce exact 403 error from backend to auth service communication"""
        # Configure backend with SERVICE_SECRET
        # Configure auth service with SECRET_KEY (different value)
        # Make service-to-service request
        # Assert 403 authentication failure occurs

    async def test_websocket_service_authentication_failure(self):
        """MUST FAIL: Reproduce WebSocket service 503 'service_not_ready' error pattern"""
        # Based on recent E2E test results showing WebSocket service issues

    async def test_cross_service_jwt_validation_failure(self):
        """MUST FAIL: Reproduce JWT validation failures between services"""
        # Test complete JWT validation flow with secret mismatch
```

#### Test File: `tests/integration/auth/test_service_authentication_circuit_breaker.py`

**Purpose:** Test authentication failure cascade effects

```python
class TestServiceAuthenticationCircuitBreaker(BaseIntegrationTest):
    async def test_authentication_failure_cascades(self):
        """MUST FAIL: Multiple auth failures trigger circuit breaker"""

    async def test_service_degradation_from_auth_failures(self):
        """MUST FAIL: Service functionality degrades due to auth failures"""
```

### 3. E2E Staging Tests - Real Environment Authentication Validation

**Goal:** Test authentication in real GCP staging environment with actual secrets
**Infrastructure:** GCP Cloud Run staging environment
**Expected Result:** Validate that authentication failures occur in production-like environment

#### Test File: `tests/e2e/gcp_staging/test_service_secret_staging_validation.py`

**Purpose:** Validate SERVICE_SECRET configuration in real staging environment

```python
class TestServiceSecretStagingValidation(BaseE2ETest):
    @pytest.mark.e2e
    @pytest.mark.staging
    @pytest.mark.auth_regression
    async def test_staging_service_secret_consistency(self):
        """MUST FAIL: Validate SERVICE_SECRET consistency across staging services"""
        # Test that all staging services use consistent secret configuration

    async def test_staging_websocket_authentication(self):
        """Test WebSocket authentication in staging (addresses recent 503 errors)"""
        # Based on recent test results showing WebSocket service issues

    async def test_staging_service_to_service_communication(self):
        """MUST FAIL: Test complete service communication in staging environment"""
        # End-to-end test of service authentication in real GCP environment
```

#### Test File: `tests/e2e/gcp_staging/test_golden_path_service_authentication.py`

**Purpose:** Ensure service authentication doesn't break Golden Path functionality

```python
class TestGoldenPathServiceAuthentication(BaseE2ETest):
    async def test_golden_path_with_service_authentication(self):
        """Test Golden Path user flow with service authentication requirements"""
        # Ensure user authentication works even if service authentication has issues

    async def test_websocket_events_with_authentication_failure(self):
        """Test WebSocket events when service authentication fails"""
        # Critical for $500K+ ARR chat functionality
```

## Test Implementation Standards

### SSOT Compliance Requirements

- **Base Test Classes:** All tests inherit from `SSotBaseTestCase` or `BaseIntegrationTest`
- **Environment Management:** Use `IsolatedEnvironment` for all environment access
- **Real Services:** Integration tests use real services, no mocks except for external dependencies
- **Test Runner:** Execute via `python tests/unified_test_runner.py` only

### Configuration Testing Strategy

```python
# Example pattern for testing SERVICE_SECRET vs SECRET_KEY mismatch
def test_service_secret_mismatch_reproduction(self):
    """Reproduce the core Issue #1037 configuration mismatch"""

    # Configure backend with SERVICE_SECRET
    with patch.object(get_env(), 'get') as mock_backend_env:
        mock_backend_env.side_effect = lambda key, default=None: {
            "SERVICE_SECRET": "backend-production-secret-123",
            "SERVICE_ID": "netra-backend"
        }.get(key, default)

        # Configure auth service with SECRET_KEY (different!)
        with patch('auth_service.auth_core.auth_environment.get_env') as mock_auth_env:
            mock_auth_env.return_value.get.side_effect = lambda key, default=None: {
                "SECRET_KEY": "auth-production-secret-456",  # Different!
                "JWT_SECRET_KEY": "jwt-secret-789"
            }.get(key, default)

            # Test service authentication - MUST FAIL
            auth_client = AuthServiceClient()

            # This should reproduce the 403 authentication failure
            with pytest.raises(AuthServiceValidationError) as exc_info:
                await auth_client.validate_service_request({
                    "service_id": "netra-backend",
                    "service_secret": "backend-production-secret-123"  # Won't match SECRET_KEY
                })

            assert "403" in str(exc_info.value) or "Not authenticated" in str(exc_info.value)
```

## Expected Failure Patterns

### 1. HTTP Status Codes
- **403 Forbidden** - Primary authentication failure pattern
- **401 Unauthorized** - Token validation failures
- **503 Service Unavailable** - Service degradation from auth failures (WebSocket pattern)

### 2. Error Messages
- "403: Not authenticated" (exact production error)
- "service:netra-backend" authentication failures
- "Invalid service credentials" or similar auth errors
- Circuit breaker related messages

### 3. Service Behaviors
- Authentication requests timing out
- Circuit breakers opening due to repeated failures
- WebSocket connections failing to establish
- Database session creation failures for service users

## Test Execution Strategy

### Phase 1: Unit Test Reproduction
```bash
# Execute unit tests to reproduce configuration mismatch
python tests/unified_test_runner.py --category unit --pattern "*service*secret*"
python tests/unified_test_runner.py --category unit --pattern "*auth*regression*"
```

### Phase 2: Integration Test Validation
```bash
# Execute integration tests with real services
python tests/unified_test_runner.py --category integration --pattern "*service*auth*regression*" --real-services
python tests/unified_test_runner.py --category integration --pattern "*auth*secret*" --real-services
```

### Phase 3: E2E Staging Verification
```bash
# Execute E2E tests in staging environment
python tests/unified_test_runner.py --category e2e --env staging --pattern "*service*secret*"
python tests/unified_test_runner.py --category e2e --env staging --pattern "*websocket*auth*"
```

### Complete Regression Test Suite
```bash
# Run all Issue #1037 authentication regression tests
python tests/unified_test_runner.py --pattern "*service*secret*auth*regression*" --real-services --env staging
```

## Success Criteria

### 1. Reproduction Success
- [ ] At least 5 unit tests reproduce the SERVICE_SECRET vs SECRET_KEY mismatch
- [ ] At least 3 integration tests reproduce 403 authentication failures
- [ ] At least 2 E2E tests demonstrate the issue in staging environment

### 2. Root Cause Validation
- [ ] Tests clearly demonstrate SERVICE_SECRET vs SECRET_KEY configuration inconsistency
- [ ] Authentication flows show exactly where the mismatch occurs
- [ ] Error patterns match production logs from Issue #1037

### 3. Coverage Completeness
- [ ] Unit tests cover configuration validation and JWT processing
- [ ] Integration tests cover complete service-to-service authentication flows
- [ ] E2E tests validate behavior in production-like GCP environment
- [ ] WebSocket authentication specifically addressed (recent 503 errors)

### 4. Business Value Protection
- [ ] Tests validate $500K+ ARR Golden Path functionality remains intact
- [ ] WebSocket events continue working for chat functionality
- [ ] Service degradation patterns are documented and tested

## Quality Assurance Standards

### Test Reliability
- **No False Positives:** Tests only pass when authentication actually works
- **Real Authentication:** Use actual auth mechanisms, minimal mocking
- **Environment Parity:** Staging tests use identical configuration to production
- **Comprehensive Logging:** All failures provide detailed authentication context

### Business Impact Validation
- **Segment:** Platform/Infrastructure (affects all customer tiers)
- **Business Goal:** System Stability - Prevent complete service communication breakdown
- **Value Impact:** Protects $500K+ ARR core platform functionality
- **Revenue Impact:** Prevents service outage affecting all customers

## Implementation Timeline

### Immediate (Next Steps)
1. **Unit Tests Creation** - Reproduce SERVICE_SECRET configuration mismatch
2. **Integration Tests Setup** - Test service-to-service communication failures
3. **E2E Staging Tests** - Validate authentication in real GCP environment

### Validation Phase
4. **Test Execution** - Run complete regression test suite
5. **Issue Reproduction Confirmation** - Validate all tests fail as expected
6. **Fix Validation Preparation** - Tests ready to validate Issue #1037 resolution

---

**Test Plan Created:** 2025-09-14
**Issue Priority:** P0 Critical
**Business Impact:** $500K+ ARR Protection
**Expected Outcome:** Complete reproduction of 403 service authentication regression for resolution validation