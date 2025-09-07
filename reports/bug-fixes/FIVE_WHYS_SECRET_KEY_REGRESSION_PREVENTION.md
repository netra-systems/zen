# Five Whys Analysis: SECRET_KEY Regression Prevention Plan

## The Problem
Auth service failed in staging because SECRET_KEY environment variable was not being mapped from Google Secret Manager, causing the service to crash on startup.

## Five Whys Analysis

### Why #1: Why did the auth service fail?
**Answer:** Because `SECRET_KEY` environment variable was not set in the staging environment.

### Why #2: Why was SECRET_KEY not set?
**Answer:** Because the SECRET_KEY mapping was missing from the auth service's `--set-secrets` parameter in deploy_to_gcp.py line 894, even though the secret existed in GSM.

### Why #3: Why was the SECRET_KEY mapping missing from auth service but not backend?
**Answer:** Because during OAuth configuration updates, someone modified the auth service secrets list multiple times (adding/removing SERVICE_ID, fixing OAuth variables) and accidentally removed SECRET_KEY without realizing it was required.

### Why #4: Why didn't we catch this missing requirement during development or testing?
**Answer:** Because:
1. The secret requirements are hardcoded as long strings in deploy_to_gcp.py (line 894 is 500+ characters)
2. There's no validation that checks if all required secrets for each service are mapped
3. The auth service crashes at runtime, not at deployment time
4. No automated tests verify secret mappings match service requirements

### Why #5: Why are secret mappings maintained as hardcoded strings instead of a validated configuration?
**Answer:** Because:
1. Historical evolution - started simple and grew complex
2. No single source of truth for what secrets each service requires
3. No build-time or deploy-time validation of environment requirements
4. The deployment script grew organically without architectural review

## Root Causes Identified

1. **No Single Source of Truth**: Secret requirements are scattered across:
   - deploy_to_gcp.py (hardcoded strings)
   - auth_environment.py (runtime checks)
   - Service code (actual usage)

2. **No Validation Layer**: Missing secrets only discovered at runtime when service crashes

3. **Poor Maintainability**: 500+ character strings are error-prone to modify

4. **No Contract Enforcement**: Services don't declare their requirements in a testable way

## Permanent Solution Design

### Solution 1: Service Secret Requirements Manifest (RECOMMENDED)
Create a declarative configuration that defines what secrets each service needs.

```python
# deployment/secrets_config.py
SERVICE_SECRETS = {
    "backend": {
        "database": [
            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB", 
            "POSTGRES_USER", "POSTGRES_PASSWORD"
        ],
        "auth": [
            "JWT_SECRET_STAGING", "JWT_SECRET_KEY", "SECRET_KEY",
            "SERVICE_SECRET"
        ],
        "oauth": [
            "GOOGLE_CLIENT_ID", "GOOGLE_CLIENT_SECRET"
        ],
        "redis": ["REDIS_URL", "REDIS_PASSWORD"],
        "ai": [
            "OPENAI_API_KEY", "ANTHROPIC_API_KEY", 
            "GEMINI_API_KEY"
        ],
        "clickhouse": ["CLICKHOUSE_PASSWORD"],
        "encryption": ["FERNET_KEY"]
    },
    "auth": {
        "database": [
            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
            "POSTGRES_USER", "POSTGRES_PASSWORD"
        ],
        "auth": [
            "JWT_SECRET_STAGING", "JWT_SECRET_KEY", "SECRET_KEY",
            "SERVICE_SECRET", "SERVICE_ID"
        ],
        "oauth": [
            "GOOGLE_OAUTH_CLIENT_ID_STAGING", 
            "GOOGLE_OAUTH_CLIENT_SECRET_STAGING",
            "OAUTH_HMAC_SECRET"
        ],
        "redis": ["REDIS_URL", "REDIS_PASSWORD"]
    },
    "frontend": {
        # Frontend doesn't use GSM secrets
    }
}

# Mapping to actual GSM secret names
SECRET_MAPPINGS = {
    "POSTGRES_HOST": "postgres-host-staging",
    "POSTGRES_PORT": "postgres-port-staging",
    "POSTGRES_DB": "postgres-db-staging",
    "POSTGRES_USER": "postgres-user-staging",
    "POSTGRES_PASSWORD": "postgres-password-staging",
    "JWT_SECRET_STAGING": "jwt-secret-staging",
    "JWT_SECRET_KEY": "jwt-secret-key-staging",
    "SECRET_KEY": "secret-key-staging",
    "SERVICE_SECRET": "service-secret-staging",
    "SERVICE_ID": "service-id-staging",
    "GOOGLE_OAUTH_CLIENT_ID_STAGING": "google-oauth-client-id-staging",
    "GOOGLE_OAUTH_CLIENT_SECRET_STAGING": "google-oauth-client-secret-staging",
    "OAUTH_HMAC_SECRET": "oauth-hmac-secret-staging",
    "REDIS_URL": "redis-url-staging",
    "REDIS_PASSWORD": "redis-password-staging",
    "OPENAI_API_KEY": "openai-api-key-staging",
    "ANTHROPIC_API_KEY": "anthropic-api-key-staging",
    "GEMINI_API_KEY": "gemini-api-key-staging",
    "FERNET_KEY": "fernet-key-staging",
    "CLICKHOUSE_PASSWORD": "clickhouse-password-staging",
    "GOOGLE_CLIENT_ID": "google-oauth-client-id-staging",
    "GOOGLE_CLIENT_SECRET": "google-oauth-client-secret-staging"
}
```

