# CORS Regression Prevention Test Suite

This comprehensive test suite prevents CORS regressions and validates cross-origin request handling across all Netra Apex services.

## Overview

The test suite is organized into three levels based on the CORS specification requirements:

1. **Unit Tests** (`tests/test_cors_configuration.py`) - 30 tests
2. **Integration Tests** (`tests/integration/test_cors_integration.py`) - 14 tests  
3. **End-to-End Tests** (`tests/e2e/test_cors_e2e.py`) - 17 tests

**Total: 61 comprehensive CORS tests**

## Quick Start

```bash
# Run all CORS tests
python -m pytest tests/test_cors_configuration.py tests/integration/test_cors_integration.py tests/e2e/test_cors_e2e.py -v

# Run specific test levels
python -m pytest tests/test_cors_configuration.py -v                    # Unit tests
python -m pytest tests/integration/test_cors_integration.py -v          # Integration tests
python -m pytest tests/e2e/test_cors_e2e.py -v                        # E2E tests
```

## Test Commands from SPEC

As specified in `SPEC/cors_configuration.xml`:

```bash
python -m pytest tests/test_cors_configuration.py -v
python -m pytest tests/integration/test_cors_integration.py -v
python -m pytest tests/e2e/test_cors_e2e.py -v
```

## Test Categories

### Unit Tests (tests/test_cors_configuration.py)

Tests CORS middleware configuration and origin validation logic without external dependencies.

**Key Test Classes:**
- `TestCORSOriginParsing` - Environment variable parsing
- `TestCORSEnvironmentConfigurations` - Environment-specific CORS settings
- `TestCORSOriginValidation` - Origin pattern matching and validation
- `TestDynamicCORSMiddleware` - Auth service dynamic CORS middleware
- `TestCustomCORSMiddleware` - Main backend custom CORS middleware
- `TestCORSHeaderValidation` - Required CORS headers validation
- `TestCORSRegressionPrevention` - Specific regression scenarios

**Environment Variables Tested:**
- `CORS_ORIGINS=*` (development wildcard)
- `CORS_ORIGINS=origin1,origin2` (comma-separated list)
- `ENVIRONMENT=development|staging|production`

### Integration Tests (tests/integration/test_cors_integration.py)

Tests cross-origin requests between services with real HTTP clients.

**Key Test Classes:**
- `TestCORSCrossOriginRequests` - Frontend ↔ Backend/Auth service communication
- `TestCORSWebSocketIntegration` - WebSocket CORS validation
- `TestCORSPreflightRequests` - OPTIONS preflight request handling
- `TestCORSEnvironmentSpecificBehavior` - Environment-specific CORS behavior
- `TestCORSRegressionScenarios` - Integration-level regression tests

**Critical Regression Test:**
- **Frontend (3001) → Auth Service (8081) `/auth/config`** - The original regression case

### End-to-End Tests (tests/e2e/test_cors_e2e.py)

Tests complete authentication flows and user journeys across services.

**Key Test Classes:**
- `TestCORSCompleteAuthFlow` - Complete OAuth/auth flows with CORS
- `TestCORSPREnvironmentValidation` - PR environment dynamic origin validation
- `TestCORSProductionStrictValidation` - Production environment strict validation
- `TestCORSDynamicPortValidation` - Dynamic localhost port handling
- `TestCORSCredentialRequestsAcrossServices` - Cookie/token-based requests
- `TestCORSRegressionComprehensive` - Comprehensive regression scenarios
- `TestCORSPerformanceAndResilience` - Performance and resilience testing

## Regression Prevention Coverage

### Primary Regression (SPEC Requirement)
**"Access to fetch at 'http://localhost:8081/auth/config' from origin 'http://localhost:3001' has been blocked by CORS policy"**

✅ **Covered by:**
- `test_auth_config_endpoint_cors_regression` (Unit)
- `test_frontend_to_auth_service_cors` (Integration) 
- `test_auth_config_flow_e2e` (E2E)

### Additional Regressions Prevented

1. **Port Mismatch Issues**
   - Frontend (3000/3001) ↔ Backend (8000)
   - Frontend (3000/3001) ↔ Auth Service (8081)
   - Dynamic development ports

2. **Environment-Specific Issues**
   - Development wildcard (`*`) handling
   - Staging PR environment dynamic origins
   - Production strict origin enforcement

3. **Credentials with Wildcard**
   - Cannot use `credentials: true` with `origin: "*"`
   - DynamicCORSMiddleware solution validation

4. **Middleware Configuration**
   - CORS middleware ordering (must be first)
   - Preflight OPTIONS handling
   - Required headers inclusion

## Environment Configuration Testing

