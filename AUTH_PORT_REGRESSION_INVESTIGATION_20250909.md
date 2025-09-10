# Auth Service Port Regression Investigation - Issue #128

**Date**: September 9, 2025  
**Issue**: Auth service port configuration regression affecting Cloud Run deployment  
**Status**: CRITICAL - Potential auth service deployment failure  

## Executive Summary

✅ **NO REGRESSION FOUND** - Auth service port configuration is correct and consistent across all environments.

## Investigation Findings

### 1. Current Auth Service Port Configuration

**Cloud Run Deployment (Production/Staging)**:
- **Port**: 8080 (correctly configured)
- **Configuration Source**: `/scripts/deploy_to_gcp.py` line 134
- **Container Port**: 8080 (matches Cloud Run expected port)

**Local Development**:
- **Port**: 8081 (correctly configured) 
- **Configuration Source**: `/docker-compose.yml` line 158-159
- **Default in main.py**: 8081 (line 829: `port = int(get_env().get("PORT", "8081"))`)

### 2. Configuration Analysis

#### A. Cloud Run Configuration (deploy_to_gcp.py)
```python
ServiceConfig(
    name="auth",
    directory="auth_service", 
    port=8080,  # ✅ CORRECT - Cloud Run standard port
    dockerfile="dockerfiles/auth.staging.alpine.Dockerfile",
    cloud_run_name="netra-auth-service",
    # ... rest of config
)
```

#### B. Local Development Configuration (docker-compose.yml)
```yaml
dev-auth:
  environment:
    PORT: 8081  # ✅ CORRECT - Avoids conflict with backend on 8000
  ports:
    - "${DEV_AUTH_PORT:-8081}:8081"  # ✅ CORRECT mapping
```

#### C. Auth Service Main Application (main.py)
```python
# Line 828-829: Proper fallback logic
port = int(get_env().get("PORT", "8081"))  # ✅ CORRECT - 8081 for dev, 8080 for Cloud Run
```

### 3. Recent Changes Analysis

**No Port-Related Regressions Found**:
- ✅ Git history shows no recent changes to auth service port configuration
- ✅ All environment-specific configurations are consistent
- ✅ Docker compose files maintain correct port mappings

### 4. Environment-Specific Port Matrix

| Environment | Auth Port | Backend Port | Frontend Port | Notes |
|-------------|-----------|--------------|---------------|-------|
| **Local Dev** | 8081 | 8000 | 3000 | No conflicts |
| **Test** | 8081 | 8000 | 3000 | Matches dev |
| **Staging** | 8080 | 8000 | 3000 | Cloud Run standard |
| **Production** | 8080 | 8000 | 3000 | Cloud Run standard |

### 5. Cloud Run Service Status Verification

**Expected Behavior**:
- Auth service should deploy to Cloud Run on port 8080
- Load balancer should route to `auth.staging.netrasystems.ai` → port 8080
- Health checks should succeed on `/health` endpoint

**Potential Issues to Check**:
1. **Secret Manager Configuration**: OAuth credentials, JWT secrets
2. **VPC Connector**: Database and Redis connectivity
3. **Cloud SQL Proxy**: Database connection timeout
4. **Resource Allocation**: Memory/CPU limits sufficient

## Root Cause Analysis

### What Was Expected vs What Was Found

**Expected Issue**: Port configuration regression causing deployment failures  
**Actual Finding**: No port regression - configuration is correct and consistent

### Likely Causes of 404 Errors

If staging endpoints are returning 404, the issue is **NOT** auth service port configuration. Possible causes:

1. **Cloud Run Service Not Deployed**: 
   - Service may not be deployed to Cloud Run
   - Service may have failed to start due to other issues

2. **Load Balancer Misconfiguration**:
   - Backend services not properly mapped
   - Health checks failing

3. **Secret Manager Issues**:
   - Missing OAuth credentials
   - Invalid JWT secrets
   - Database connection secrets missing

4. **Resource Issues**:
   - Service failing due to memory/CPU constraints
   - Database connection timeouts

## Recommended Next Steps

### 1. Verify Cloud Run Service Status
```bash
gcloud run services list --region=us-central1 --project=netra-staging
gcloud run services describe netra-auth-service --region=us-central1 --project=netra-staging
```

### 2. Check Service Health
```bash
curl -I https://auth.staging.netrasystems.ai/health
curl -v https://auth.staging.netrasystems.ai/
```

### 3. Validate Secrets Configuration
```bash
python scripts/deploy_to_gcp.py --project netra-staging --check-secrets
```

### 4. Deploy with Full Validation
```bash
python scripts/deploy_to_gcp.py --project netra-staging --build-local --run-checks --check-secrets --check-apis
```

## Conclusion

✅ **Auth service port configuration is CORRECT and requires no changes**

The 404 errors mentioned in issue #128 are NOT caused by port configuration regression. The auth service is properly configured to use:
- Port 8080 for Cloud Run deployment (staging/production)
- Port 8081 for local development
- Proper environment variable fallbacks in place

**Investigation should focus on**:
1. Cloud Run deployment status
2. Secret Manager configuration
3. Load balancer configuration
4. Service startup logs

**No code changes required** for auth service port configuration.