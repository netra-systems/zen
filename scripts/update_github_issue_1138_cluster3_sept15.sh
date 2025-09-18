#!/bin/bash

# Update GitHub Issue #1138 with CLUSTER 3 evidence from Sept 15, 2025
# Missing sentry-sdk[fastapi] dependency

gh issue comment 1138 --body "$(cat <<'EOF'
## 🚨 CLUSTER 3 Recurrence: Sept 15, 2025 21:41-22:41 PDT

**Critical Evidence:** Sentry SDK missing dependency actively impacting staging deployment

### Current Status
- **Error Pattern:** "Sentry SDK not available - install sentry-sdk[fastapi] to enable error tracking"
- **Service:** netra-backend-staging
- **Time Window:** Sept 15, 2025 21:41-22:41 PDT (1 hour analysis)
- **Frequency:** Multiple instances throughout critical service period
- **Impact:** P2 - Error tracking completely disabled during service outage

### Critical Timing Correlation
The missing Sentry SDK occurred simultaneously with major service stability issues (CLUSTER 1/2 service failures), creating a **critical observability gap** exactly when error tracking was most needed for diagnostics.

### Technical Details
- **File:** `netra_backend/app/core/sentry_integration.py:106`
- **Code Path:** Proper error handling exists, only missing dependency installation
- **Root Cause:** `sentry-sdk[fastapi]` absent from all requirements files
- **Current Behavior:** Service functional but error monitoring disabled

### Business Impact (Escalated Priority)
- **Lost Observability:** No error tracking during critical deployment issues
- **Debugging Handicap:** Unable to diagnose service failures effectively
- **Enterprise Gap:** Missing professional monitoring during customer-impacting period
- **Correlation Risk:** Sentry unavailable exactly when CLUSTER 1/2 failures occurred

### Immediate Fix Required
```bash
# Add to requirements.txt
echo "sentry-sdk[fastapi]>=1.38.0" >> requirements.txt
```

### Validation
- Deploy and verify no "Sentry SDK not available" warnings
- Confirm Sentry initialization success in logs
- Test error capture functionality

**Priority Justification:** P2 confirmed - monitoring degraded during critical operational period when error tracking was most vital.

🤖 Generated with [Claude Code](https://claude.ai/code)
EOF
)"