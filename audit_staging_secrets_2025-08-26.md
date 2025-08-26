# Staging Secrets Management Audit Report
**Date:** 2025-08-26  
**Auditor:** Principal Engineer  
**Status:** CRITICAL ISSUES IDENTIFIED  

## Executive Summary

Multiple critical issues have been identified in the staging environment's secret management system that are preventing proper utilization of Google Secret Manager secrets. The primary issues are:

1. **Invalid Redis URL in Google Secret Manager** - Contains placeholder password
2. **Missing secret mappings** - Some secrets in GSM don't match expected environment variable names
3. **Persistent .env.staging file** - Overrides Google secrets with invalid/placeholder values
4. **Architectural violation** - Direct environment file usage violates unified environment management spec

## Critical Findings

### 1. Invalid Redis URL in Google Secret Manager
**Severity:** CRITICAL  
**Location:** Google Secret Manager - `redis-url-staging`  
**Current Value:** `redis://default:REPLACE_WITH_REDIS_PASSWORD@10.128.0.3:6379/0`  
**Issue:** Contains placeholder text "REPLACE_WITH_REDIS_PASSWORD" instead of actual password  
**Impact:** Redis connection failures in staging environment  

### 2. Secret Name Mismatches
**Severity:** HIGH  
**Issue:** Multiple secret naming inconsistencies found:

| Google Secret Name | Expected Mapping | Status |
|-------------------|------------------|---------|
| clickhouse-default-password-staging | Not mapped | ❌ Missing |
| clickhouse-password-staging | CLICKHOUSE_PASSWORD | ✅ Mapped |
| redis-url | Not mapped | ❌ Orphaned |
| redis-url-staging | Not mapped | ❌ Should use redis-password-staging |
| GOOGLE_OAUTH_CLIENT_CLIENT_ID_STAGING | Not mapped | ❌ Duplicate pattern |
| google-client-id-staging | GOOGLE_CLIENT_ID | ✅ Mapped |

### 3. .env.staging File Persistence
**Severity:** CRITICAL  
**Location:** `/netra-core-generation-1/.env.staging`  
**Issues:**
- File contains placeholder values that override Google secrets:
  - `POSTGRES_PASSWORD=will-be-set-by-secrets`
  - `JWT_SECRET_KEY=staging-jwt-secret-key-should-be-replaced-in-deployment`
  - `FERNET_KEY=staging-fernet-key-should-be-replaced-in-deployment`
- File is gitignored but keeps being recreated
- Template file exists at `.env.staging.template` that may be getting copied

**Root Cause:** No automated process found creating the file, likely manual creation from template

### 4. Secret Loading Priority Issues
**Severity:** HIGH  
**Location:** `netra_backend/app/core/secret_manager.py`
**Current Behavior:**
1. Loads environment variables first (including from .env.staging)
2. Then attempts to override with Google secrets
3. Only overrides if value is in PLACEHOLDER_VALUES list

**Problem:** If .env.staging has non-placeholder invalid values, they won't be overridden

### 5. ClickHouse Configuration Issues
**Severity:** MEDIUM  
**Findings:**
- ClickHouse host in GSM: `clickhouse.staging.netrasystems.ai` 
- Expected in .env.staging: `staging-clickhouse.netrasystems.ai`
- Mismatch in subdomain naming pattern

## Secret Manager Architecture Analysis

### Current Flow:
1. **IsolatedEnvironment** loads from .env files (including .env.staging if present)
2. **SecretManager** class:
   - Detects environment (staging/production)
   - Loads base secrets from environment
   - Fetches Google secrets
   - Merges Google secrets, overriding placeholders
3. **Secret Mappings** in `shared/secret_mappings.py` define GSM name to env var mappings

### Identified Gaps:
- No validation that all required secrets are loaded from GSM
- No warning when .env.staging exists and may conflict
- Inconsistent secret naming in GSM (some with -staging suffix, some without)
- No automated cleanup of invalid .env.staging files

## Compliance Issues

