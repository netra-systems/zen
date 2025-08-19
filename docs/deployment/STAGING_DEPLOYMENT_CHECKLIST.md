# Staging Deployment Checklist

## Pre-Deployment Validation

### 1. Configuration Files
- [x] `config/staging.env` - Updated with proper staging URLs
- [x] `terraform-gcp/terraform.staging.tfvars` - Fixed database URL to use Cloud SQL socket
- [x] GitHub Actions workflow (`deploy-staging.yml`) - Configured correctly

### 2. Secrets Management
- [ ] GCP_STAGING_SA_KEY - Set in GitHub Secrets
- [ ] STAGING_DB_PASSWORD - Set in GitHub Secrets
- [ ] CLICKHOUSE_PASSWORD - Set in GitHub Secrets
- [ ] JWT_SECRET_KEY - Generated (32+ characters)
- [ ] FERNET_KEY - Generated (44 characters)
- [ ] GOOGLE_OAUTH_CLIENT_ID_STAGING - Optional
- [ ] GOOGLE_OAUTH_CLIENT_SECRET_STAGING - Optional

### 3. Infrastructure Requirements
- [ ] GCP Project: `netra-staging` exists
- [ ] Cloud SQL instance configured
- [ ] Redis instance available
- [ ] ClickHouse instance available (or placeholder)
- [ ] Artifact Registry created
- [ ] Required APIs enabled

### 4. Code Validation
- [x] Staging deployment readiness tests created
- [x] Integration flow tests created
- [x] Health check validator script created
- [ ] Run: `python test_runner.py --level integration --no-coverage --fast-fail`
- [ ] Run: `python scripts/validate_staging_config.py`

## During Deployment

### 5. Build & Push
- [ ] Backend Docker image built
- [ ] Frontend Docker image built
- [ ] Auth service Docker image built (if applicable)
- [ ] Images pushed to Artifact Registry

### 6. Deploy Services
- [ ] Backend deployed to Cloud Run
- [ ] Frontend deployed to Cloud Run
- [ ] Auth service deployed (if applicable)
- [ ] Environment variables set correctly
- [ ] Secrets mounted properly

### 7. Networking & Security
- [ ] HTTPS enforced on all endpoints
- [ ] CORS configured for staging domains
- [ ] Security headers present
- [ ] WebSocket upgraded to WSS

## Post-Deployment Validation

### 8. Health Checks
- [ ] Run: `python scripts/validate_staging_health.py https://api.staging.netrasystems.ai`
- [ ] `/health` endpoint responding
- [ ] `/ready` endpoint responding
- [ ] `/live` endpoint responding

### 9. Service Connectivity
- [ ] Database connection working
- [ ] Redis connection working
- [ ] ClickHouse connection working (if used)
- [ ] WebSocket connections working

### 10. Performance Validation
- [ ] Response time < 1000ms
- [ ] Throughput > 10 RPS
- [ ] Error rate < 5%

### 11. Monitoring & Logging
- [ ] Logs visible in Cloud Logging
- [ ] Metrics being collected
- [ ] Alerts configured (optional for staging)

## Rollback Plan

### If Deployment Fails:
1. Check logs: `gcloud logging read "resource.type=cloud_run_revision"`
2. Rollback Terraform: `terraform plan -destroy -var-file=staging.tfvars`
3. Restore previous Cloud Run revision
4. Investigate root cause

## Critical Issues Fixed

1. **Database URL** - Changed from localhost to Cloud SQL socket format
2. **Staging Environment Variables** - Added proper staging URLs and CORS configuration
3. **Test Coverage** - Created comprehensive staging validation tests
4. **Health Check Validation** - Added script to validate deployment health

## Next Steps After Successful Deployment

1. Run full integration test suite against staging
2. Validate all API endpoints
3. Test WebSocket connections
4. Verify authentication flow
5. Load test with expected traffic patterns
6. Update DNS records if needed

## Important URLs

- Frontend: https://staging.netrasystems.ai
- Backend API: https://api.staging.netrasystems.ai
- WebSocket: wss://api.staging.netrasystems.ai/ws
- Health Check: https://api.staging.netrasystems.ai/health

## Contact for Issues

- DevOps Team: For infrastructure issues
- Backend Team: For API issues
- Frontend Team: For UI issues

---

**Last Updated**: 2025-08-18
**Status**: Ready for Deployment ✅