### Solution 2: Service Requirements Declaration
Each service declares its requirements in a manifest file:

```yaml
# auth_service/deployment.yaml
service: auth
secrets_required:
  - JWT_SECRET_KEY
  - SECRET_KEY
  - SERVICE_SECRET
  - POSTGRES_HOST
  - POSTGRES_PORT
  - POSTGRES_DB
  - POSTGRES_USER
  - POSTGRES_PASSWORD
  - REDIS_URL
  
secrets_optional:
  - GOOGLE_OAUTH_CLIENT_ID_STAGING
  - GOOGLE_OAUTH_CLIENT_SECRET_STAGING
  
health_check:
  path: /health
  expected_keys:
    - status
    - database_status
```

### Solution 3: Build-Time Validation
Add validation that runs during deployment:

```python
# scripts/validate_secrets.py
def validate_service_secrets(service_name: str, project_id: str):
    """Validate all required secrets exist before deployment."""
    
    required_secrets = SERVICE_SECRETS.get(service_name, {})
    missing_secrets = []
    
    for category, secrets in required_secrets.items():
        for secret in secrets:
            gsm_name = SECRET_MAPPINGS.get(secret)
            if not check_secret_exists(gsm_name, project_id):
                missing_secrets.append(f"{secret} -> {gsm_name}")
    
    if missing_secrets:
        raise ValueError(
            f"Cannot deploy {service_name}: Missing secrets:\n" + 
            "\n".join(missing_secrets)
        )
    
    return generate_secrets_string(service_name)
```

### Solution 4: Runtime Contract Validation
Add startup validation in services:

```python
# auth_service/startup_validator.py
class StartupValidator:
    REQUIRED_SECRETS = [
        "JWT_SECRET_KEY",
        "SECRET_KEY", 
        "SERVICE_SECRET"
    ]
    
    @classmethod
    def validate_environment(cls):
        """Fail fast if required secrets are missing."""
        missing = []
        for secret in cls.REQUIRED_SECRETS:
            if not os.environ.get(secret):
                missing.append(secret)
        
        if missing:
            # This helps identify what's missing at deployment time
            error_msg = f"Missing required secrets: {', '.join(missing)}"
            logger.error(error_msg)
            
            # Write to a status file for external monitoring
            with open("/tmp/startup_failure.txt", "w") as f:
                f.write(error_msg)
            
            raise EnvironmentError(error_msg)
```

### Solution 5: Automated Testing
Add tests that verify secret mappings:

```python
# tests/deployment/test_secret_mappings.py
def test_auth_service_has_all_required_secrets():
    """Verify auth service secret mappings include all requirements."""
    
    # Parse the actual deploy_to_gcp.py file
    with open("scripts/deploy_to_gcp.py") as f:
        content = f.read()
    
    # Extract auth service secrets
    auth_secrets_line = re.search(
        r'service\.name == "auth".*?"--set-secrets",\s*"([^"]+)"',
        content, re.DOTALL
    )
    
    mapped_secrets = auth_secrets_line.group(1).split(",")
    
    # Check all required secrets are present
    for secret in AUTH_REQUIRED_SECRETS:
        gsm_name = f"{SECRET_MAPPINGS[secret]}:latest"
        assert any(
            mapping.startswith(f"{secret}={gsm_name}")
            for mapping in mapped_secrets
        ), f"Missing {secret} in auth service deployment"
```

## Implementation Plan

### Phase 1: Immediate (Today)
1. ✅ Fix the immediate issue (DONE)
2. Create secrets_config.py with current mappings
3. Add validation function to deploy_to_gcp.py

### Phase 2: Short-term (This Week)  
1. Refactor deploy_to_gcp.py to use secrets_config.py
2. Add build-time validation
3. Add automated tests for secret mappings

### Phase 3: Medium-term (Next Sprint)
1. Add service manifest files (deployment.yaml)
2. Implement startup validators in each service
3. Create monitoring dashboard for secret health

### Phase 4: Long-term (Next Month)
1. Move to Kubernetes ConfigMaps/Secrets
2. Use Helm charts for deployment configuration
3. Implement secret rotation automation

## Validation Checklist

Before any deployment:
- [ ] Run `python scripts/validate_secrets.py --service auth`
- [ ] Run `pytest tests/deployment/test_secret_mappings.py`
- [ ] Check service startup logs for secret validation
- [ ] Verify health endpoint includes all expected fields

## Monitoring & Alerting

1. **Pre-deployment Checks**
   ```bash
   gcloud secrets list --filter="name:staging" --format=json | \
     python scripts/check_secret_versions.py
   ```

2. **Post-deployment Validation**
   ```bash
   curl https://{service-url}/health | \
     python scripts/validate_health_response.py --service auth
   ```

3. **Continuous Monitoring**
   - Alert if any service fails with "SECRET_KEY" or similar in logs
   - Weekly audit of secret mappings vs requirements
   - Automated PR checks for deploy_to_gcp.py changes

## Prevention Metrics

Track these metrics to ensure the solution works:
1. Number of secret-related deployment failures (target: 0)
2. Time to detect missing secrets (target: < 1 minute at build time)
3. Secret configuration drift (target: 0 differences between services and manifests)

## Conclusion

The root cause is **lack of a single source of truth** for secret requirements and **no validation layer** between configuration and runtime. The solution is to:

1. **Centralize** secret configuration in a maintainable format
2. **Validate** at build time, deploy time, and runtime
3. **Test** secret mappings automatically
4. **Monitor** for configuration drift

This will prevent not just SECRET_KEY regressions, but ANY secret-related deployment failures.