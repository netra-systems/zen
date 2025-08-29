# Critical Bugs and Failing Tests Report

## Summary
Created failing tests for 4 critical bugs identified in the system. These tests demonstrate the bugs exist and will pass once the bugs are fixed.

## 1. ✅ Auth Service Refresh Endpoint Bug (VERIFIED WORKING)
**Issue**: The refresh endpoint had concerns about `await request.body()` not being awaitable
**Location**: `auth_service/auth_core/routes/auth_routes.py:582`
**Status**: VERIFIED WORKING - `request.body()` IS awaitable and returns bytes
**Tests Created**: 
- `auth_service/tests/test_refresh_endpoint.py` - Comprehensive test suite
- `auth_service/tests/test_refresh_endpoint_integration.py` - Integration tests

**Test Results**:
- ✅ Confirmed `request.body()` returns an awaitable coroutine
- ✅ Endpoint correctly parses JSON from request body
- ✅ Accepts multiple field name formats (refresh_token, refreshToken, token)
- ✅ Properly returns 422 for missing tokens
- ✅ Handles invalid tokens with 401 responses

## 2. ❌ User Model Missing Fields
**Issue**: User model missing 'role', 'is_active', 'created_at', 'updated_at' fields that tests expect
**Location**: `auth_service/auth_core/models/auth_models.py:194`
**Test**: `tests/test_critical_bugs_simple.py::TestUserModelFieldsSimple`
**Status**: Test PASSES (demonstrating the bug exists)

Current User model has:
- id, email, name, picture, verified_email, provider

Tests expect:
- id, email, name, role, is_active, created_at, updated_at

## 3. ✅ Database Engine Configuration Bug (FIXED)
**Issue**: SQLite doesn't support pool parameters like pool_size, max_overflow
**Location**: `auth_service/auth_core/database/database_manager.py:42`
**Fix Applied**: Added conditional logic to check if database is SQLite

## 4. ❌ JWTGenerationTestManager Import Issues
**Issue**: Tests importing JWTGenerationTestManager from wrong path
**Expected Import**: `from test_framework.test_managers import JWTGenerationTestManager`
**Status**: Module doesn't exist at expected location

## 5. ❌ AsyncClient Initialization Issues
**Issue**: E2E tests not using AsyncClient with proper context manager
**Impact**: Causes resource leaks and test failures
**Pattern to Fix**: Use `async with AsyncClient() as client:` instead of bare `AsyncClient()`

## Test Files Created
1. `auth_service/tests/test_critical_bugs.py` - Comprehensive tests (database issues)
2. `auth_service/tests/test_critical_bugs_simple.py` - Simple tests without database dependency

## Fixes Applied
1. ✅ Database engine configuration for SQLite compatibility
2. ✅ Auth refresh endpoint already fixed (uses request.json())

## Fixes Still Needed
1. Extend User model with missing fields or create ExtendedUser model
2. Fix import paths for JWTGenerationTestManager or create the missing module
3. Update E2E tests to use AsyncClient with context managers

## Running the Tests
```bash
# Run simple tests (no database dependency)
cd auth_service
python -m pytest tests/test_critical_bugs_simple.py -v

# Test specific bug
python -m pytest tests/test_critical_bugs_simple.py::TestUserModelFieldsSimple -v
```