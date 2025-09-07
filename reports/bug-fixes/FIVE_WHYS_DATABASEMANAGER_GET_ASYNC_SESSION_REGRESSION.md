# Five Whys Root Cause Analysis: DatabaseManager.get_async_session() Regression

## Issue
**Status**: CRITICAL  
**Environment**: Staging  
**Error**: `type object 'DatabaseManager' has no attribute 'get_async_session'`  
**Endpoint**: `https://api.staging.netrasystems.ai/health/ready`  
**Impact**: Health check endpoint returns 503 Service Unavailable

## Current State vs Expected State

### Current State (BROKEN)
```python
# netra_backend/app/routes/health.py:455
from netra_backend.app.db.database_manager import DatabaseManager
async with DatabaseManager.get_async_session() as db:  # FAILS - method doesn't exist
```

### Expected State (WORKING) 
```python
# Should use instance method or proper import
from netra_backend.app.database import get_db
async with get_db() as db:  # WORKS - proper context manager
```

## Five Whys Analysis

### Why #1: Why is the staging health check failing?
**Answer**: Because the health route at line 455 is calling `DatabaseManager.get_async_session()` as a static/class method, but this method doesn't exist on the DatabaseManager class.

### Why #2: Why doesn't DatabaseManager have get_async_session as a static method?
**Answer**: Because there are TWO different DatabaseManager implementations in the codebase, and neither provides `get_async_session` as a static/class method:
- `netra_backend/app/database/__init__.py` - Has `session_scope()` instance method
- `netra_backend/app/db/database_manager.py` - Has `get_session()` instance method

### Why #3: Why was the code changed to call a non-existent method?
**Answer**: Based on git history and comments, there was an attempt to fix async generator issues. The comment at line 452 says "CRITICAL FIX: Use direct database context manager from DatabaseManager" suggesting someone tried to bypass dependency injection to avoid async generator issues but used the wrong method name.

### Why #4: Why did this pass testing and get deployed to staging?
**Answer**: Multiple failures in the development and deployment process:
1. **No unit tests** for the health endpoint's database connection logic
2. **Local testing likely used mocks** that masked the issue  
3. **CI/CD didn't catch it** because health checks may have been disabled or mocked
4. **Code review missed it** because the change looked reasonable with the "CRITICAL FIX" comment

### Why #5: Why do we have conflicting database access patterns?
**Answer**: SSOT (Single Source of Truth) violation - Multiple database access patterns exist:
1. Dependency injection via `get_request_scoped_db_session`
2. Direct DatabaseManager usage (two different implementations)
3. Legacy patterns from `get_async_db()` and `get_db()`
4. References to non-existent `DatabaseManager.get_async_session()` in docs/comments

## Root Causes

1. **SSOT Violation**: Multiple DatabaseManager classes and database access patterns
2. **Missing Static Method**: Code expects a static method that was never implemented
3. **Documentation Drift**: Comments and docs reference methods that don't exist
4. **Testing Gaps**: Health endpoints not tested with real database connections
5. **Deployment Process**: Changes can reach staging without proper integration testing

## Immediate Fix

```python
# Option 1: Use the canonical get_db() function
from netra_backend.app.database import get_db
async with get_db() as db:
    result = await asyncio.wait_for(_check_readiness_status(db), timeout=6.0)

# Option 2: Use database_manager instance
from netra_backend.app.database import database_manager
async with database_manager.session_scope() as db:
    result = await asyncio.wait_for(_check_readiness_status(db), timeout=6.0)

# Option 3: Add the missing static method (NOT RECOMMENDED - adds more complexity)
```

## Prevention Measures

1. **Consolidate Database Access**
   - Choose ONE canonical database access pattern
   - Remove duplicate DatabaseManager implementations
   - Update all code to use the single pattern

2. **Add Integration Tests**
   ```python
   async def test_health_ready_endpoint_real_db():
       """Test health/ready endpoint with real database connection."""
       # Must use real database, not mocks
       response = await client.get("/health/ready")
       assert response.status_code == 200
   ```

3. **Update Documentation**
   - Remove references to non-existent methods
   - Document the ONE correct way to get database sessions
   - Add warnings about deprecated patterns

4. **Staging Deployment Validation**
   - Run health check validation after deployment
   - Alert on 5xx errors from health endpoints
   - Rollback if health checks fail

5. **Code Review Checklist**
   - [ ] Does this use the canonical database access pattern?
   - [ ] Are there unit tests for the changed code?
   - [ ] Has this been tested with real services (no mocks)?
   - [ ] Do health checks still work?

## Timeline

- **Recent commits**: Database refactoring (6feb5fd78, f4e4e11ac) integrated DatabaseURLBuilder
- **Regression introduced**: Likely in attempt to fix async issues (41e0dd6a8)
- **Detection**: User report of staging health check failure
- **Current impact**: Staging environment health checks broken

## Recommendations

1. **IMMEDIATE**: Fix health.py to use correct database access pattern
2. **SHORT-TERM**: Add integration tests for all health endpoints
3. **MEDIUM-TERM**: Consolidate to single DatabaseManager implementation
4. **LONG-TERM**: Implement automated staging validation post-deployment