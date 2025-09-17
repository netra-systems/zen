#!/bin/bash

# Update GitHub Issue #398 with CLUSTER 3 evidence from Sept 15, 2025
# SERVICE_ID Environment Variable Contains Trailing Whitespace

gh issue comment 398 --body "$(cat <<'EOF'
## 🚨 CLUSTER 3 Recurrence: Sept 15, 2025 21:41-22:41 PDT

**Latest Evidence:** SERVICE_ID whitespace issue persists in staging deployment

### Current Status
- **Pattern:** SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
- **Service:** netra-backend-staging
- **Time Window:** Sept 15, 2025 21:41-22:41 PDT (1 hour analysis)
- **Frequency:** Multiple instances during critical service period
- **Impact:** Configuration hygiene degraded, operational noise

### Technical Details
- **Source:** GCP Log Analysis - Latest deployment logs
- **Auto-Correction:** System sanitizes but logs WARNING level messages
- **Root Cause:** Environment variable contains trailing newline character
- **Business Risk:** P3 (Minor recurring - functional impact minimal but process gaps evident)

### Operational Impact During Critical Period
This configuration issue occurred during the same timeframe as major service stability issues (CLUSTER 1/2), contributing to operational noise when clear diagnostics were most critical.

**Evidence Pattern:**
```
WARNING: SERVICE_ID contained whitespace - sanitized from 'netra-backend\n' to 'netra-backend'
```

### Recommended Action (15 min fix)
1. **Source Investigation:** Check deployment scripts and .env files
2. **Configuration Cleanup:** Remove trailing whitespace/newlines
3. **Prevention:** Add validation to deployment pipeline

**Files to Check:**
- `.env.staging.tests`
- `.env.staging.e2e`
- `scripts/deploy_to_gcp.py`
- `netra_backend/app/core/configuration/base.py`

### Success Criteria
- No SERVICE_ID sanitization warnings in next deployment
- Clean configuration values in all environments
- Improved operational clarity during critical periods

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)"