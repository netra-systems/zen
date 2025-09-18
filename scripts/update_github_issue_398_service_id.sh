#!/bin/bash

# GitHub Issue Update Script for Issue #398 - SERVICE_ID Sanitization (CLUSTER 3)
# Repository: netra-systems/netra-apex

echo "Updating GitHub issue #398 with CLUSTER 3 SERVICE_ID whitespace findings..."

gh issue comment 398 \
  --body "$(cat <<'EOF'
## 🔄 **CLUSTER 3 Update: SERVICE_ID Whitespace Issue Persists - NEW EVIDENCE**

### **Latest Evidence (2025-09-16T16:00:00Z)**

**⚠️ ESCALATION: 14 NEW incidents detected in the last 1 hour!**

The SERVICE_ID whitespace issue continues to occur frequently in staging environment:

```json
{
    "context": {
        "name": "netra_backend.app.core.configuration",
        "service": "netra-backend-staging"
    },
    "message": "SERVICE_ID contained whitespace - sanitized from 'netra-backend\\n' to 'netra-backend'",
    "timestamp": "2025-09-16T00:42:52.984106Z",
    "severity": "WARNING"
}
```

### **📊 Updated Frequency Analysis**
- **New Incident Count:** 14 incidents in the last 1 hour (2025-09-16T15:00Z to 2025-09-16T16:00Z)
- **Current Severity:** P2 MEDIUM (recurring configuration issue)
- **Pattern:** Recurring during service startup and container restarts
- **Location:** netra_backend.app.core.configuration
- **Source:** netra-backend-staging service logs
- **Business Impact:** Configuration inconsistencies affecting service identification
- **Priority Status:** **CONFIRMED P2** due to high frequency and persistence

### **🔧 Immediate Actions Recommended**

**Phase 1: Source Investigation (15 minutes)**
```bash
# Check for whitespace in environment variables
echo "$SERVICE_ID" | cat -A
grep -n "SERVICE_ID" .env.staging.* | cat -A
```

**Phase 2: Configuration Cleanup (15 minutes)**
- Audit `.env.staging.tests` and `.env.staging.e2e` for trailing newlines
- Check GCP Cloud Run environment variable settings
- Validate terraform configuration files

**Phase 3: Prevention (30 minutes)**
```python
def validate_service_configuration():
    service_id = os.getenv('SERVICE_ID', '').strip()
    if service_id != os.getenv('SERVICE_ID', ''):
        raise ConfigurationError("SERVICE_ID contains whitespace")
```

### **📝 Files to Update**
1. `.env.staging.tests` - Remove trailing whitespace from SERVICE_ID
2. `.env.staging.e2e` - Validate environment variable formatting
3. `netra_backend/app/core/configuration/base.py` - Add startup validation
4. `scripts/deploy_to_gcp.py` - Pre-deployment environment validation

### **✅ Success Criteria**
- [ ] No SERVICE_ID sanitization warnings for 24 hours
- [ ] Environment variables properly formatted
- [ ] Pre-deployment validation prevents whitespace
- [ ] Clean configuration audit results

### **📈 Business Impact Assessment**
- **Current Status:** P2 MEDIUM - Auto-corrected but recurring with high frequency
- **Risk:** Medium - Configuration inconsistencies affecting service identification
- **Effort:** ~1 hour total implementation time
- **Value:** Improved configuration reliability and reduced log noise
- **Escalation Reason:** 14 incidents in 1 hour indicates persistent configuration problem

### **🏷️ Labels**
- `claude-code-generated-issue`
- `P2-medium`
- `configuration`
- `staging-environment`

---

**Reference:** GCP-LOG-GARDENER-WORKLOG-last-1-hour-2025-09-16-1600.md (CLUSTER 3)
**Analysis:** CLUSTER 3 from comprehensive GCP log analysis
**Timestamp:** 2025-09-16T16:00:00Z
**Next Review:** After implementation of recommended fixes

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

echo "Issue #398 update comment posted successfully."
echo "Please verify the comment was added to: https://github.com/netra-systems/netra-apex/issues/398"