# Alembic AsyncPG Greenlet Fix Implementation Plan

## Business Value Justification (BVJ)
- **Segment:** Platform/Internal
- **Business Goal:** Stability - Fix critical migration failures
- **Value Impact:** Enables database migrations critical for feature deployment
- **Strategic Impact:** Unblocks development velocity and production deployments

## Problem Summary
Alembic migrations fail with `sqlalchemy.exc.MissingGreenlet` error because:
1. Database URL is converted to `postgresql+asyncpg://` for async operations
2. Alembic runs in synchronous context
3. AsyncPG driver requires async context or greenlet for sync operations

## Solution Architecture
Separate synchronous migration URLs from asynchronous application URLs.

## Implementation Tasks

### Task 1: Update Alembic env.py
**File:** `app/alembic/env.py`
**Actions:**
1. Add `_ensure_sync_database_url()` function to convert async URLs to sync
2. Update `_get_configuration()` to use sync URL for migrations
3. Test migration execution without greenlet errors

### Task 2: Update Database Configuration
**File:** `app/core/configuration/database.py`
**Actions:**
1. Add `get_sync_database_url()` method to DatabaseConfigProvider
2. Ensure method properly converts asyncpg URLs to sync psycopg2 URLs
3. Handle SSL parameter conversion (ssl -> sslmode)

### Task 3: Test Migration Execution
**Actions:**
1. Run `python -m alembic upgrade head` locally
2. Verify no greenlet errors occur
3. Confirm database schema is updated correctly

### Task 4: Verify Async Operations
**Actions:**
1. Start application with `python scripts/dev_launcher.py`
2. Verify async database operations still work
3. Check health endpoints respond correctly

## Testing Strategy
1. **Unit Tests:** Test URL conversion functions
2. **Integration Tests:** Test migration execution
3. **E2E Tests:** Verify full startup with migrations

## Rollback Plan
If issues occur:
1. Revert env.py changes
2. Install greenlet package as temporary workaround
3. Document issue for future resolution

## Success Criteria
- [ ] Migrations run without greenlet errors
- [ ] Application starts successfully
- [ ] Async database operations work correctly
- [ ] Health checks pass
- [ ] No regression in existing functionality