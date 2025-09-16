# Issue #631 Test Plan: HTTP 403 WebSocket Authentication Failures

## Overview

**Issue**: WebSocket connections failing with HTTP 403 errors due to authentication service integration failures.

**Root Cause Analysis**:
- Missing AUTH_SERVICE_URL configuration preventing backend from communicating with auth service
- Service-to-service authentication validation failures
- WebSocket middleware rejecting connections during handshake
- JWT token validation pipeline breakdown

**Business Impact**: $500K+ ARR chat functionality blocked by authentication failures

## Test Strategy

This test plan follows SSOT testing patterns and focuses on non-Docker tests that can reproduce and validate the HTTP 403 issue.

### Test Categories

#### 1. Unit Tests - Configuration Validation
**Purpose**: Ensure AUTH_SERVICE_URL configuration is properly loaded and validated
**Location**: `tests/unit/issue_631/`

#### 2. Integration Tests - Service Communication  
**Purpose**: Test backend-to-auth service communication without Docker dependencies
**Location**: `tests/integration/issue_631/`

#### 3. E2E Staging Tests - Live Environment Reproduction
**Purpose**: Reproduce HTTP 403 errors in actual staging environment
**Location**: `tests/e2e/staging/issue_631/`

## Detailed Test Specifications

### Unit Test Suite: Configuration and Auth Client Validation

**File**: `tests/unit/issue_631/test_auth_service_configuration_unit.py`

**Test Cases**:
1. `test_auth_service_url_configuration_loaded` - Verify AUTH_SERVICE_URL is loaded from environment
2. `test_auth_service_url_missing_handling` - Test behavior when AUTH_SERVICE_URL is missing
3. `test_auth_client_initialization_with_valid_url` - Auth client initializes correctly with valid URL
4. `test_auth_client_initialization_with_invalid_url` - Auth client fails gracefully with invalid URL
5. `test_jwt_validation_configuration` - JWT validation settings are correctly configured

**Expected Behavior**: These tests should FAIL until AUTH_SERVICE_URL configuration is properly implemented.

### Integration Test Suite: Service-to-Service Authentication

**File**: `tests/integration/issue_631/test_websocket_auth_service_integration.py`

**Test Cases**:
1. `test_backend_auth_service_communication` - Test backend can communicate with auth service
2. `test_jwt_token_validation_integration` - End-to-end JWT token validation through auth service
3. `test_websocket_middleware_auth_flow` - WebSocket auth middleware integration with auth service
4. `test_403_error_generation_and_logging` - Verify 403 errors are properly generated and logged
5. `test_auth_service_unavailable_handling` - Test graceful degradation when auth service unavailable

**Test Infrastructure**:
- Use real auth service instances (non-Docker)
- Mock WebSocket connections for controlled testing
- Real JWT tokens from auth service
- Network timeouts and retry testing

### E2E Staging Test Suite: Live Environment Reproduction

**File**: `tests/e2e/staging/issue_631/test_websocket_403_reproduction_staging.py`

**Test Cases**:
1. `test_reproduce_http_403_websocket_handshake` - Exact reproduction of staging 403 errors
2. `test_websocket_connection_with_valid_jwt` - Successful connection with proper auth
3. `test_websocket_connection_with_invalid_jwt` - Expected 403 with invalid JWT
4. `test_websocket_connection_timeout_scenarios` - Auth service timeout handling
5. `test_auth_service_url_staging_configuration` - Verify staging AUTH_SERVICE_URL configuration

**Staging Test Requirements**:
- Use actual GCP staging environment
- Real WebSocket connections to staging backend
- Live auth service integration
- Monitor actual 403 response codes and timing

## Test Implementation Strategy

### Phase 1: Unit Tests (FAILING tests to drive development)
```bash
# Create unit tests that expose configuration issues
python -m pytest tests/unit/issue_631/test_auth_service_configuration_unit.py -v

# Expected: Tests should FAIL showing AUTH_SERVICE_URL missing
```

### Phase 2: Integration Tests (Service communication validation)
```bash
# Test service-to-service authentication
python -m pytest tests/integration/issue_631/test_websocket_auth_service_integration.py -v

# Expected: Tests should FAIL showing communication breakdown
```

### Phase 3: E2E Staging Tests (Live issue reproduction)
```bash
# Reproduce actual HTTP 403 errors in staging
python -m pytest tests/e2e/staging/issue_631/test_websocket_403_reproduction_staging.py -v

# Expected: Tests should reproduce exact 403 failure pattern
```

## Success Criteria

### Definition of Done
1. **Configuration Tests Pass**: AUTH_SERVICE_URL properly configured and loaded
2. **Integration Tests Pass**: Backend can successfully communicate with auth service
3. **WebSocket Auth Works**: 403 errors resolved, successful WebSocket connections
4. **Staging Tests Pass**: Live environment shows resolved authentication flow
5. **Error Handling Verified**: Proper error logging and graceful degradation

### Test Coverage Metrics
- Configuration validation: 100% coverage
- Auth service integration: 95% coverage
- WebSocket auth middleware: 90% coverage
- Error scenarios: 85% coverage

## SSOT Testing Compliance

Following established SSOT testing patterns:
- All tests inherit from `SSotBaseTestCase`
- Use `test_framework.ssot` utilities for consistent testing
- No Docker dependencies in unit/integration tests
- Real services for staging E2E tests
- Proper error logging and validation

## Risk Assessment

**High Risk Areas**:
- Service-to-service authentication configuration
- WebSocket handshake timing and retries
- JWT token validation pipeline
- Network connectivity between services

**Mitigation Strategy**:
- Comprehensive error logging in tests
- Multiple test environments (unit, integration, staging)
- Real service integration testing
- Clear failure reproduction paths

---

**Created**: 2025-09-12  
**Issue**: #631 HTTP 403 WebSocket Authentication Failures  
**Business Priority**: Critical - $500K+ ARR functionality blocked  
**Test Strategy**: FAILING tests to drive configuration fix implementation