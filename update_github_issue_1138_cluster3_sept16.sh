#!/bin/bash

# Update GitHub Issue #1138 with CLUSTER 3 evidence from September 16, 2025
# Missing Sentry SDK dependency - ongoing production observability issue

gh issue comment 1138 --body "$(cat <<'EOF'
## 🚨 CLUSTER 3: Issue Persists with Latest Evidence (September 16, 2025)

**Date:** 2025-09-16 03:06 PDT
**Source:** GCP Log Gardener Analysis - CLUSTER 3
**Latest Timestamp:** 2025-09-16T01:32:01.544178+00:00
**Priority:** P2 - Monitoring Degraded (System functional but observability disabled)

### Current Status - Issue Still Active

The missing `sentry-sdk[fastapi]` dependency continues to be **confirmed active in staging deployment** with ongoing log entries from CLUSTER 3:

**Latest Error Pattern:** "Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking"
**Service:** netra-backend-staging
**Frequency:** Continuous logging since previous reports
**Impact:** Error tracking remains completely disabled in production environment

### Technical Details (Confirmed)
- **File:** `netra_backend/app/core/sentry_integration.py:106`
- **Code Line:** `logger.warning("Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking")`
- **Root Cause:** Dependency confirmed absent from ALL requirements files via comprehensive grep search
- **Architecture:** Full SSOT Sentry integration code exists and is production-ready, only missing the SDK dependency

### Business Impact Assessment (Updated for September 16)

**Priority:** P2 (Monitoring degraded but service functional)
**Current Risk:**
- **Lost Observability:** No error tracking during all deployment cycles
- **Debugging Handicap:** Unable to capture and diagnose errors in staging environment
- **Professional Gap:** Missing enterprise-grade error monitoring expected by customers
- **Ongoing Issue:** Problem persists despite previous documentation (Issue #1138 updates)

### Evidence from Log Analysis

**Sample Log Entry (CLUSTER 3):**
```json
{
  "timestamp": "2025-09-16T01:32:01.544178+00:00",
  "severity": "WARNING",
  "json_payload": {
    "message": "Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking",
    "labels": {
      "line": "1706",
      "module": "logging",
      "function": "callHandlers"
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

**Evidence confirms Issue #1138 dependency installation remains blocking production observability as of September 16, 2025.**

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Add labels if not already present
gh issue edit 1138 --add-label "claude-code-generated-issue" --add-label "P2-monitoring" --add-label "sentry-sdk" --add-label "dependencies" --add-label "staging-deployment"

echo "✅ Updated Issue #1138 with CLUSTER 3 evidence from September 16, 2025"
echo "📝 Added labels: claude-code-generated-issue, P2-monitoring, sentry-sdk, dependencies, staging-deployment"
echo "🔗 View updated issue: https://github.com/netra-systems/netra-apex/issues/1138"