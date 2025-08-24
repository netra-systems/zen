# Critical Remediation Plan - Staging Environment Issues
**Date:** 2025-08-24  
**Severity:** CRITICAL  
**Environment:** Staging  

## Executive Summary
Real LLM testing on staging has revealed critical security vulnerabilities and system failures that must be addressed before production deployment. The most severe issue is the complete failure of cost limit enforcement, which poses significant financial risk.

## Priority Matrix

### P0 - CRITICAL (Immediate Action Required)
These issues present immediate security or financial risk.

#### 1. Cost Limit Enforcement Failure
**Issue:** Cost limits are not being enforced for LLM API calls  
**Test:** `test_real_llm_security.py::test_cost_limit_enforcement`  
**Risk:** Unbounded API costs, potential for abuse, financial exposure  
**Root Cause:** Missing or misconfigured rate limiting/cost tracking middleware  

**Remediation Steps:**
```python
# 1. Implement cost tracking middleware
# Location: netra_backend/app/middleware/cost_limiter.py
class CostLimitMiddleware:
    async def __call__(self, request, call_next):
        # Track API costs per user/tenant
        # Enforce hard limits
        # Return 429 when limits exceeded
        
# 2. Add to FastAPI app initialization
# Location: netra_backend/app/main.py
app.add_middleware(CostLimitMiddleware)

# 3. Configure limits per tier
# Location: netra_backend/app/config/tier_limits.py
TIER_LIMITS = {
    "free": {"daily_cost_usd": 1.0},
    "early": {"daily_cost_usd": 10.0},
    "mid": {"daily_cost_usd": 100.0},
    "enterprise": {"daily_cost_usd": 1000.0}
}
```

**Validation:**
- [ ] Run `test_real_llm_security.py` - must pass
- [ ] Verify 429 responses when limits exceeded
- [ ] Check cost tracking in database
- [ ] Test with real LLM calls

### P1 - HIGH (Deploy Blocker)
These issues prevent proper system operation.

#### 2. WebSocket Server 500 Errors
**Issue:** WebSocket connections failing with Internal Server Error  
**Test:** Multiple agent collaboration tests  
**Risk:** Core functionality unavailable, user experience impact  

**Remediation Steps:**
```bash
# 1. Check WebSocket server logs
python scripts/check_staging_logs.py --service websocket --errors

# 2. Verify database connectivity
python scripts/test_database_connection.py --env staging

# 3. Check auth service integration
curl -X GET https://staging-api.netra.ai/health/auth

# 4. Fix connection string issues
# Update: netra_backend/app/websocket_core/server.py
```

**Validation:**
- [ ] WebSocket connections establish successfully
- [ ] Run `test_agent_collaboration_real.py`
- [ ] Check server logs for errors
- [ ] Monitor connection stability

#### 3. Missing Environment Variables
**Issue:** CLICKHOUSE_DEFAULT_PASSWORD not configured  
**Impact:** ClickHouse integration failures  

**Remediation Steps:**
```bash
# 1. Update staging secrets
gcloud secrets versions add CLICKHOUSE_DEFAULT_PASSWORD --data-file=-

# 2. Update deployment configuration
# File: organized_root/staging/app.yaml
env_variables:
  CLICKHOUSE_DEFAULT_PASSWORD: ${CLICKHOUSE_DEFAULT_PASSWORD}

# 3. Restart services
gcloud app deploy --project netra-staging
```

### P2 - MEDIUM (Fix Within Sprint)
These issues affect functionality but have workarounds.

#### 4. Import Path Issues
**Issue:** Multiple import errors in tests  
**Files Affected:**
- `test_database_migration_rollback.py` (partially fixed)
- `test_first_user_journey.py` (email_service)

**Remediation Steps:**
```python
# 1. Fix email service import
# File: tests/e2e/test_first_user_journey.py
from netra_backend.app.services.notification_service import EmailNotificationService

# 2. Validate all test imports
python scripts/validate_test_imports.py

# 3. Update import mapping documentation
# File: SPEC/import_management_architecture.xml
```

**Validation:**
- [ ] All tests import correctly
- [ ] No ImportError exceptions
- [ ] Documentation updated

## Implementation Timeline

### Day 1 (Immediate)
- [ ] Deploy cost limit enforcement (P0)
- [ ] Add monitoring alerts for cost overruns
- [ ] Emergency hotfix to staging

### Day 2-3
- [ ] Fix WebSocket server issues (P1)
- [ ] Configure missing environment variables (P1)
- [ ] Deploy fixes to staging

### Day 4-5
- [ ] Fix all import issues (P2)
- [ ] Run full regression test suite
- [ ] Update documentation

## Monitoring Checklist

### Pre-Deployment
- [ ] All P0 issues resolved
- [ ] All P1 issues resolved  
- [ ] Security review completed
- [ ] Cost tracking verified

### Post-Deployment
- [ ] Monitor cost metrics dashboard
- [ ] Check WebSocket connection metrics
- [ ] Review error logs hourly for 24h
- [ ] Verify all E2E tests passing

## Testing Protocol

### Regression Testing
```bash
# Run full test suite with real LLM
python unified_test_runner.py --categories integration e2e --real-llm --env staging

# Specific security tests
python -m pytest tests/e2e/test_real_llm_security.py -xvs

# WebSocket stability
python -m pytest tests/e2e/websocket/ -xvs

# Cost tracking validation
python scripts/validate_cost_tracking.py --env staging
```

### Performance Validation
- Response time < 2s for API calls
- WebSocket latency < 100ms
- Cost calculation accuracy > 99%
- No memory leaks after 1000 requests

## Rollback Plan

If issues persist after deployment:

1. **Immediate Rollback**
   ```bash
   gcloud app versions list --project netra-staging
   gcloud app services set-traffic default --splits=<previous-version>=100
   ```

2. **Data Recovery**
   - Restore from hourly backups if needed
   - Validate data integrity

3. **Communication**
   - Notify stakeholders immediately
   - Document issues in incident report

## Success Criteria

- [ ] Zero cost limit bypass vulnerabilities
- [ ] 100% WebSocket connection success rate
- [ ] All E2E tests passing with real LLM
- [ ] No 500 errors in 24h period
- [ ] Cost tracking accuracy validated

## Contact Points

- **Security Issues:** security@netra.ai
- **Platform Issues:** platform@netra.ai  
- **On-Call:** Use PagerDuty escalation

## Appendix: Test Commands

```bash
# Quick validation
python scripts/staging_health_check.py

# Full E2E with real LLM
python unified_test_runner.py --categories e2e --real-llm --env staging

# Security-specific tests
python -m pytest tests/e2e/test_real_llm_security.py tests/e2e/test_token_validation.py -xvs

# WebSocket tests
python -m pytest tests/e2e/websocket/ -xvs --env staging

# Cost tracking audit
python scripts/audit_cost_tracking.py --start-date 2025-08-24 --env staging
```

---
**Document Status:** ACTIVE  
**Next Review:** After P0/P1 fixes deployed  
**Owner:** Platform Team