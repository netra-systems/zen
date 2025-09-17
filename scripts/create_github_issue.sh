#!/bin/bash

# GitHub Issue Creation Script for Goldenpath Integration Test Failure
# Repository: netra-systems/netra-apex

echo "Creating GitHub issue for goldenpath integration test failure..."

gh issue create \
  --title "🚨 RECURRING: Goldenpath Integration Tests Failing - Staging API Timeout (api.staging.netrasystems.ai)" \
  --label "goldenpath,staging,integration,api-timeout,P0-critical,service-unavailable,recurring-issue" \
  --body "$(cat <<'EOF'
## 🚨 **CRITICAL: Golden Path Integration Test Failure - Staging API Timeout**

### **Test Failure Details**
- **Test:** \`test_golden_path_baseline_complete_flow\` 
- **File:** \`test_plans/phase5/test_golden_path_protection_validation.py:67\`
- **Error:** API service unreachable timeout at \`api.staging.netrasystems.ai\`
- **Specific Error:** 
  \`\`\`
  HTTPSConnectionPool(host='api.staging.netrasystems.ai', port=443): Read timed out. (read timeout=10)
  \`\`\`
- **Test Type:** Goldenpath integration tests
- **Impact:** **BLOCKS $500K+ ARR business value validation**

### **⚠️ RECURRING PATTERN IDENTIFIED**

This failure matches **EXACT patterns** from previously resolved issues:

#### **Related Resolved Issues:**
- **Issue #1263** - Database Connectivity Timeout ✅ RESOLVED
  - **Root Cause:** Missing VPC connector configuration
  - **Resolution:** Added VPC connector flags to deployment workflow

- **Issue #1229** - Staging Database Timeout ✅ RESOLVED  
  - **Resolution:** Increased timeout from 13s → 30s for Cloud SQL compatibility

- **Issue #586** - Staging Deployment Timeout ✅ RESOLVED
  - **Resolution:** Timeout optimization for Cloud Run environment

- **Issue #395** - Staging Timeout Configuration ✅ RESOLVED
  - **Resolution:** Increased staging timeout from 0.5s to 1.5s

### **🔍 ERROR PATTERN ANALYSIS**

Repository documentation shows **multiple instances** of identical error:
\`\`\`
api.staging.netrasystems.ai timeout
HTTPSConnectionPool(host='api.staging.netrasystems.ai', port=443): Read timed out
Backend Health: https://api.staging.netrasystems.ai/health → TIMEOUT
\`\`\`

### **📋 IMMEDIATE ACTION REQUIRED**

Based on previous resolutions, investigate:

1. **VPC Connector Configuration** (Issue #1263 fix)
2. **Timeout Values** (Issues #1229, #586, #395 fixes)  
3. **Cloud Run Environment** connectivity
4. **Staging Infrastructure** health

### **📚 Reference Materials**

- **Remediation Plan:** \`reports/websocket/WEBSOCKET_STAGING_TIMEOUT_REMEDIATION_PLAN.md\`
- **Previous Resolution:** \`ISSUE_1263_DATABASE_CONNECTIVITY_REMEDIATION_COMPLETE.md\`
- **Test Documentation:** \`test_plans/phase5/test_golden_path_protection_validation.py\`

### **🎯 SUCCESS CRITERIA**

- [ ] Staging API health endpoint responds within 10s timeout
- [ ] Golden path test \`test_golden_path_baseline_complete_flow\` passes
- [ ] No regression in other integration tests
- [ ] Infrastructure monitoring confirms stable connectivity

### **⏰ URGENCY: P0 - CRITICAL**

**Business Impact:** Blocks validation of $500K+ ARR business value during deployment consolidation.

**Expected Resolution:** Apply same fixes that resolved Issues #1263, #1229, #586, #395.

---

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)"

echo "Issue creation command executed. Check output above for issue URL and ID."