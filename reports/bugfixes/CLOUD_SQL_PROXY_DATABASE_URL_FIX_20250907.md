# Cloud SQL Proxy Database URL Fix Report

**Date:** 2025-09-07  
**Issue:** Cloud SQL proxy connections failing due to incorrect DATABASE_URL construction  
**Status:** FIXED  
**Severity:** CRITICAL  

## Executive Summary

Fixed a critical issue where the GCP deployment script was incorrectly constructing DATABASE_URL for Cloud SQL proxy connections, violating the SSOT principle. The backend and auth services should use `DatabaseURLBuilder` to construct URLs from POSTGRES_* environment variables, not receive a pre-built DATABASE_URL.

## Root Cause Analysis (Five Whys)

### Why 1: Why were Cloud SQL proxy connections failing?
The deployment script was constructing DATABASE_URL incorrectly for Cloud SQL Unix socket connections.

### Why 2: Why was the deployment script constructing DATABASE_URL?
Historical code in `deploy_to_gcp.py` was manually building DATABASE_URL from POSTGRES_* variables instead of letting the services use DatabaseURLBuilder.

### Why 3: Why was this a problem?
The deployment script's URL construction logic was duplicated and not synchronized with the SSOT DatabaseURLBuilder, leading to format mismatches.

### Why 4: Why did this duplication exist?
Earlier implementations required DATABASE_URL as an environment variable, but after implementing DatabaseURLBuilder as SSOT, the deployment script wasn't updated.

### Why 5: Why wasn't the deployment script updated when DatabaseURLBuilder became SSOT?
Lack of cross-component validation and missing regression tests for Cloud SQL proxy connections during the SSOT migration.

## Technical Details

### The Problem

1. **Deployment Script (BEFORE FIX):**
   - Lines 924-941: Manually constructed DATABASE_URL
   - Lines 972-980: Added DATABASE_URL to environment variables
   - Format used: `postgresql+asyncpg://user:pass@/db?host=/cloudsql/...`

2. **DatabaseURLBuilder (SSOT):**
   - Correctly handles Cloud SQL Unix socket connections
   - Located in: `shared/database_url_builder.py`
   - Used by: `netra_backend/app/core/backend_environment.py` and `auth_service/auth_core/auth_environment.py`

### The Solution

Removed DATABASE_URL construction from the deployment script entirely. Services now:
1. Receive individual POSTGRES_* environment variables from GCP Secret Manager
2. Use DatabaseURLBuilder to construct the correct URL format
3. Ensure Cloud SQL proxy connections work correctly

### Files Modified

1. **scripts/deploy_to_gcp.py**
   - Line 924-933: Removed DATABASE_URL construction, added documentation
   - Line 972-978: Removed DATABASE_URL addition to environment variables

## Verification Checklist

- [x] Deployment script no longer constructs DATABASE_URL
- [x] Backend uses DatabaseURLBuilder via backend_environment.py
- [x] Auth service uses DatabaseURLBuilder via auth_environment.py
- [x] Cloud SQL proxy format handled correctly in DatabaseURLBuilder
- [x] Documentation added to prevent regression

## Prevention Measures

1. **SSOT Compliance:** DatabaseURLBuilder is the SINGLE SOURCE OF TRUTH for database URL construction
2. **No Manual URL Construction:** Never construct database URLs manually outside DatabaseURLBuilder
3. **Environment Variables:** Services receive POSTGRES_* variables, not DATABASE_URL
4. **Cloud SQL Support:** DatabaseURLBuilder correctly detects and formats Cloud SQL Unix socket connections

## Testing Requirements

Regression test suite should verify:
1. Cloud SQL proxy connections work with POSTGRES_HOST="/cloudsql/..."
2. DatabaseURLBuilder correctly constructs URLs for all environments
3. Deployment script provides correct environment variables
4. No DATABASE_URL is set by deployment script

## Related Documentation

- **SSOT Database URL Builder:** `shared/database_url_builder.py`
- **Backend Environment:** `netra_backend/app/core/backend_environment.py`
- **Auth Environment:** `auth_service/auth_core/auth_environment.py`
- **Historical Fix:** Commit 1365ff67c (2025-09-04) - "restore DatabaseURLBuilder integration for staging database connection"

## Key Learnings

1. **SSOT Violations Are Critical:** When establishing an SSOT pattern, ALL components must be updated
2. **Deployment Scripts Need Validation:** Deployment configuration must be validated against service expectations
3. **Cloud SQL Requires Special Handling:** Unix socket connections have different URL formats than TCP connections
4. **Regression Tests Are Essential:** Every critical fix needs regression tests to prevent reoccurrence

## Impact

This fix ensures:
- Cloud SQL proxy connections work correctly in staging/production
- Database URL construction follows SSOT principles
- No duplicate/conflicting URL construction logic
- Easier debugging and maintenance of database connections