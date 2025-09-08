# Staging Backend 503 Service Unavailable - 5 Whys Root Cause Analysis

**Date:** September 7, 2025  
**Issue:** Staging backend returning 503 Service Unavailable on all endpoints  
**Impact:** All E2E tests failing, staging environment completely down  
**Investigator:** Claude Code  

## CRITICAL ERROR IDENTIFIED

```
DeterministicStartupError: Factory pattern initialization failed: 
WebSocket manager creation requires valid UserExecutionContext. 
Import-time initialization is prohibited. Use request-scoped factory pattern instead.
```

## 5 WHYS ANALYSIS

### WHY 1: Why is the staging backend returning 503 Service Unavailable?
**Answer:** The Cloud Run service is failing to start up. Worker processes are exiting with "Application startup failed. Exiting."

**Evidence:**
- GCP logs show: `[ERROR] Application startup failed. Exiting.`
- Health endpoint returning 503 on both URLs
- Worker process exit with code 3

### WHY 2: Why is the application startup failing?
**Answer:** The deterministic startup sequence is failing during Phase 5 (Services Setup) when initializing factory patterns.

**Evidence:**
- Error trace shows failure in `SMD._phase5_services_setup()` → `_initialize_factory_patterns()`
- `DeterministicStartupError: Factory pattern initialization failed`

### WHY 3: Why is factory pattern initialization failing?
**Answer:** The startup code is calling `get_websocket_manager()` without a required `user_context` parameter at application startup.

**Evidence:**
- Line 1557 in SMD: `websocket_manager=get_websocket_manager()`
- WebSocket manager now requires UserExecutionContext for security isolation
- Import-time initialization is prohibited by new architecture

### WHY 4: Why was get_websocket_manager() changed to require user_context?
**Answer:** Security migration to prevent multi-user data leakage through singleton WebSocket managers. The architecture was updated to use factory patterns with per-user isolation.

**Evidence:**
- Code comment: "SECURITY MIGRATION: Compatibility wrapper for get_websocket_manager"  
- Function raises ValueError if user_context is None
- User Context Architecture requires request-scoped factory patterns

### WHY 5: Why wasn't the startup code updated when the WebSocket manager was migrated?
**Answer:** The security migration focused on runtime request handling but missed the startup/initialization code paths that were still using the old singleton pattern.

**Evidence:**
- AgentInstanceFactory configuration still used `get_websocket_manager()` directly
- Factory pattern initialization happens during startup before any user requests
- No user context available during startup phase

## ROOT CAUSE SUMMARY

**Primary Cause:** Startup code calling `get_websocket_manager()` without user context during factory initialization

**Contributing Factors:**
1. Security migration to factory patterns was incomplete
2. Startup code not updated to match new architecture patterns  
3. Missing validation that startup code works with new WebSocket architecture

## IMMEDIATE FIX IMPLEMENTED

**File:** `netra_backend/app/smd.py` line 1557  
**Change:** 
```python
# OLD (broken)
websocket_manager=get_websocket_manager(),

# NEW (fixed) 
websocket_manager=None,  # Will be created per-request in UserExecutionContext pattern
```

**Rationale:** 
- AgentInstanceFactory accepts `websocket_manager=None` 
- WebSocket managers will be created per-request with proper user context
- Aligns with User Context Architecture requirements

## PREVENTION MEASURES

1. **Architecture Compliance:** All migration changes must include startup code validation
2. **Testing Coverage:** E2E tests must catch startup failures before deployment  
3. **Staging Validation:** Health checks must be part of deployment pipeline
4. **Code Review:** Security migrations require comprehensive impact analysis

## DEPLOYMENT STATUS

- **Fix Applied:** ✅ SMD startup code updated
- **Ready for Deploy:** ✅ Change is minimal and targeted
- **Risk Level:** Low - Parameter already supported as optional
- **Validation Plan:** Deploy and verify staging health endpoints respond successfully

## ERROR BEHIND THE ERROR

This incident demonstrates the importance of checking the "error behind the error":
- Surface error: "503 Service Unavailable" 
- First error behind: "Application startup failed"
- Second error behind: "Factory pattern initialization failed"  
- **Root error:** "WebSocket manager creation requires valid UserExecutionContext"

The staging outage was caused by architectural migration incompleteness, not infrastructure issues.