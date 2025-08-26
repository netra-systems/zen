# Staging Secrets Management Audit Report

**Date:** 2025-08-26  
**Priority:** CRITICAL  
**Impact:** Staging environment unable to properly load secrets from Google Secrets Manager  

## Executive Summary

The staging environment has critical issues with secrets management that prevent Google Secrets Manager from working correctly. The primary issues are:

1. **`.env.staging` is tracked in git** with placeholder values that override Google Secrets
2. **Secret name mismatches** between what's created in Google and what's expected by the code
3. **Inconsistent secret mappings** across different services
4. **Configuration loading precedence issues** where environment files override Google Secrets

## Critical Findings

### 1. `.env.staging` File Tracked in Git
**Severity:** CRITICAL  
**Evidence:**
```bash
$ git ls-files --cached | grep -E "\.env"
.env.staging  # THIS SHOULD NOT BE TRACKED
```

**Current `.env.staging` Content:**
- Contains placeholder values like `POSTGRES_PASSWORD=will-be-set-by-secrets`
- Has empty values like `CLICKHOUSE_PASSWORD=`
- These values are loaded and prevent Google Secrets from working

**Root Cause:** While `.env` files are in `.gitignore`, `.env.staging` is explicitly tracked in git

### 2. Secret Name Mismatches
**Severity:** CRITICAL  
**Evidence:**

**Backend expects (netra_backend/app/core/secret_manager_helpers.py):**
```python
"clickhouse-default-password-staging": "CLICKHOUSE_PASSWORD"
```

**Deployment script creates (scripts/deploy_to_gcp.py):**
```python
secrets_config = {
    "clickhouse-password-staging": "staging_clickhouse_password"  # MISMATCH!
}
```

**Dev launcher expects (dev_launcher/google_secret_manager.py):**
```python
"clickhouse-password": "CLICKHOUSE_PASSWORD"  # DIFFERENT AGAIN!
```

### 3. Configuration Loading Order Issues  
**Severity:** HIGH  
**Evidence:**

In `netra_backend/app/core/secret_manager.py`:
```python
def _load_base_environment_secrets(self, environment: str) -> Dict[str, Any]:
    # Loads from environment variables FIRST
    return self._load_from_environment()

def _merge_google_secrets_if_needed(...):
    # Google secrets loaded AFTER and only update if key exists
    secrets.update(google_secrets)  # Won't override empty strings!
```

**Issue:** Empty strings from `.env.staging` (like `CLICKHOUSE_PASSWORD=`) are considered valid values and won't be overridden.

### 4. Deployment Script Creates Invalid Secrets
**Severity:** HIGH  
**Evidence:**

In `scripts/deploy_to_gcp.py:940-953`:
```python
# Creates secrets with placeholder values
secrets_config = {
    "postgres-password-staging": "staging_postgres_password",
    "clickhouse-password-staging": "staging_clickhouse_password",
    "redis-password-staging": "staging_redis_password",
    # These are just string literals, not actual passwords!
}
```

### 5. Auth Service Secret Loader Issues
**Severity:** MEDIUM  
**Evidence:**

`auth_service/auth_core/secret_loader.py` has its own implementation that differs from the backend, creating inconsistency in how secrets are loaded.

## Detailed Analysis

### Why .env.staging Keeps "Coming Back"

1. **It's tracked in git** - Every time someone pulls the repo, they get the file with invalid values
2. **Git operations restore it** - Checkout, merge, or reset operations restore the tracked version
3. **Deployment might copy it** - Some deployment processes may include the file in Docker images

### Secret Loading Flow Issues

1. **Environment Loading:**
   - `.env.staging` is loaded first with invalid/empty values
   - These become the "base" configuration

2. **Google Secrets Loading:**
   - Attempts to load from Google Secrets Manager
   - Due to name mismatches, many secrets aren't found
   - Even if found, empty strings from env files aren't overridden

3. **Result:**
   - Services start with invalid credentials
   - ClickHouse and Redis connections fail
   - Authentication issues occur

## Recommended Fixes

### Priority 1: Remove .env.staging from Git Tracking (IMMEDIATE)

```bash
# Remove from git tracking but keep local file
git rm --cached .env.staging

# Add to .gitignore
echo ".env.staging" >> .gitignore

# Create template file instead
cp .env.staging .env.staging.template
# Edit template to have comments instead of values
```

### Priority 2: Standardize Secret Names (HIGH)

Create a single source of truth for secret mappings:

