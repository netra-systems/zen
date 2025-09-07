# Staging Database Connection Fix Summary

## Issue Identified
The staging environment is failing with "password authentication failed for user 'postgres'" because the DATABASE_URL secret in Google Cloud has an incorrect format or outdated credentials.

## Root Cause
This is a **known issue** documented in `SPEC/learnings/auth_service_staging_errors_five_whys.xml`. The root causes are:
1. DATABASE_URL secret uses incorrect format for Cloud SQL Unix socket connections
2. Missing DATABASE_URL mapping in the Google Secret Manager configuration
3. No pre-deployment validation of database credentials

## Solution Implemented

### 1. Fixed Google Secret Manager Mapping
Updated `dev_launcher/google_secret_manager.py` to include:
```python
"database-url-staging": "DATABASE_URL"  # Critical for staging database connectivity
```

### 2. Generated Correct DATABASE_URL Format
The correct format for Cloud SQL Unix socket connection is:
```
postgresql://postgres:[URL_ENCODED_PASSWORD]@/postgres?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres
```

Key points:
- Uses Unix socket path (`/cloudsql/...`)
- No SSL parameters needed (they cause errors with asyncpg)
- Password must be URL-encoded to handle special characters

### 3. Created Fix Script
Created `scripts/fix_staging_database_url.py` that:
- Generates the correct DATABASE_URL format
- Provides the exact gcloud command to update the secret
- Documents the solution based on previous learnings

## Action Required

### Step 1: Update the Secret in Google Cloud
Run this command to update the database-url-staging secret:
```bash
echo 'postgresql://postgres:qNdlZRHu%28Mlc%23%296K8LHm-lYi%5B7sc%7D25K@/postgres?host=/cloudsql/netra-staging:us-central1:staging-shared-postgres' | gcloud secrets versions add database-url-staging --data-file=- --project=netra-staging
```

**Note**: If the password is incorrect, get the correct one from:
```bash
gcloud secrets versions access latest --secret=postgres-password-staging --project=netra-staging
```

### Step 2: Verify the Secret
```bash
gcloud secrets versions access latest --secret=database-url-staging --project=netra-staging
```

### Step 3: Redeploy Services
```bash
python scripts/deploy_to_gcp.py --project netra-staging --build-local
```

## Prevention for Future

1. **Use Pre-deployment Validation**: Run `scripts/validate_staging_deployment.py` before deployments
2. **Maintain Secret Documentation**: Keep DATABASE_URL format documented in deployment specs
3. **Test Connections**: Always test database connectivity before marking deployment as successful

## Related Files
- `SPEC/learnings/auth_service_staging_errors_five_whys.xml` - Previous analysis of this issue
- `SPEC/database_connectivity_architecture.xml` - Database connection architecture
- `scripts/fix_staging_database_url.py` - Script to generate correct DATABASE_URL
- `staging_database_url.txt` - Generated DATABASE_URL (contains sensitive data)

## Success Criteria
After applying the fix:
1. Services should connect to the database without authentication errors
2. Health check endpoints should return 200 OK
3. Users should be able to sign in successfully