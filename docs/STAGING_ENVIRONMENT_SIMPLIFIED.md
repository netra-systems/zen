# Staging Environment Configuration - Simplified

## Overview

The staging environment configuration has been simplified to eliminate precedence issues and ensure all secrets are loaded exclusively from Google Secret Manager (GSM).

## Key Changes

### 1. Removed .env.staging File
- **Problem**: .env.staging contained hardcoded secrets that would override GSM values
- **Solution**: Deleted .env.staging completely - staging never uses local env files

### 2. Application Startup Changes
- Both `netra_backend` and `auth_service` now check `ENVIRONMENT` variable first
- When `ENVIRONMENT=staging`, all .env file loading is skipped
- All configuration comes from Cloud Run environment variables and GSM

### 3. Deployment Script Consolidation
- All non-secret configuration is set as Cloud Run environment variables in `deploy_to_gcp.py`
- All secrets are loaded from Google Secret Manager using `--set-secrets`
- Single source of truth for deployment configuration

## Environment Hierarchy

| Environment | Configuration Source | .env Files |
|------------|---------------------|------------|
| Development | .env files + local config | ✅ Allowed |
| Staging | Cloud Run env vars + GSM | ❌ Forbidden |
| Production | Cloud Run env vars + GSM | ❌ Forbidden |

## Configuration Flow

### Development
```
.env file → IsolatedEnvironment → Application
```

### Staging/Production
```
Cloud Run env vars + GSM → Application (no .env loading)
```

## Testing

Run the audit test suite to ensure compliance:
```bash
pytest tests/audit/test_no_environment_files.py -v
```

This test suite verifies:
- No .env.staging file exists
- Applications skip .env loading in staging
- No hardcoded secrets in application code
- Deployment script properly configured
- No references to .env.staging in code

## Deployment

Deploy to staging with simplified configuration:
```bash
python scripts/deploy_to_gcp.py --project netra-staging --build-local
```

## Important Notes

1. **Never create .env.staging or .env.production files** - They cause precedence issues
2. **All staging/production secrets must be in Google Secret Manager**
3. **Non-secret configuration goes in deployment script as env vars**
4. **Applications must check ENVIRONMENT before loading .env files**

## Troubleshooting

If staging deployment fails:
1. Check that ENVIRONMENT=staging is set in Cloud Run
2. Verify secrets exist in Google Secret Manager
3. Ensure no .env.staging file exists
4. Check deployment logs for GSM access errors

## Related Documentation

- [SPEC/learnings/staging_environment_simplification.xml](../SPEC/learnings/staging_environment_simplification.xml)
- [SPEC/unified_environment_management.xml](../SPEC/unified_environment_management.xml)
- [scripts/test_staging_simplified.py](../scripts/test_staging_simplified.py)
- [tests/audit/test_no_environment_files.py](../tests/audit/test_no_environment_files.py)