```python
# shared/secret_mappings.py
STAGING_SECRET_MAPPINGS = {
    # Google Secret Name -> Environment Variable
    "postgres-host-staging": "POSTGRES_HOST",
    "postgres-password-staging": "POSTGRES_PASSWORD",
    "clickhouse-password-staging": "CLICKHOUSE_PASSWORD",  
    "redis-password-staging": "REDIS_PASSWORD",
    # ... rest of mappings
}
```

### Priority 3: Fix Configuration Loading Precedence (HIGH)

Update secret manager to properly override empty/placeholder values:

```python
def _merge_google_secrets_with_override(self, base_secrets, google_secrets):
    """Merge secrets with Google taking precedence over placeholders."""
    PLACEHOLDER_VALUES = ["", "will-be-set-by-secrets", "placeholder", None]
    
    for key, value in google_secrets.items():
        # Always use Google secret if base value is a placeholder
        if key not in base_secrets or base_secrets[key] in PLACEHOLDER_VALUES:
            base_secrets[key] = value
            self._logger.info(f"Overriding {key} with Google Secret")
    
    return base_secrets
```

### Priority 4: Create Proper Staging Secrets (MEDIUM)

Update deployment script to actually create/update secrets in Google:

```python
def ensure_staging_secrets_exist(self):
    """Ensure all required secrets exist in Google Secret Manager."""
    required_secrets = {
        "clickhouse-password-staging": os.environ.get("STAGING_CLICKHOUSE_PASSWORD"),
        "redis-password-staging": os.environ.get("STAGING_REDIS_PASSWORD"),
        # ... etc
    }
    
    for secret_name, secret_value in required_secrets.items():
        if not secret_value:
            self.logger.warning(f"Secret {secret_name} not provided, skipping")
            continue
            
        self.create_or_update_secret(secret_name, secret_value)
```

## Implementation Plan

### Phase 1: Immediate Actions (1 hour)
1. Remove `.env.staging` from git tracking
2. Create `.env.staging.template` with documentation
3. Update `.gitignore` to explicitly exclude `.env.staging`

### Phase 2: Fix Secret Names (2 hours)
1. Audit all secret names in Google Secrets Manager
2. Create standardized mapping file
3. Update all services to use the same mappings

### Phase 3: Fix Loading Logic (3 hours)  
1. Update secret_manager.py to properly override placeholders
2. Add logging to track which secrets are loaded from where
3. Test with staging environment

### Phase 4: Deployment Updates (2 hours)
1. Update deployment script to validate secrets exist
2. Add secret verification step to deployment
3. Document proper secret creation process

### Phase 5: Testing & Validation (2 hours)
1. Test complete deployment flow
2. Verify all services can connect to databases
3. Document the fixed process

## Verification Steps

After fixes are implemented:

1. **Check Git Status:**
   ```bash
   git ls-files --cached | grep -E "\.env"  # Should not show .env.staging
   ```

2. **Verify Secret Loading:**
   ```python
   # Add debug logging to see which secrets are loaded from where
   python scripts/test_staging_secrets.py
   ```

3. **Test Connections:**
   ```bash
   # Test database connections
   python scripts/validate_staging_deployment.py
   ```

## Risk Assessment

**Without these fixes:**
- Staging will continue to fail with authentication errors
- Developers will waste time debugging connection issues  
- Security risk of hardcoded/invalid credentials

**With these fixes:**
- Proper secret management from Google Secrets Manager
- Consistent behavior across environments
- Secure credential handling

## Next Steps

1. **Immediate:** Remove `.env.staging` from git tracking
2. **Today:** Implement secret name standardization
3. **This Week:** Complete all phases of the implementation plan
4. **Ongoing:** Monitor and maintain proper secret hygiene

## Appendix: Files Requiring Changes

1. **Remove from Git:**
   - `.env.staging`

2. **Update Secret Mappings:**
   - `netra_backend/app/core/secret_manager.py`
   - `netra_backend/app/core/secret_manager_helpers.py`
   - `dev_launcher/google_secret_manager.py`
   - `auth_service/auth_core/secret_loader.py`

3. **Update Deployment:**
   - `scripts/deploy_to_gcp.py`
   - `scripts/create_staging_secrets.py`

4. **Update Documentation:**
   - Create `docs/staging_secrets_setup.md`
   - Update `SPEC/deployment_architecture.xml`

---
**Report Generated:** 2025-08-26  
**Auditor:** Principal Engineer / QA Security Agent  
**Status:** Requires immediate attention and remediation