### Development Environment
```bash
export ENVIRONMENT=development
export CORS_ORIGINS="*"
```
- ✅ Wildcard origins allowed
- ✅ All localhost ports allowed
- ✅ DynamicCORSMiddleware used

### Staging Environment  
```bash
export ENVIRONMENT=staging
export CORS_ORIGINS="https://app.staging.netrasystems.ai,https://auth.staging.netrasystems.ai"
```
- ✅ Staging domain patterns allowed
- ✅ PR environment dynamic validation
- ✅ Cloud Run URL patterns allowed
- ✅ Localhost allowed for development

### Production Environment
```bash
export ENVIRONMENT=production
export CORS_ORIGINS="https://netrasystems.ai,https://app.netrasystems.ai"
```
- ✅ Strict origin enforcement
- ✅ No wildcard allowed
- ✅ No localhost allowed
- ✅ Only production domains allowed

## Test Dependencies

### Required Python Packages
- `pytest` - Test framework
- `httpx` - Async HTTP client for integration tests
- `websockets` - WebSocket client for WebSocket CORS tests
- `pytest-asyncio` - Async test support

### Service Dependencies (Integration/E2E Tests)
- **Backend Service**: `http://localhost:8000`
- **Auth Service**: `http://localhost:8081`
- **WebSocket**: `ws://localhost:8000/ws`

### Environment Variables
- `BACKEND_URL` - Backend service URL (default: http://localhost:8000)
- `AUTH_URL` - Auth service URL (default: http://localhost:8081)
- `FRONTEND_URL` - Frontend URL (default: http://localhost:3001)
- `WS_URL` - WebSocket URL (default: ws://localhost:8000/ws)

## Test Execution Strategies

### Local Development
```bash
# Start services first
python dev_launcher/launcher.py

# Run CORS tests
python -m pytest tests/test_cors_configuration.py -v
```

### CI/CD Pipeline
```bash
# Unit tests (no service dependencies)
python -m pytest tests/test_cors_configuration.py -v

# Integration tests (requires running services)
python -m pytest tests/integration/test_cors_integration.py -v --tb=short

# E2E tests (full service stack)
python -m pytest tests/e2e/test_cors_e2e.py -v --tb=short
```

### Service-Specific Testing
```bash
# Test only backend CORS
python -m pytest tests/test_cors_configuration.py::TestCustomCORSMiddleware -v

# Test only auth service CORS  
python -m pytest tests/test_cors_configuration.py::TestDynamicCORSMiddleware -v

# Test specific regression
python -m pytest -k "auth_config_endpoint_cors_regression" -v
```

## Skipped Tests Handling

Integration and E2E tests gracefully skip when services are unavailable:

- **Connection Errors**: Service not running
- **Timeout Errors**: Service slow/unresponsive
- **Port Conflicts**: Service on different port

Example skip message:
```
SKIPPED - Auth service not available for integration test
```

## CORS Headers Validated

### Required Response Headers
- `Access-Control-Allow-Origin`
- `Access-Control-Allow-Credentials`
- `Access-Control-Allow-Methods`
- `Access-Control-Allow-Headers`
- `Access-Control-Expose-Headers`
- `Access-Control-Max-Age` (preflight only)

### Required Methods Support
- `GET`, `POST`, `PUT`, `DELETE`, `OPTIONS`, `PATCH`, `HEAD`

### Required Headers Support
- `Authorization`, `Content-Type`, `X-Request-ID`, `X-Trace-ID`
- `Accept`, `Origin`, `Referer`, `X-Requested-With`

## Continuous Monitoring

### Test Automation
Add to CI/CD pipeline:
```yaml
- name: Run CORS Tests
  run: |
    python -m pytest tests/test_cors_configuration.py -v
    python -m pytest tests/integration/test_cors_integration.py -v  
    python -m pytest tests/e2e/test_cors_e2e.py -v
```

### Pre-deployment Validation
```bash
# Before any deployment
python -m pytest tests/test_cors_configuration.py -v --tb=short
```

### Development Workflow
```bash
# After CORS configuration changes
python -m pytest -k "cors" -v
```

## Common Issues Debugged

1. **Missing CORS Headers**: Middleware not configured
2. **Preflight Failures**: OPTIONS method not handled
3. **Wildcard + Credentials**: Cannot use together
4. **Port Mismatches**: Origin not in allowed list
5. **Environment Misconfig**: Wrong CORS_ORIGINS setting

## Related Files

- `SPEC/cors_configuration.xml` - CORS specification
- `app/core/middleware_setup.py` - Main backend CORS implementation
- `auth_service/main.py` - Auth service CORS implementation
- `dev_launcher/launcher.py` - Development environment setup

This test suite ensures robust CORS handling and prevents regressions across all Netra Apex services and environments.