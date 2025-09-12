# Environment-Specific Auth Separation Tests

## Overview

This module contains E2E tests for validating environment-specific authentication flow separation, addressing WebSocket auth golden path issues identified through Five Whys analysis.

## Problem Statement

From the Five Whys analysis: **Environment-specific behavior creates different auth flows that aren't cleanly separated, causing golden path issues in staging vs development.**

## Solution

Created comprehensive E2E tests that validate clean separation between environment-specific authentication flows to prevent cross-environment contamination and golden path failures.

## Test Implementation

### File: `test_environment_auth_separation.py`

#### Test Methods:

1. **`test_staging_auth_flow_differs_from_development()`**
   - Validates environment marker differences (staging vs development)
   - Checks auth service health endpoints contain proper environment markers
   - Ensures OAuth configuration uses staging domains (not localhost)
   - Verifies service versions don't contain development markers

2. **`test_environment_specific_auth_configuration()`**
   - Validates JWT secrets are environment-specific (not default/dev values)  
   - Ensures OAuth client IDs don't contain localhost (development leakage)
   - Checks Redis/Database URLs are staging-specific
   - Validates auth service URLs match environment expectations

3. **`test_cross_environment_auth_token_rejection()`**
   - Tests that staging rejects development tokens (security boundary)
   - Validates auth service rejects tokens with wrong environment markers
   - Ensures tokens with wrong secrets are properly rejected
   - Prevents unauthorized cross-environment access

4. **`test_demo_mode_vs_production_auth_separation()`**
   - Validates demo auth endpoints differ from production endpoints
   - Ensures demo tokens contain proper demo markers and environment info
   - Checks demo endpoints are disabled when demo mode is off
   - Validates production endpoints apply restrictions for demo tokens

### Technical Features:

- **Framework**: Inherits from `SSotAsyncTestCase` (CLAUDE.md compliant)
- **Environment Detection**: Automatically detects and configures for current environment
- **Real Services**: Uses real staging services (no mocks for E2E validation)
- **Security Focus**: Validates critical security boundaries between environments
- **Business Impact**: Protects $500K+ ARR Golden Path from auth cross-contamination

### Environment Configuration:

```python
# Development
auth_base_url = "http://localhost:8081"
backend_url = "http://localhost:8000"

# Staging  
auth_base_url = "https://auth.staging.netrasystems.ai"
backend_url = "https://backend.staging.netrasystems.ai"
```

## Usage

### Running Tests

```bash
# Run all environment separation tests
pytest tests/e2e/staging/test_environment_auth_separation.py -v

# Run specific test
pytest tests/e2e/staging/test_environment_auth_separation.py::TestEnvironmentAuthSeparation::test_staging_auth_flow_differs_from_development -v

# Run in staging environment (skips development-only tests)
ENVIRONMENT=staging pytest tests/e2e/staging/test_environment_auth_separation.py -v
```

### Validation Script

```bash
# Validate test implementation and environment detection
python tests/e2e/staging/validate_environment_auth_separation.py
```

## Business Impact

### Protects Golden Path ($500K+ ARR)
- Prevents development auth configurations from leaking into staging
- Ensures staging auth is properly isolated from production patterns
- Validates clean environment boundaries prevent user auth issues

### Enterprise Security Requirements
- Validates JWT secret environment separation
- Ensures OAuth configurations are environment-specific
- Tests cross-environment token rejection (security boundaries)
- Validates demo mode isolation from production data

### Development Velocity
- Catches environment configuration drift early
- Prevents staging deployment issues from auth misconfiguration
- Validates that environment-specific behavior is properly isolated

## Expected Test Results

### In Development Environment:
- Tests detect localhost URLs and development configuration
- Environment marker is "development"
- Development-specific auth flows are validated

### In Staging Environment:
- Tests detect staging.netrasystems.ai URLs and staging configuration
- Environment marker is "staging" 
- Cross-environment token rejection is validated
- Staging-specific auth flows differ from development

### Security Validation:
- Development tokens are rejected by staging services
- Staging uses different JWT secrets than development
- OAuth configuration doesn't leak localhost endpoints
- Demo mode (if enabled) is properly isolated

## Test Markers

- `@staging_only`: Tests only run in staging environment
- `@env_requires(services=["auth_service", "backend"])`: Requires specific services
- `@pytest.mark.auth`: Auth-related test marker
- `@pytest.mark.e2e`: End-to-end test marker

## Integration with Test Plan

This module implements the **E2E Staging Tests** component of the WebSocket Auth Golden Path test plan, specifically focusing on environment-specific behavior separation identified in the Five Whys root cause analysis.

## Next Steps

1. Run tests in actual staging environment to validate configuration
2. Monitor test results for environment configuration drift
3. Add additional environment-specific validations as needed
4. Integrate with CI/CD pipeline for deployment validation