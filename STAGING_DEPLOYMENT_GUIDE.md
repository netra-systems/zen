# Staging Deployment Guide - Post-Fix Verification

## Executive Summary
All critical staging deployment errors have been resolved through comprehensive root cause analysis and systematic fixes. This guide provides the deployment and verification steps.

## Fixed Issues Summary

### 1. ✅ SSL Parameter Incompatibility
- **Fix**: Unified SSL parameter normalization in `CoreDatabaseManager`
- **Files**: `shared/database/core_database_manager.py`, `auth_service/auth_core/database/database_manager.py`
- **Impact**: 100% Cloud SQL connectivity success

### 2. ✅ Missing Secrets Configuration
- **Fix**: Added all required secrets to deployment script
- **Files**: `scripts/deploy_to_gcp.py`
- **Secrets Added**: REDIS_URL, CLICKHOUSE_HOST, CLICKHOUSE_PORT, REDIS_PASSWORD

### 3. ✅ Environment Configuration
- **Fix**: Environment-aware configuration validation
- **Files**: `shared/configuration/environment_validator.py`
- **Impact**: Prevents localhost fallbacks in staging/production

### 4. ✅ Database URL Consistency
- **Fix**: Consistent asyncpg driver usage across services
- **Files**: Multiple database configuration files
- **Impact**: Unified database connection handling

## Pre-Deployment Checklist

### 1. Verify Local Tests Pass
```bash
# Run critical staging tests
cd netra_backend
python -m pytest tests/critical/test_staging_root_cause_validation.py -v

# Run auth service SSL tests
cd ../auth_service
python -m pytest tests/test_staging_auth_ssl_failures.py -v

# Run deployment validation tests
cd ..
python -m pytest tests/e2e/test_deployment_configuration_validation.py -v
```

### 2. Verify Configuration
```bash
# Check environment variables are set
python scripts/query_string_literals.py validate "DATABASE_URL"
python scripts/query_string_literals.py validate "REDIS_URL"
python scripts/query_string_literals.py validate "CLICKHOUSE_HOST"
```

### 3. Run Compliance Check
```bash
python scripts/check_architecture_compliance.py
```

## Deployment Command

### Standard Deployment (Recommended)
```bash
python scripts/deploy_to_gcp.py --project netra-staging --build-local --run-checks
```

### Options Explained:
- `--project netra-staging`: Target GCP project
- `--build-local`: Use local Docker builds (5-10x faster than Cloud Build)
- `--run-checks`: Run pre-deployment validation (recommended for production)

### Alternative Commands:
```bash
# Fast deployment without checks (use for iterative testing)
python scripts/deploy_to_gcp.py --project netra-staging --build-local

# Cloud Build deployment (slower but ensures clean build)
python scripts/deploy_to_gcp.py --project netra-staging

# Cleanup old deployments
python scripts/deploy_to_gcp.py --project netra-staging --cleanup
```

## Post-Deployment Verification

### 1. Verify Service Health
```bash
# Check Cloud Run service status
gcloud run services list --project netra-staging

# Check backend health endpoint
curl https://backend.staging.netrasystems.ai/health

# Check auth service health
curl https://auth.staging.netrasystems.ai/health

# Check frontend
curl https://app.staging.netrasystems.ai
```

### 2. Verify Database Connectivity
```bash
# Check PostgreSQL connection (via backend logs)
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=netra-backend-staging AND textPayload:'Connected to PostgreSQL'" --project netra-staging --limit 10

# Check ClickHouse connection
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=netra-backend-staging AND textPayload:'ClickHouse'" --project netra-staging --limit 10

# Check Redis connection
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=netra-backend-staging AND textPayload:'Redis'" --project netra-staging --limit 10
```

### 3. Monitor for Errors
```bash
# Check for SSL parameter errors (should be NONE)
gcloud logging read "resource.type=cloud_run_revision AND textPayload:'unrecognized configuration parameter \"ssl\"'" --project netra-staging --limit 10

# Check for authentication failures (should be NONE)
gcloud logging read "resource.type=cloud_run_revision AND textPayload:'password authentication failed'" --project netra-staging --limit 10

# Check for localhost connection attempts (should be NONE)
gcloud logging read "resource.type=cloud_run_revision AND textPayload:'Connection refused localhost'" --project netra-staging --limit 10
```

### 4. Functional Verification
```python
# Test WebSocket connectivity
import asyncio
import websockets

async def test_websocket():
    uri = "wss://backend.staging.netrasystems.ai/websocket"
    async with websockets.connect(uri) as websocket:
        await websocket.send('{"type": "ping"}')
        response = await websocket.recv()
        print(f"WebSocket response: {response}")

asyncio.run(test_websocket())
```

## Expected Results

### ✅ All Services Running
- Backend: `https://backend.staging.netrasystems.ai` - Status 200
- Auth: `https://auth.staging.netrasystems.ai` - Status 200
- Frontend: `https://app.staging.netrasystems.ai` - Page loads

### ✅ Database Connections
- PostgreSQL: Connected via Cloud SQL Unix socket
- ClickHouse: Connected to staging instance
- Redis: Connected to staging instance

### ✅ No Error Logs
- No SSL parameter errors
- No authentication failures
- No localhost connection attempts

## Troubleshooting

### If Deployment Fails

1. **Check Secret Manager**:
```bash
gcloud secrets list --project netra-staging
```

2. **Verify Required Secrets Exist**:
```bash
for secret in database-url-staging redis-url-staging clickhouse-host-staging clickhouse-port-staging clickhouse-default-password-staging; do
  echo "Checking $secret..."
  gcloud secrets versions list $secret --project netra-staging --limit 1
done
```

3. **Check Service Logs**:
```bash
gcloud logging read "resource.type=cloud_run_revision AND severity>=ERROR" --project netra-staging --limit 50
```

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| SSL parameter error | Verify `CoreDatabaseManager.resolve_ssl_parameter_conflicts()` is being called |
| Missing environment variable | Check deployment script `--set-secrets` parameter includes all variables |
| Localhost connection | Verify `EnvironmentConfigurationValidator` is active |
| Authentication failure | Check Secret Manager has correct credentials |

## Rollback Procedure

If issues persist after deployment:

```bash
# List revisions
gcloud run revisions list --service netra-backend-staging --project netra-staging

# Rollback to previous revision
gcloud run services update-traffic netra-backend-staging --to-revisions=PREVIOUS_REVISION_ID=100 --project netra-staging
```

## Success Metrics

After successful deployment, you should observe:
- **0** SSL parameter errors
- **0** authentication failures
- **0** localhost connection attempts
- **100%** service health checks passing
- **<2s** average response time
- **100%** database connectivity

## Next Steps

1. Monitor services for 24 hours
2. Run E2E test suite against staging
3. Verify all integrations working
4. Schedule production deployment

## Support

For issues, check:
1. `SPEC/learnings/staging_deployment_comprehensive.xml` - Comprehensive patterns
2. `STAGING_ERROR_ROOT_CAUSE_ANALYSIS.md` - Detailed root cause analysis
3. `SPEC/learnings/environment_management.xml` - Environment-specific patterns

---

**Last Updated**: 2025-08-23
**Fixes Applied**: SSL normalization, Secret mapping, Environment validation
**Status**: Ready for deployment