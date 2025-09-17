# AuthTicketManager Phase 2 Deployment Instructions (Issue #1296)

## Overview

This document provides step-by-step instructions for deploying the AuthTicketManager Phase 2 implementation to GCP staging and verifying the deployment.

## Changes Being Deployed

**Files Modified:**
- `/netra_backend/app/routes/auth_proxy.py` - Added `/auth/generate-ticket` endpoint
- Integration with existing AuthTicketManager implementation from Phase 1
- Compatibility endpoint for backward compatibility with tests

**New Endpoints:**
- `POST /api/v1/auth/generate-ticket` - Primary endpoint
- `POST /auth/generate-ticket` - Compatibility endpoint for tests

## Pre-Deployment Checklist

### 1. Verify Code Changes
```bash
# Check that the generate-ticket endpoint is implemented
grep -n "generate-ticket" netra_backend/app/routes/auth_proxy.py

# Verify AuthTicketManager imports are working
python -c "from netra_backend.app.websocket_core.unified_auth_ssot import AuthTicketManager; print('✅ AuthTicketManager imports successfully')"
```

### 2. Run Local Tests
```bash
# Run AuthTicketManager unit tests
python tests/unit/websocket_core/test_auth_ticket_manager.py

# Run integration tests for the new endpoint
python tests/integration/auth/test_generate_ticket_endpoint.py

# Validate Phase 2 implementation
python validate_phase2_implementation.py
```

## Deployment Commands

### Step 1: Deploy Backend Service to Staging
```bash
# Deploy only the backend service since we only modified auth_proxy.py
python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local --services backend

# Alternative: Full deployment if needed
python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local
```

### Step 2: Monitor Deployment
```bash
# Check deployment status
gcloud run services describe netra-backend-staging --region=us-central1 --project=netra-staging

# Monitor service logs during startup
gcloud logs tail netra-backend-staging --project=netra-staging
```

## Post-Deployment Validation

### Step 1: Run Staging Validation Script
```bash
# Run the comprehensive validation script
python validate_authticketmanager_phase2_staging.py --verbose

# Get JSON output for CI/CD integration
python validate_authticketmanager_phase2_staging.py --json > validation_results.json
```

### Step 2: Manual Testing
```bash
# Test health endpoint
curl -f https://staging.netrasystems.ai/health

# Test generate-ticket endpoint (should return 401/403)
curl -X POST https://staging.netrasystems.ai/api/v1/auth/generate-ticket
curl -X POST https://staging.netrasystems.ai/auth/generate-ticket

# Check OpenAPI docs for endpoint visibility
curl https://staging.netrasystems.ai/docs
```

### Step 3: Integration Tests
```bash
# Run e2e tests against staging
python tests/unified_test_runner.py --category e2e --env staging

# Run specific auth-related tests
python tests/unified_test_runner.py --category auth --env staging --real-services
```

## Validation Criteria

### ✅ Successful Deployment Indicators
- [ ] Backend service revision successfully deployed
- [ ] Health endpoint responds with HTTP 200
- [ ] `/api/v1/auth/generate-ticket` endpoint returns 401/403 for unauthenticated requests
- [ ] `/auth/generate-ticket` compatibility endpoint returns 401/403 for unauthenticated requests
- [ ] OpenAPI docs include the new endpoint
- [ ] No critical errors in service logs
- [ ] All existing functionality still works

### ❌ Deployment Failure Indicators
- [ ] Service fails to start or crashes during startup
- [ ] Health endpoint returns 500 or times out
- [ ] Generate-ticket endpoints return 404 (not found)
- [ ] Critical errors in service logs related to AuthTicketManager
- [ ] Existing endpoints broken or returning errors

## Rollback Procedures

If deployment fails or causes issues:

### Immediate Rollback
```bash
# Rollback to previous revision
gcloud run services update netra-backend-staging --revision-suffix=rollback --project=netra-staging

# Or use deployment script rollback
python scripts/deploy_to_gcp_actual.py --rollback --project=netra-staging
```

### Post-Rollback Validation
```bash
# Verify rollback successful
python validate_authticketmanager_phase2_staging.py

# Check that existing functionality works
curl https://staging.netrasystems.ai/health
```

## Monitoring & Logging

### Key Metrics to Monitor
- Service startup time and success rate
- Error rates on new endpoints
- Memory and CPU usage during ticket generation
- Redis connection health (for AuthTicketManager)

### Log Patterns to Watch For
```bash
# Success patterns
grep "AuthTicketManager initialized" /var/log/staging/backend.log
grep "Ticket generated successfully" /var/log/staging/backend.log

# Error patterns to investigate
grep "ERROR.*generate.ticket" /var/log/staging/backend.log
grep "Redis.*connection.*failed" /var/log/staging/backend.log
grep "AuthTicketManager.*initialization.*failed" /var/log/staging/backend.log
```

## Staging Environment Details

**Environment:** netra-staging  
**Region:** us-central1  
**Service URLs:**
- Backend/Auth: https://staging.netrasystems.ai
- Frontend: https://staging.netrasystems.ai
- WebSocket: wss://api-staging.netrasystems.ai

**Resources (Issue #1278 remediation):**
- Memory: 6Gi (increased for infrastructure reliability)
- CPU: 4 cores (increased for asyncio performance)
- Timeout: 600s (10 minutes with better resource allocation)

## Issue Tracking

**Primary Issue:** #1296 - AuthTicketManager Phase 2 Implementation  
**Related Issues:** 
- #1293 - AuthTicketManager core implementation (Phase 1 - Complete)
- #1295 - Legacy auth removal (Phase 3 - Pending)
- #1278 - Domain configuration update (infrastructure pressure handling)

## Success Criteria Summary

1. **Deployment Status:** Backend service successfully deployed with new endpoints
2. **Functional:** Both `/api/v1/auth/generate-ticket` and `/auth/generate-ticket` endpoints respond appropriately
3. **Integration:** AuthTicketManager properly integrated with existing auth flow
4. **Stability:** No regressions in existing functionality
5. **Performance:** Service starts within timeout and maintains healthy resource usage
6. **Monitoring:** No critical errors in logs, proper Redis connectivity

## Next Steps After Successful Deployment

1. **Phase 3 Planning:** Prepare for legacy auth removal (Issue #1295)
2. **Production Planning:** Evaluate Phase 2 performance and prepare production deployment
3. **Documentation Update:** Update API documentation with new endpoint details
4. **Monitoring Setup:** Configure alerts for AuthTicketManager metrics

---

**Created:** $(date +"%Y-%m-%d %H:%M:%S")  
**For Issue:** #1296 Phase 2 - AuthTicketManager Endpoint Implementation  
**Environment:** netra-staging