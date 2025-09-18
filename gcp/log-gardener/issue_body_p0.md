## Problem
Backend service is in a continuous crash loop due to missing `get_unified_config` import from `netra_backend.app.config`. This is a P0 critical issue blocking the Golden Path - users cannot login or get AI responses.

## Error Details
```python
File "/app/netra_backend/app/db/postgres_events.py", line 13, in <module>
    from netra_backend.app.config import get_unified_config
ImportError: cannot import name 'get_unified_config' from 'netra_backend.app.config'
```

## Impact
- **Service Status**: Backend service completely down (crash loop with exit code 3)
- **Business Impact**: $500K+ ARR at risk - no user can access the platform
- **Golden Path**: ❌ BLOCKED - Cannot validate user login → AI response flow
- **Frequency**: 107 instances in last hour (continuous crash loop)
- **Time Range**: 2025-09-17T23:36:02Z to 2025-09-17T23:45:32Z
- **Service Revision**: netra-backend-staging-00827-lxh

## Root Cause Analysis
The `get_unified_config` function appears to be missing from `/netra_backend/app/config.py`. This is likely a regression from recent SSOT configuration changes or incomplete migration.

## Related Issues
- #1308 - SessionManager import conflicts (marked resolved but may be related)
- Configuration migration from legacy `DatabaseConfig` to unified config system

## Logs
Full GCP logs available at: `/Users/anthony/Desktop/netra-apex/gcp_logs_backend.json`
GCP Log Gardener Worklog: `/Users/anthony/Desktop/netra-apex/gcp/log-gardener/GCP-LOG-GARDENER-WORKLOG-last-1-hour-2025-09-17-16-45.md`

## Proposed Fix
1. Check `/netra_backend/app/config.py` for missing `get_unified_config` function
2. Either restore the function or update imports in `postgres_events.py` to use correct config pattern
3. Verify all database-related modules use consistent configuration import pattern
4. Test service startup locally before deployment

## Acceptance Criteria
- [ ] Backend service starts successfully without crash loop
- [ ] All configuration imports resolved consistently across codebase
- [ ] Service passes health checks and responds to requests
- [ ] Golden Path validation restored (users can login and get AI responses)

## Priority
**P0 Critical** - Service completely down, blocking all user access