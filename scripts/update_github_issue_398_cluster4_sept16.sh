#!/bin/bash

# Update GitHub Issue #398 with CLUSTER 4 evidence from September 16, 2025
# SERVICE_ID whitespace configuration hygiene issue

gh issue comment 398 --body "$(cat <<'EOF'
## 🧹 CLUSTER 4: Configuration Hygiene Issue - SERVICE_ID Whitespace (September 16, 2025)

**Date:** 2025-09-16 03:06 PDT
**Source:** GCP Log Gardener Analysis - CLUSTER 4
**Latest Evidence:** September 15, 2025 staging deployment
**Priority:** P3 - Configuration Hygiene (upgraded from P4 due to frequency)

### Latest Occurrence - CLUSTER 4 Analysis

The SERVICE_ID whitespace issue continues to occur in staging environment based on latest GCP log analysis:

#### **New Evidence from CLUSTER 4:**
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

#### **Frequency Analysis:**
- **Time Range:** 2025-09-15 18:00-19:06 PDT
- **Pattern:** Recurring during service startup
- **Location:** netra_backend.app.core.configuration
- **Impact:** Minor - Auto-corrected but creates log noise

### Current Status Assessment

✅ **System Functioning:** Auto-sanitization prevents functional issues
⚠️ **Configuration Hygiene:** Still indicates upstream configuration problem
📊 **Business Impact:** P3 - Minor maintenance issue affecting log cleanliness

### Primary Blocker Context

**Important:** This configuration hygiene issue is secondary to the **P0 monitoring module import failure** which remains the primary backend stability blocker. While SERVICE_ID whitespace is being auto-corrected and doesn't affect functionality, the monitoring module issue requires immediate attention for system stability.

### Recommended Next Steps

Based on the recurring nature of this issue, recommend escalating from P4 to P3 and implementing:

#### **Phase 1: Source Investigation (15 minutes)**
```bash
# Check deployment environment variables for whitespace
echo "$SERVICE_ID" | cat -A

# Audit configuration files
grep -n "SERVICE_ID" .env.staging.* | cat -A
grep -n "netra-backend" terraform-gcp-staging/*.tf | cat -A
```

#### **Phase 2: Configuration Cleanup (15 minutes)**
1. **Environment Variable Sources:**
   - `.env.staging.tests`
   - `.env.staging.e2e`
   - GCP Cloud Run environment variable settings
   - Terraform configuration files

2. **Deployment Script Validation:**
   - Add pre-deployment environment variable validation
   - Check for trailing whitespace in all environment variables

#### **Phase 3: Prevention (30 minutes)**
```python
# Add to startup validation
def validate_service_configuration():
    """Validate service configuration before startup"""
    service_id = os.getenv('SERVICE_ID', '').strip()
    original_service_id = os.getenv('SERVICE_ID', '')
    if service_id != original_service_id:
        raise ConfigurationError(f"SERVICE_ID contains whitespace: '{original_service_id}' -> '{service_id}'")
```

### Files to Update
1. **Environment Configuration:**
   - `.env.staging.tests` (check for `\n` in SERVICE_ID)
   - `.env.staging.e2e` (validate formatting)
   - `terraform-gcp-staging/main.tf` (environment variable definitions)

2. **Validation Code:**
   - `netra_backend/app/core/configuration/base.py` (add startup validation)
   - `scripts/deploy_to_gcp.py` (pre-deployment checks)

### Business Impact Update
- **Priority:** P3 (upgraded from P4 due to recurring frequency)
- **Risk:** Low - Auto-corrected but indicates process gaps
- **Effort:** ~1 hour total fix time
- **Value:** Improves configuration reliability and reduces log noise

### Success Criteria
- [ ] No SERVICE_ID sanitization warnings in staging logs for 24 hours
- [ ] Environment variable properly formatted without trailing characters
- [ ] Pre-deployment validation prevents whitespace in SERVICE_ID
- [ ] Configuration audit shows clean environment variable formatting

---

**RECOMMENDATION:** Schedule configuration cleanup after resolving the P0 monitoring module import failure. This issue is functional but affects configuration hygiene and log cleanliness.

**Evidence confirms Issue #398 configuration hygiene issue remains active as of September 16, 2025, with auto-correction preventing functional impact.**

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>
EOF
)"

# Add labels if not already present
gh issue edit 398 --add-label "claude-code-generated-issue" --add-label "P3-configuration" --add-label "service-id" --add-label "staging-deployment" --add-label "configuration-hygiene"

echo "✅ Updated Issue #398 with CLUSTER 4 evidence from September 16, 2025"
echo "📝 Added labels: claude-code-generated-issue, P3-configuration, service-id, staging-deployment, configuration-hygiene"
echo "🔗 View updated issue: https://github.com/netra-systems/netra-apex/issues/398"