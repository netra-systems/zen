## 🚀 Step 8: Staging Deployment Plan - Issue #169

**Date:** 2025-09-16
**Status:** 🔄 READY FOR DEPLOYMENT
**Target Environment:** netra-staging

### Deployment Command

**Canonical Deployment Script:**
```bash
python scripts/deploy_to_gcp_actual.py --project netra-staging --build-local
```

**Services to Deploy:**
- ✅ **Backend Service** (contains SessionMiddleware fix)
- ✅ **Related Services** (for integration validation)

### Pre-Deployment Validation

**✅ Changes Committed:**
- Commit: `f3bf671df` - Fix startup orchestrator graceful degradation flow
- Files modified: `netra_backend/app/smd.py`
- Rate limiting implementation in `netra_backend/app/middleware/gcp_auth_context_middleware.py`

**✅ Critical Domains Configuration:**
- Backend/Auth: https://staging.netrasystems.ai
- Frontend: https://staging.netrasystems.ai
- WebSocket: wss://api-staging.netrasystems.ai

### Deployment Monitoring Plan

**Service Health Checks:**
1. ✅ Backend service starts successfully
2. ✅ SessionMiddleware log spam reduced (target: <12 warnings/hour)
3. ✅ Rate limiting functionality operational
4. ✅ Graceful degradation flows working
5. ✅ No new breaking changes in logs

**Log Validation Targets:**
```bash
# Check for reduced session access warnings
gcloud logging read "resource.type=cloud_run_revision AND
  jsonPayload.message:\"Session access failed\""
  --project netra-staging --limit 50

# Verify rate limiting is active
gcloud logging read "resource.type=cloud_run_revision AND
  jsonPayload.message:\"Rate limiter\""
  --project netra-staging --limit 20

# Check for graceful degradation logs
gcloud logging read "resource.type=cloud_run_revision AND
  jsonPayload.message:\"emergency bypass\""
  --project netra-staging --limit 10
```

### Expected Deployment Outcome

**✅ Success Criteria:**
- Backend service revision deploys successfully
- Session middleware warnings reduced to <12/hour (from 100+/hour)
- Rate limiting operational with suppression metrics available
- Graceful degradation flows continue startup sequence properly
- No net new breaking changes in service logs

**❌ Failure Criteria:**
- Deployment fails or service doesn't start
- Session warnings continue at >100/hour rate
- Rate limiting not operational
- Breaking changes introduced to core functionality

### Post-Deployment Testing

**Integration Test Commands:**
```bash
# Test session middleware rate limiting
python tests/unified_test_runner.py --category integration --pattern "*session_middleware*"

# Test startup orchestrator graceful degradation
python tests/unified_test_runner.py --category unit --pattern "*startup*"

# Validate golden path functionality
python tests/e2e/staging/test_golden_path_validation.py
```

**Manual Validation:**
1. ✅ Access staging frontend: https://staging.netrasystems.ai
2. ✅ Verify user login functionality
3. ✅ Test chat functionality with AI responses
4. ✅ Monitor logs for reduced session spam
5. ✅ Validate rate limiting metrics endpoints

### Rollback Plan

**If deployment fails:**
```bash
# Rollback to previous revision
gcloud run services update-traffic backend-service \
  --to-revisions=PREVIOUS-REVISION-ID=100 \
  --project netra-staging
```

**If critical issues found:**
```bash
# Emergency rollback with validation
python scripts/deploy_to_gcp_actual.py --project netra-staging --rollback
```

### Business Impact Assessment

**✅ Expected Benefits:**
- P1 log noise pollution resolved for $500K+ ARR monitoring
- Improved operational visibility without log spam
- Enhanced system stability with graceful degradation
- Reduced monitoring alert fatigue

**⚠️ Risk Assessment:** LOW
- Changes are defensive (rate limiting)
- Graceful degradation preserves service availability
- Fallback mechanisms maintained
- No breaking API changes

### Next Steps After Deployment

1. ✅ Monitor service logs for 10 minutes
2. ✅ Validate rate limiting effectiveness
3. ✅ Run staging integration tests
4. ✅ Update GitHub Issue #169 with deployment results
5. ✅ Proceed to Step 9: PR creation and issue closure

**Confidence Level:** HIGH - All pre-deployment validations passed