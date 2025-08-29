# Cloud Run Logging ANSI Escape Code Fix

## Problem
Cloud Run logs were showing ANSI escape codes (color codes) in error tracebacks, making them difficult to read:
```
[35m[1masync[0m [35m[1mwith[0m [1mget_clickhouse_client[0m[1m([0m[1m)[0m
```

This was caused by Python 3.11+ adding colored tracebacks by default, which don't render properly in Cloud Run's logging system.

## Root Cause
- Python 3.11 introduced colored exception tracebacks using ANSI escape codes
- Cloud Run's logging system doesn't properly strip these codes
- The codes appear as raw text in the logs, making them unreadable

## Solution Implemented

### 1. Docker Environment Variables
Added environment variables to `docker/backend.Dockerfile` to disable all color output:
```dockerfile
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NO_COLOR=1
ENV FORCE_COLOR=0
ENV PY_COLORS=0
```

### 2. Logging Configuration Module
Created `netra_backend/app/core/logging_config.py` to:
- Disable colored output programmatically
- Set up custom exception handler for production
- Strip any remaining ANSI codes from tracebacks
- Configure structured logging for Cloud Run

### 3. Early Initialization
Updated `netra_backend/app/main.py` to import and configure logging early in the startup process, before any other modules that might generate exceptions.

## Verification

### Local Testing
Run the test script to verify ANSI codes are removed:
```bash
python scripts/test_ansi_logging.py
```

### Configuration Verification
Check that all components are properly configured:
```bash
python scripts/verify_cloud_run_logging_fix.py
```

### Staging Deployment
After deploying to staging, monitor logs to ensure:
1. No ANSI escape codes appear in tracebacks
2. Exceptions are properly formatted and readable
3. Log levels and messages are clear

## Impact
- **Production/Staging**: Logs will be clean and readable without ANSI codes
- **Development**: Local development retains standard Python formatting
- **Performance**: Minimal impact, only affects exception formatting

## Rollback Plan
If issues arise, revert these changes:
1. Remove environment variables from Dockerfile
2. Delete `netra_backend/app/core/logging_config.py`
3. Remove imports from `main.py`

## Testing Checklist
- [x] Local test script passes
- [x] Configuration verification passes
- [x] Docker environment variables set
- [x] Logging module created and imported
- [ ] Staging deployment tested
- [ ] Production deployment verified