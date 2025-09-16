#!/bin/bash

# GitHub Issue Update Script for Issue #398 - SERVICE_ID Sanitization (CLUSTER 3)
# Repository: netra-systems/netra-apex

echo "Updating GitHub issue #398 with CLUSTER 3 SERVICE_ID whitespace findings..."

gh issue comment 398 \
  --body "$(cat <<'EOF'
## 🔄 **CLUSTER 3 Update: SERVICE_ID Whitespace Issue Persists**

### **Latest Evidence (2025-09-15 18:00-19:06 PDT)**

The SERVICE_ID whitespace issue continues in staging environment:

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

### **📊 Frequency Analysis**
- **Pattern:** Recurring during service startup
- **Location:** netra_backend.app.core.configuration
- **Impact:** Auto-corrected but creates log noise
- **Priority Recommendation:** Upgrade from P4 → P3 due to persistence

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
- **Current Status:** P3 (Minor) - Auto-corrected but recurring
- **Risk:** Low - Functional impact minimal, but indicates process gaps
- **Effort:** ~1 hour total implementation time
- **Value:** Improved configuration reliability and reduced log noise

---

**Reference:** GCP-LOG-GARDENER-WORKLOG-last-1-hour-20250915-1906PDT.md (CLUSTER 3)
**Analysis:** CLUSTER 3 from comprehensive GCP log analysis
**Next Review:** After implementation of recommended fixes

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

echo "Issue #398 update comment posted successfully."
echo "Please verify the comment was added to: https://github.com/netra-systems/netra-apex/issues/398"