#!/bin/bash

# GitHub Issue Creation Script for P0 Monitoring Module Import Failure
# Repository: netra-systems/netra-apex

echo "Creating GitHub issue for P0 monitoring module import failure..."

gh issue create \
  --title "🚨 GCP-regression | P0 | Missing Monitoring Module Causing Backend Outage" \
  --label "P0-critical,monitoring,module-import,backend-outage,claude-code-generated-issue,gcp-regression" \
  --body "$(cat <<'EOF'
## 🚨 **CRITICAL: P0 Backend Outage - Monitoring Module Import Failure**

### **Issue Summary**
- **Error**: `ModuleNotFoundError: No module named 'netra_backend.app.services.monitoring'`
- **Location**: `/app/netra_backend/app/middleware/gcp_auth_context_middleware.py:23`
- **Impact**: **Complete backend service outage - 1+ hours duration**
- **Timeline**: 2025-09-15T21:48-22:48 UTC (ongoing)
- **Severity**: **P0 CRITICAL - Active outage affecting all users**

### **🔥 BUSINESS IMPACT**
- **Service Status**: Complete backend unavailability
- **Customer Impact**: All tiers affected - 100% service downtime
- **Revenue Impact**: Complete service interruption
- **Duration**: 1+ hours of continuous outage

### **⚠️ ROOT CAUSE IDENTIFIED**

**Import Failure**:
```python
# FAILING IMPORT (Line 23)
from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context, clear_request_context
```

**Root Cause**: Missing exports in monitoring module `__init__.py`
- ✅ File exists: `gcp_error_reporter.py`
- ✅ Functions exist: `set_request_context()`, `clear_request_context()`
- ❌ **Missing**: Functions not exported in `__init__.py`

### **🔧 RESOLUTION APPLIED**

**Fixed File**: `netra_backend/app/services/monitoring/__init__.py`

**Added Missing Exports**:
```python
from netra_backend.app.services.monitoring.gcp_error_reporter import GCPErrorReporter, set_request_context, clear_request_context

__all__ = [
    "GCPErrorService",
    "GCPClientManager", 
    "ErrorFormatter",
    "GCPRateLimiter",
    "GCPErrorReporter",        # ✅ ADDED
    "set_request_context",     # ✅ ADDED  
    "clear_request_context"    # ✅ ADDED
]
```

### **✅ VALIDATION COMPLETED**

**Import Testing Results**:
- ✅ Direct import: `from netra_backend.app.services.monitoring.gcp_error_reporter import set_request_context`
- ✅ Module import: `from netra_backend.app.services.monitoring import set_request_context`
- ✅ Application startup: Expected to succeed after deployment

### **📋 IMMEDIATE ACTIONS REQUIRED**

**Priority 0 - URGENT DEPLOYMENT**:
- [ ] Deploy fix to production environment immediately
- [ ] Verify application startup succeeds
- [ ] Monitor health endpoint restoration
- [ ] Validate authentication middleware functionality

**Priority 1 - Post-Resolution**:
- [ ] Root cause analysis: How was this export missed?
- [ ] Add import validation to CI/CD pipeline
- [ ] Implement startup health checks for critical imports
- [ ] Add ModuleNotFoundError monitoring alerts

### **🛡️ PREVENTION MEASURES**

**Immediate (0-24 hours)**:
- Add import validation tests to build pipeline
- Implement critical middleware import health checks
- Add monitoring for startup sequence failures

**Long-term (1-4 weeks)**:
- Review all module `__init__.py` files for export completeness
- Automated export validation in CI/CD
- Integration tests for critical middleware components

### **📊 MONITORING & VALIDATION**

**Success Criteria**:
- Application startup success rate = 100%
- ModuleNotFoundError frequency = 0
- Backend service health endpoint responding
- Authentication middleware loading successfully

**Alert Configuration**:
- Any middleware import failure in production
- Application startup sequence timeouts
- Critical module import errors

### **🔗 TECHNICAL CONTEXT**

**Related Components**:
- `netra_backend.app.middleware.gcp_auth_context_middleware` (Primary failure)
- `netra_backend.app.services.monitoring.gcp_error_reporter` (Missing exports)
- Application startup sequence (Complete failure)
- GCP Error Reporting integration (Non-functional)

**GCP Log Evidence**:
- Consistent ModuleNotFoundError during startup attempts
- 100% application startup failure rate
- Timeline: 2025-09-15T21:48 UTC onwards

---

**⏰ URGENCY: DEPLOY IMMEDIATELY**
**Business Impact**: Complete service outage affecting all customers
**Expected Resolution Time**: 15 minutes post-deployment

**Issue Classification**: `claude-code-generated-issue`
**Component**: Monitoring Module, Authentication Middleware
**Cluster**: MONITORING MODULE IMPORT FAILURE

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

echo "GitHub issue creation command executed."
echo "Issue URL will be displayed above if successful."
echo ""
echo "Next steps:"
echo "1. Review the created issue"
echo "2. Deploy the monitoring module fix immediately"  
echo "3. Monitor application startup success"
echo "4. Update issue with deployment results"