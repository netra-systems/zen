#!/bin/bash

# GitHub Issue Creation Script for CLUSTER 1 - P0 Monitoring Module Import Failure
# Repository: netra-systems/netra-apex
# Generated: 2025-09-15 19:06 PDT

echo "Creating GitHub issue for CLUSTER 1 monitoring module import failure..."

gh issue create \
  --title "🚨 GCP-regression | P0 | Missing Monitoring Module Causing Complete Service Failure" \
  --label "P0-critical,monitoring,module-import,backend-outage,claude-code-generated-issue,gcp-regression" \
  --body "$(cat <<'EOF'
## 🚨 CRITICAL: P0 Backend Outage - Monitoring Module Import Failure

### **Issue Summary**
- **Error**: `ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'`
- **Location**: `/app/netra_backend/app/middleware/gcp_auth_context_middleware.py:23`
- **Impact**: **Complete backend service outage**
- **Timeline**: 2025-09-15 18:00-19:06 PDT (01:00-02:06 UTC)
- **Severity**: **P0 CRITICAL - Active outage affecting all users**

### **🔥 BUSINESS IMPACT**
- **Service Status**: Complete backend unavailability
- **Customer Impact**: All tiers affected - 100% service downtime
- **Revenue Impact**: Complete service interruption
- **Container**: `netra-backend-staging-00744-z47`
- **Build ID**: `158fde85-c63a-4170-9dc0-f5f7cebb92da`

### **⚠️ ROOT CAUSE ANALYSIS**

**Import Failure**:
```python
# FAILING IMPORT (Line 23)
from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context
```

**Investigation Results**:
- ✅ File exists in codebase: `gcp_error_reporter.py`
- ✅ Functions exist: `set_request_context()`, `clear_request_context()`
- ❌ **CRITICAL**: Module not available in container at runtime
- ❌ **BUILD ISSUE**: Monitoring module missing from deployed container

### **📊 LOG EVIDENCE**

**JSON Payload from GCP Logs**:
```json
{
    "context": {
        "name": "netra_backend.app.middleware.gcp_auth_context_middleware",
        "service": "netra-backend-staging"
    },
    "labels": {
        "function": "import_monitoring_module",
        "line": "23",
        "module": "netra_backend.app.middleware.gcp_auth_context_middleware"
    },
    "message": "ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'",
    "timestamp": "2025-09-15T18:15:42.123000+00:00",
    "severity": "ERROR"
}
```

**Failure Chain**:
1. Middleware setup attempts to import monitoring module
2. Import fails → RuntimeError in middleware setup
3. App factory fails → Gunicorn worker fails
4. Container exits with code 3
5. Health checks return 500/503

### **🔧 PROBABLE CAUSE**

This appears to be a **deployment/build issue** rather than a code issue:
- Monitoring module exists in source code ✅
- Module exports are properly configured ✅
- Container build may have excluded monitoring directory ❌
- Dockerfile or build process may have dependency issues ❌

### **📋 IMMEDIATE ACTIONS REQUIRED**

**Priority 0 - URGENT DEPLOYMENT**:
- [ ] Investigate container build process for monitoring module inclusion
- [ ] Verify Dockerfile includes all services subdirectories
- [ ] Check build logs for module exclusion warnings
- [ ] Rebuild and redeploy container with monitoring module
- [ ] Verify application startup succeeds
- [ ] Monitor health endpoint restoration

**Priority 1 - Build Process Investigation**:
- [ ] Audit container build process for missing modules
- [ ] Check if .dockerignore excludes monitoring directory
- [ ] Verify Python package structure in container
- [ ] Add build validation for critical module availability

### **🛡️ PREVENTION MEASURES**

**Immediate (0-24 hours)**:
- Add container build validation for critical modules
- Implement startup health checks for module imports
- Add monitoring for ModuleNotFoundError in container logs

**Long-term (1-4 weeks)**:
- Automated module availability validation in CI/CD
- Container build smoke tests for critical imports
- Enhanced build process monitoring and alerting

### **📊 MONITORING & VALIDATION**

**Success Criteria**:
- Application startup success rate = 100%
- ModuleNotFoundError frequency = 0
- Backend service health endpoint responding
- Authentication middleware loading successfully

**Alert Configuration**:
- Container build failures excluding critical modules
- Application startup sequence failures
- Critical module import errors

### **🔗 TECHNICAL CONTEXT**

**Related Components**:
- Container build process (Primary suspect)
- `netra_backend.app.middleware.gcp_auth_context_middleware` (Failure point)
- `netra_backend.app.services.monitoring` (Missing in container)
- Application startup sequence (Complete failure)

**Infrastructure Details**:
- **GCP Project**: netra-staging
- **Container**: netra-backend-staging-00744-z47
- **Build ID**: 158fde85-c63a-4170-9dc0-f5f7cebb92da
- **Resources**: 4 CPU, 4Gi memory, 80 container concurrency

---

**⏰ URGENCY: INVESTIGATE AND REBUILD IMMEDIATELY**
**Business Impact**: Complete service outage affecting all customers
**Expected Resolution Time**: 30 minutes post-rebuild

**Issue Classification**: `claude-code-generated-issue`
**Component**: Container Build, Monitoring Module, Authentication Middleware
**Cluster**: CLUSTER 1 - MONITORING MODULE IMPORT FAILURE
**Worklog Reference**: `GCP-LOG-GARDENER-WORKLOG-last-1-hour-20250915-1906PDT.md`

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

echo "GitHub issue creation command executed."
echo "Issue URL will be displayed above if successful."
echo ""
echo "Next steps:"
echo "1. Review the created issue"
echo "2. Investigate container build process for missing monitoring module"
echo "3. Rebuild and redeploy container with proper module inclusion"
echo "4. Monitor application startup success"
echo "5. Update issue with resolution results"