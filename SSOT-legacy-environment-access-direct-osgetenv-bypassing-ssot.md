# SSOT Legacy Environment Access Violation - Issue #722

**GitHub Issue**: https://github.com/netra-systems/netra-apex/issues/722
**Priority**: P1 - High Impact SSOT Legacy Violation
**Status**: In Progress

## Problem Summary
Multiple files directly access `os.environ` instead of using SSOT `IsolatedEnvironment`, violating architectural standards and risking **$12K MRR loss**.

## Business Impact
- **Golden Path Risk**: Environment configuration errors affect user authentication and service connectivity
- **Documented Financial Risk**: $12K MRR loss potential from configuration inconsistencies
- **System-Wide Effect**: Affects multiple critical services (auth, WebSocket, corpus admin)
- **Race Conditions**: Multiple services accessing environment variables differently leads to configuration drift

## Files Affected
- `netra_backend/app/logging/auth_trace_logger.py:284, 293, 302`
- `netra_backend/app/admin/corpus/unified_corpus_admin.py:155, 281`
- `netra_backend/app/websocket_core/types.py:349-355`
- `netra_backend/app/core/auth_startup_validator.py:514-520`

## Evidence
```python
# VIOLATION: Direct os.environ access
env = os.getenv('ENVIRONMENT', '').lower()
corpus_base_path = os.getenv('CORPUS_BASE_PATH', '/data/corpus')
os.getenv('K_SERVICE'),  # Cloud Run service name
```

## Solution Plan
Replace all `os.getenv()` calls with `get_env()` from `shared.isolated_environment` (SSOT pattern).

## Progress Log

### Step 0: SSOT Audit - COMPLETED
- ✅ Discovered critical legacy SSOT violation
- ✅ Created GitHub Issue #722
- ✅ Created progress tracker file
- ✅ Identified 4 affected files with specific line numbers

### Step 1: Discover and Plan Tests - IN PROGRESS
- [ ] Discover existing tests protecting against breaking changes
- [ ] Plan new SSOT tests to reproduce violation
- [ ] Follow TEST_CREATION_GUIDE.md best practices

### Next Steps
1. Discover existing tests for affected files
2. Plan SSOT-compliant test suite
3. Execute remediation plan
4. Validate all tests pass
5. Create PR and close issue