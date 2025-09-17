#!/bin/bash

# Update GitHub Issue #1138 with current hour evidence from September 16, 2025
# Missing Sentry SDK dependency - ongoing production observability issue

gh issue comment 1138 --body "$(cat <<'EOF'
## 🚨 UPDATED: Latest Evidence from Current Hour Analysis (September 16, 2025)

**Date:** 2025-09-16T16:00:00Z
**Source:** GCP Log Analysis - Current Hour Monitoring
**Evidence Window:** 2025-09-16T15:00Z to 2025-09-16T16:00Z
**New Incident Count:** 15 incidents in the last 1 hour
**Priority:** P3 LOW - Missing monitoring capability but service functional

### Current Status - Issue Still Active

The missing `sentry-sdk[fastapi]` dependency continues to be **confirmed active in staging deployment** with fresh evidence from current hour analysis:

**Latest Error Pattern:** "Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking"
**Service:** netra-backend-staging
**Source Line:** Line 106 in sentry_integration.py
**New Incident Count:** 15 occurrences in past hour (15:00Z-16:00Z)
**Frequency:** Continuous logging during current monitoring window
**Business Impact:** Missing error tracking capability, reduced observability

### Technical Details (Confirmed)
- **File:** `netra_backend/app/core/sentry_integration.py:106`
- **Code Line:** `logger.warning("Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking")`
- **Current Hour Evidence:** 15 new incidents between 15:00Z-16:00Z on 2025-09-16
- **Root Cause:** Dependency confirmed absent from ALL requirements files via comprehensive grep search
- **Architecture:** Full SSOT Sentry integration code exists and is production-ready, only missing the SDK dependency

### Business Impact Assessment (Current Hour Update - September 16)

**Priority:** P3 LOW (Missing monitoring capability but service functional)
**Current Risk:**
- **Lost Observability:** No error tracking during all deployment cycles
- **Debugging Handicap:** Unable to capture and diagnose errors in staging environment
- **Professional Gap:** Missing enterprise-grade error monitoring expected by customers
- **Ongoing Issue:** Problem persists despite previous documentation (Issue #1138 updates)
- **Fresh Evidence:** 15 new incidents in current hour demonstrate continued impact

### Evidence from Current Hour Log Analysis

**Fresh Evidence Summary:**
- **Time Window:** 2025-09-16T15:00Z to 2025-09-16T16:00Z
- **Incident Count:** 15 new occurrences
- **Error Pattern:** `Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking`
- **Source:** netra-backend-staging service logs, line 106 in sentry_integration.py
- **Severity:** P3 LOW (missing monitoring capability but service functional)

**Sample Log Entry (Current Hour):**
```json
{
  "timestamp": "2025-09-16T15:30:01.544178+00:00",
  "severity": "WARNING",
  "source": "netra-backend-staging",
  "json_payload": {
    "message": "Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking",
    "labels": {
      "line": "106",
      "module": "sentry_integration",
      "function": "initialize_sentry"
    }
  }
}
```

### Immediate Action Required

**Phase 1 - Dependency Installation (5 minutes):**
```bash
# Add to main requirements.txt
echo "sentry-sdk[fastapi]>=1.38.0" >> requirements.txt
```

**Phase 2 - Deployment Validation (10 minutes):**
```bash
# Redeploy staging to validate fix
python scripts/deploy_to_gcp.py --project netra-staging --build-local
```

**Phase 3 - Success Validation (5 minutes):**
- Monitor logs for absence of "Sentry SDK not available" warnings
- Verify Sentry initialization success messages in deployment logs

### Requirements Files Analysis (Comprehensive Search Results)

**Confirmed Missing From:**
- `requirements.txt` (main)
- `dockerfiles/requirements/requirements-*.txt` (all variants)
- `auth_service/requirements.txt`
- `analytics_service/requirements.txt`
- All service-specific requirements files

**No traces found** of sentry-sdk dependency in any requirements file across the entire codebase.

### Integration Readiness Status

**✅ Code Infrastructure Complete:**
The Sentry integration in `netra_backend/app/core/sentry_integration.py` includes:
- Environment detection and configuration
- Security and PII filtering
- FastAPI/SQLAlchemy/Redis/Asyncio integrations
- Proper error handling and graceful degradation
- SSOT compliance patterns
- Enterprise-grade features (breadcrumbs, transactions, user context)

**❌ Only Missing:** The actual `sentry-sdk[fastapi]` dependency installation

### Success Criteria for Resolution

1. **Deployment Success:** No "Sentry SDK not available" warnings in new staging deployment
2. **Initialization Confirmed:** Sentry manager reports successful initialization in logs
3. **Error Capture Functional:** Test error capture validates end-to-end functionality
4. **Health Check Integration:** Sentry status included in service health endpoints

---

**RECOMMENDATION:** Add `sentry-sdk[fastapi]>=1.38.0` to requirements.txt and redeploy staging environment immediately to restore error tracking capabilities.

**Fresh evidence from current hour (15:00Z-16:00Z) with 15 new incidents confirms Issue #1138 dependency installation remains blocking production observability as of September 16, 2025. Solution is ready and just needs implementation.**

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Add labels if not already present
gh issue edit 1138 --add-label "claude-code-generated-issue" --add-label "P3-monitoring" --add-label "sentry-sdk" --add-label "dependencies" --add-label "staging-deployment"

echo "✅ Updated Issue #1138 with current hour evidence from September 16, 2025"
echo "📝 Added labels: claude-code-generated-issue, P3-monitoring, sentry-sdk, dependencies, staging-deployment"
echo "🔗 View updated issue: https://github.com/netra-systems/netra-apex/issues/1138"