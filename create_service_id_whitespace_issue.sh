#!/bin/bash

# GitHub Issue Creation Script for SERVICE_ID Whitespace Configuration Issue (CLUSTER 3)
# Repository: netra-systems/netra-apex
# Priority: P3 - Configuration Issue (Minor but recurring)

echo "Creating GitHub issue for SERVICE_ID whitespace configuration hygiene..."

gh issue create \
  --title "GCP-other | P3 | SERVICE_ID Environment Variable Contains Trailing Whitespace" \
  --label "claude-code-generated-issue,configuration,environment-variables,gcp-staging,hygiene,P3-minor" \
  --body "$(cat <<'EOF'
## 📋 **CLUSTER 3: SERVICE_ID Configuration Whitespace Issue**

### **Issue Summary**
SERVICE_ID environment variable contains trailing whitespace character causing runtime sanitization warnings in staging environment. While auto-corrected by the system, this indicates configuration cleanup needed.

### **Current Behavior**
```json
{
    "context": {
        "name": "netra_backend.app.core.configuration",
        "service": "netra-backend-staging"
    },
    "message": "SERVICE_ID contained whitespace - sanitized from 'netra-backend\\n' to 'netra-backend'",
    "timestamp": "2025-09-15T18:05:12.891000+00:00",
    "severity": "NOTICE"
}
```

### **🔍 Technical Details**
- **Pattern:** "SERVICE_ID contained whitespace - sanitized from 'netra-backend\\n' to 'netra-backend'"
- **Severity:** P3 - Configuration Issue
- **Impact:** Minor - Auto-corrected but indicates configuration cleanup needed
- **Service:** netra-backend-staging
- **Time Range:** 2025-09-15 18:00-19:06 PDT
- **Frequency:** Recurring during service startup
- **Location:** netra_backend.app.core.configuration

### **📊 Error Pattern Analysis**
From **GCP Log Analysis (CLUSTER 3)**:
- **Issue Type:** Configuration Issues
- **Root Cause:** Environment variable SERVICE_ID has trailing newline character (`\n`)
- **System Response:** Automatic sanitization with warning log
- **Business Impact:** None (auto-corrected) but affects log cleanliness

### **🛠️ Expected Behavior**
- SERVICE_ID environment variable should be properly formatted without trailing whitespace
- No sanitization warnings during service startup
- Clean configuration validation during deployment

### **🔧 Proposed Resolution**

#### **Phase 1: Configuration Source Identification**
1. **Check deployment environment variables:**
   ```bash
   # Check for whitespace in SERVICE_ID
   echo "$SERVICE_ID" | cat -A
   # Look for trailing characters
   ```

2. **Audit configuration files:**
   - `.env.staging.tests`
   - `.env.staging.e2e`
   - Docker environment configuration
   - GCP Cloud Run environment variable settings

#### **Phase 2: Configuration Cleanup**
1. **Remove trailing whitespace from SERVICE_ID**
2. **Update deployment scripts to validate environment variables**
3. **Add pre-deployment configuration validation**

#### **Phase 3: Prevention**
```python
def validate_service_configuration():
    """Validate service configuration before startup"""
    service_id = os.getenv('SERVICE_ID', '').strip()
    if service_id != os.getenv('SERVICE_ID', ''):
        raise ConfigurationError("SERVICE_ID contains whitespace")
```

### **📝 Files to Investigate**
1. **Environment Configuration:**
   - `.env.staging.tests`
   - `.env.staging.e2e`
   - Docker environment files
   - GCP Cloud Run environment variable settings

2. **Configuration Validation:**
   - `netra_backend/app/core/configuration/base.py`
   - Deployment scripts in `scripts/`
   - Docker configuration files

### **✅ Success Criteria**
- [ ] No SERVICE_ID sanitization warnings in staging logs
- [ ] Environment variable properly formatted without trailing characters
- [ ] Configuration validation passes without sanitization
- [ ] Pre-deployment checks prevent whitespace in environment variables

### **📈 Business Impact**
- **Priority:** P3 (Minor) - Configuration hygiene issue
- **Risk:** Low - Auto-corrected but indicates process gaps
- **Maintenance:** Improves configuration reliability and log cleanliness

### **🔗 Related Issues & Context**
- **Reference:** GCP-LOG-GARDENER-WORKLOG-last-1-hour-20250915-1906PDT.md
- **Cluster:** CLUSTER 3 from GCP log analysis
- **Related:** Configuration hygiene improvements (broader pattern)

### **⏰ Timeline**
- **Urgency:** P3 - Non-critical but recurring
- **Estimated Fix Time:** 30 minutes (simple configuration cleanup)
- **Validation:** Quick staging deployment verification

---

**Note:** This is a minor configuration hygiene issue that auto-corrects but should be resolved to maintain clean configuration practices and reduce log noise.

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

echo "SERVICE_ID whitespace configuration issue creation command executed."
echo "Check output above for issue URL and ID."