### Violation of SPEC/unified_environment_management.xml:
- Direct .env.staging usage violates centralized environment management
- Should use IsolatedEnvironment exclusively
- .env.staging creates untracked environment state

### Violation of SPEC/no_test_stubs.xml:
- Placeholder values in production paths
- Invalid configuration values reaching staging

## Immediate Actions Required

### Priority 1 - Fix Invalid Secrets in GSM:
```bash
# Fix Redis URL secret
echo "redis://default:ACTUAL_REDIS_PASSWORD@10.128.0.3:6379/0" | \
  gcloud secrets versions add redis-url-staging --project=netra-staging --data-file=-

# Or better - use redis-password-staging separately and construct URL in code
```

### Priority 2 - Remove .env.staging:
```bash
# Delete the file
rm .env.staging

# Add pre-deployment check to prevent recreation
```

### Priority 3 - Fix Secret Mappings:
- Consolidate duplicate secrets in GSM
- Update `shared/secret_mappings.py` to include all GSM secrets
- Remove orphaned/duplicate secrets from GSM

## Recommended Fixes

### 1. Enhanced Secret Validation
Add validation in `SecretManager._merge_google_secrets_with_logging`:
```python
def _validate_critical_secrets(self, secrets: Dict[str, Any]) -> None:
    """Validate critical secrets are properly loaded from GSM."""
    critical_secrets = {
        'POSTGRES_PASSWORD': lambda v: v and v != 'will-be-set-by-secrets',
        'REDIS_PASSWORD': lambda v: v and 'REPLACE' not in v,
        'JWT_SECRET_KEY': lambda v: v and 'should-be-replaced' not in v,
        'CLICKHOUSE_PASSWORD': lambda v: v is not None
    }
    
    for key, validator in critical_secrets.items():
        value = secrets.get(key)
        if not validator(value):
            self._logger.error(f"CRITICAL: Invalid or missing secret: {key}")
            raise SecretManagerError(f"Invalid secret configuration for {key}")
```

### 2. Prevent .env.staging Usage
Add check in `dev_launcher/env_file_loader.py`:
```python
def _check_staging_file(self) -> None:
    """Check for and warn about .env.staging file."""
    staging_file = self.project_root / ".env.staging"
    if staging_file.exists():
        logger.warning("CRITICAL: .env.staging file detected!")
        logger.warning("This file overrides Google Secret Manager!")
        logger.warning("Delete it immediately: rm .env.staging")
        # In staging environment, could even raise an exception
```

### 3. Clean Up GSM Secrets
Script to identify and remove duplicates:
```python
# List all secrets and identify patterns
# Remove duplicates keeping only the mapped ones
# Ensure consistent naming convention
```

## Testing Recommendations

1. Add integration test to verify GSM secrets load correctly
2. Add test to ensure .env.staging doesn't exist in staging
3. Add validation that critical secrets don't contain placeholders
4. Test secret precedence to ensure GSM always wins

## Long-term Improvements

1. **Automated Secret Rotation** - Implement automated rotation for critical secrets
2. **Secret Validation Pipeline** - Pre-deployment validation of all secrets
3. **Monitoring** - Add alerts for secret loading failures
4. **Documentation** - Update deployment docs to clarify no .env.staging should exist

## Conclusion

The staging environment's secret management has multiple critical issues that need immediate attention. The most urgent are:

1. Fix invalid Redis URL in Google Secret Manager
2. Delete .env.staging file and prevent recreation
3. Validate all secrets are loading correctly from GSM

These issues are causing authentication failures, connection errors, and violating architectural specifications. Immediate remediation is required to restore staging environment functionality.

## Appendix: Files Reviewed

- `/netra_backend/app/core/secret_manager.py`
- `/netra_backend/app/core/secret_manager_helpers.py`
- `/shared/secret_mappings.py`
- `/dev_launcher/env_file_loader.py`
- `/dev_launcher/isolated_environment.py`
- `/.env.staging`
- `/.env.staging.template`
- `/SPEC/unified_environment_management.xml`
- Google Secret Manager secrets in project `netra-staging`