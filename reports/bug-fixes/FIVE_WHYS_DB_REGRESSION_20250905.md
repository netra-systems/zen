# Five Whys Analysis: Database Regression in Staging
## Date: 2025-09-05

## Problem Statement
The backend health check endpoint `/health/ready` returns 503 errors with "Core database unavailable" in GCP staging deployment.

## Five Whys Analysis

### Level 1: Why is the health check returning 503?
**Answer:** The database session creation in `health.py` is failing with error: "'NoneType' object has no attribute 'lower'"

### Level 2: Why is the database session creation failing?
**Answer:** The `get_db()` function from `netra_backend.app.database` is not properly initializing the database connection. The error suggests a None value is being accessed where a string (likely database URL or host) is expected.

### Level 3: Why is get_db() not properly initializing?
**Answer:** The database configuration is not being properly loaded in the GCP environment. The `get_database_url()` function in `database/__init__.py` relies on `get_backend_env().get_database_url()` which may be returning None or malformed data.

### Level 4: Why is the database configuration not loading properly?
**Answer:** The environment variables in GCP are set, but the backend is not reading them correctly. Looking at the deployment configuration:
- Individual POSTGRES_* variables are NOT set in the Cloud Run service
- The code expects either DATABASE_URL or individual POSTGRES_* variables
- The secrets are in Secret Manager but not mounted as environment variables

### Level 5: Why are the database environment variables not mounted?
**Answer:** The deployment script (`deploy_to_gcp.py`) validates that secrets exist in Secret Manager but doesn't mount them as environment variables in the Cloud Run service configuration. The script only sets non-secret environment variables directly.

## Root Causes Identified

1. **Missing Secret Mounting**: The deployment script validates secrets exist but doesn't mount them as environment variables
2. **Configuration Regression**: The switch to DatabaseURLBuilder pattern wasn't fully propagated to the GCP deployment
3. **Incomplete Testing**: The deployment was tested for build success but not for runtime database connectivity

## Evidence
- Logs show: `PostgreSQL readiness check failed: 'NoneType' object has no attribute 'lower'`
- Cloud Run service config shows CLICKHOUSE_* vars but NO POSTGRES_* vars
- Secrets exist in Secret Manager but aren't referenced in the service spec

## Immediate Fix Required

### Option 1: Update Cloud Run Service to Mount Secrets
```bash
gcloud run services update netra-backend-staging \
  --update-env-vars POSTGRES_HOST=10.x.x.x \
  --update-env-vars POSTGRES_PORT=5432 \
  --update-env-vars POSTGRES_DB=staging \
  --update-env-vars POSTGRES_USER=postgres \
  --update-secrets POSTGRES_PASSWORD=postgres-password-staging:latest \
  --region us-central1 \
  --project netra-staging
```

### Option 2: Fix Deployment Script
Update `scripts/deploy_to_gcp.py` to properly mount database secrets as environment variables in the Cloud Run deployment command.

## Prevention Measures

1. **Add E2E Health Check**: After deployment, always test `/health/ready` endpoint
2. **Fix Deployment Script**: Ensure all required secrets are mounted as environment variables
3. **Add Deployment Validation**: Create post-deployment validation that checks database connectivity
4. **Document Secret Requirements**: Clear documentation of which secrets must be mounted
5. **Add Integration Tests**: Test the full deployment configuration locally with docker-compose

## Historical Context
- This regression was previously fixed in commit `8a540c039` which updated health.py to use canonical database patterns
- However, the root cause (missing environment variables in deployment) was not addressed
- The issue manifests differently each time because various workarounds are applied without fixing the core deployment configuration issue

## Action Items
1. [ ] Mount database secrets in Cloud Run service
2. [ ] Update deployment script to automatically mount all required secrets
3. [ ] Add post-deployment health check validation
4. [ ] Document the complete secret mounting requirements
5. [ ] Add integration test for GCP deployment configuration