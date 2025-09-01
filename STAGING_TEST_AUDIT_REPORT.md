# Staging Test Configuration Audit Report

## Executive Summary
Audit of staging test configuration reveals that tests are **NOT defaulting to GCP staging** but rather conditionally switching based on `ENVIRONMENT` variable. The hardcoded staging URLs are inconsistent and not properly defaulting to staging.

## Critical Findings

### 1. Environment Variable Dependency (HIGH PRIORITY)
**Issue**: All staging tests rely on `ENVIRONMENT` variable defaulting to `"development"`, not `"staging"`

**Current Pattern**:
```python
self.env = IsolatedEnvironment()
self.environment = self.env.get("ENVIRONMENT", "development")  # <-- DEFAULTS TO DEVELOPMENT
self.urls = STAGING_URLS if self.environment == "staging" else LOCAL_URLS
```

**Files Affected**: All 10 staging test files in `/tests/staging/`

**Impact**: Tests run against localhost by default unless `ENVIRONMENT=staging` is explicitly set.

### 2. Inconsistent Staging URLs
**Issue**: Hardcoded staging URLs use project number `701982941522` but deployment scripts reference `netra-staging` project.

**Current URLs in Tests**:
```python
STAGING_URLS = {
    "backend": "https://netra-backend-staging-701982941522.us-central1.run.app",
    "auth": "https://netra-auth-service-701982941522.us-central1.run.app",
    "frontend": "https://netra-frontend-staging-701982941522.us-central1.run.app"
}
```

**Deployment Configuration** (`deploy_to_gcp.py`):
- Backend: `cloud_run_name="netra-backend-staging"`
- Frontend: `cloud_run_name="netra-frontend-staging"`
- Auth: Not found in service configs (missing from deployment script)

### 3. Missing Auth Service in Deployment
**Issue**: Auth service deployment configuration is missing from the main deployment script's service configurations.

**Evidence**: Only backend and frontend ServiceConfig objects found in `deploy_to_gcp.py`

### 4. Project ID Confusion
**Issue**: Multiple project identifiers in use:
- Project name: `netra-staging`
- Project number: `701982941522`
- Service URLs mix both formats

## Recommendations

### Immediate Actions Required

#### 1. Change Default Environment to Staging
Update all staging test files to default to staging:

```python
# FROM:
self.environment = self.env.get("ENVIRONMENT", "development")

# TO:
self.environment = self.env.get("ENVIRONMENT", "staging")
```

#### 2. Create Centralized Staging Configuration
Create `/tests/staging/staging_config.py`:

```python
"""Centralized staging configuration - Single Source of Truth"""

# GCP Project Configuration
GCP_PROJECT_NAME = "netra-staging"
GCP_PROJECT_NUMBER = "701982941522"
GCP_REGION = "us-central1"

# Service URLs - Use actual deployed URLs from GCP
STAGING_URLS = {
    "backend": f"https://netra-backend-staging-{GCP_PROJECT_NUMBER}.{GCP_REGION}.run.app",
    "auth": f"https://netra-auth-service-{GCP_PROJECT_NUMBER}.{GCP_REGION}.run.app",
    "frontend": f"https://netra-frontend-staging-{GCP_PROJECT_NUMBER}.{GCP_REGION}.run.app"
}

# Local URLs for development
LOCAL_URLS = {
    "backend": "http://localhost:8000",
    "auth": "http://localhost:8081",
    "frontend": "http://localhost:3000"
}

def get_urls(environment: str = "staging"):
    """Get URLs based on environment, defaulting to staging."""
    return STAGING_URLS if environment == "staging" else LOCAL_URLS
```

#### 3. Update All Test Files
Modify all staging test files to use centralized config:

```python
from tests.staging.staging_config import get_urls

class StagingTestRunner:
    def __init__(self):
        self.env = IsolatedEnvironment()
        # Force staging unless explicitly overridden
        self.environment = self.env.get("ENVIRONMENT", "staging")
        self.urls = get_urls(self.environment)
```

#### 4. Add Auth Service to Deployment
Update `deploy_to_gcp.py` to include auth service configuration:

```python
ServiceConfig(
    name="auth",
    directory="auth_service",
    port=8081,
    dockerfile="deployment/docker/auth.gcp.Dockerfile",
    cloud_run_name="netra-auth-service",
    memory="512Mi",
    cpu="1",
    min_instances=1,
    max_instances=10,
    environment_vars={
        "ENVIRONMENT": "staging",
        "PYTHONUNBUFFERED": "1",
        # ... other auth service env vars
    }
)
```

### Long-term Improvements

1. **Environment Variable Validation**
   - Add startup validation to ensure ENVIRONMENT is explicitly set for staging tests
   - Fail fast with clear error message if configuration is missing

2. **URL Discovery**
   - Consider implementing dynamic URL discovery from GCP rather than hardcoding
   - Use GCP APIs to fetch actual deployed service URLs

3. **Configuration Documentation**
   - Document the relationship between project name and project number
   - Create clear deployment-to-test mapping documentation

4. **Test Runner Enhancement**
   - Add `--force-staging` flag to test runner to override environment detection
   - Implement URL validation before test execution

## Testing the Fix

After implementing recommendations:

1. **Verify Default Behavior**:
   ```bash
   # Should use staging URLs by default
   python tests/staging/run_staging_tests.py --test configuration
   ```

2. **Verify Explicit Staging**:
   ```bash
   # Should definitely use staging URLs
   ENVIRONMENT=staging python tests/staging/run_staging_tests.py
   ```

3. **Verify Local Override**:
   ```bash
   # Should use local URLs when explicitly set
   ENVIRONMENT=development python tests/staging/run_staging_tests.py
   ```

## Files Requiring Updates

1. `/tests/staging/test_staging_jwt_cross_service_auth.py`
2. `/tests/staging/test_staging_websocket_agent_events.py`
3. `/tests/staging/test_staging_e2e_user_auth_flow.py`
4. `/tests/staging/test_staging_api_endpoints.py`
5. `/tests/staging/test_staging_service_health.py`
6. `/tests/staging/test_staging_database_connectivity.py`
7. `/tests/staging/test_staging_token_validation.py`
8. `/tests/staging/test_staging_configuration.py`
9. `/tests/staging/test_staging_agent_execution.py`
10. `/tests/staging/test_staging_frontend_backend_integration.py`
11. `/tests/staging/run_staging_tests.py`
12. `/scripts/deploy_to_gcp.py` (add auth service)

## Conclusion

The staging test suite is currently configured to default to local development rather than GCP staging. This defeats the purpose of staging tests and could lead to false positives. Implementing the recommended changes will ensure tests default to the actual staging environment while still allowing local testing when explicitly requested.

**Priority**: HIGH - This affects the reliability of all staging environment validation.

**Estimated Effort**: 2-3 hours to implement all recommendations.

---
Generated: 2025-01-09
Auditor: Claude Code