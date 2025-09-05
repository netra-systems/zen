# MessageRouter SSOT Violation - Critical Fix Completed

## Executive Summary
✅ **FIXED**: Critical staging error `'MessageRouter' object has no attribute 'register_handler'` resolved through SSOT compliance.

## Problem Analysis (Five Whys)
1. **Why did registration fail?** → MessageRouter missing `register_handler` attribute
2. **Why no register_handler?** → Two different MessageRouter classes with incompatible interfaces  
3. **Why two classes?** → SSOT violation - duplicate implementations
4. **Why not caught earlier?** → Mixed imports across codebase
5. **Why staging but not dev?** → Deployment caching (Python bytecode/Docker layers)

## Root Cause
**SSOT VIOLATION**: Two MessageRouter classes existed:
- ✅ `netra_backend/app/websocket_core/handlers.py` → Has `add_handler()` (CORRECT)
- ❌ `netra_backend/app/services/websocket/message_router.py` → Has `register_handler()` (DELETED)

## Solution Implemented
1. **Deleted duplicate MessageRouter** at `services/websocket/message_router.py`
2. **Updated ALL imports** to use canonical `websocket_core.handlers.MessageRouter`
3. **Fixed all method calls** from `register_handler()` to `add_handler()`
4. **Created comprehensive test** at `tests/mission_critical/test_message_router_failure.py`

## Files Changed
- **Deleted**: `netra_backend/app/services/websocket/message_router.py`
- **Updated**: 7 files with corrected imports and method calls
- **Created**: Mission-critical test suite for SSOT compliance

## Test Results
```
✅ MessageRouter SSOT compliant
✅ Has add_handler() method (correct)
✅ Does NOT have register_handler() (correct)
✅ Duplicate MessageRouter removed
✅ All imports point to canonical version
✅ AgentMessageHandler registration works
```

## Deployment Instructions
```bash
# 1. Clear Python bytecode
find . -name "*.pyc" -delete
find . -name "__pycache__" -delete

# 2. Deploy with cache clearing
python scripts/deploy_to_gcp.py --project netra-staging --no-cache --force-rebuild

# 3. Verify deployment
gcloud logging read "Registered new AgentMessageHandler" --project=netra-staging --limit=10
```

## Prevention Measures
1. **Lint for duplicates**: `grep -r "^class ClassName" --include="*.py"`
2. **Run SSOT test**: `python tests/mission_critical/test_message_router_failure.py`
3. **Always deploy with**: `--no-cache` flag for critical fixes
4. **Document canonical imports** in `SPEC/canonical_imports.xml`

## Learnings Saved
- Created: `SPEC/learnings/message_router_staging_failure_20250904.xml`
- Updated: `SPEC/learnings/index.xml` with new entry
- Test: `tests/mission_critical/test_message_router_failure.py`

## Status
✅ **READY FOR DEPLOYMENT** - All tests pass, SSOT violation fixed, staging should work correctly.