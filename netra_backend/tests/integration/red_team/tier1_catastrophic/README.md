# Red Team Tier 1 Catastrophic Tests

## Overview

These tests are **DESIGNED TO FAIL INITIALLY**. They are "Red Team" tests that expose real integration issues by testing core functionality that should work but likely doesn't yet.

## Critical Requirements

- **NO MOCKS**: All tests use real services, real databases, real connections
- **REAL FAILURE TESTING**: Tests are designed to expose actual system gaps
- **L3 Testing Level**: Real System Under Test (SUT) with real dependencies
- **EXPECTED INITIAL RESULT**: FAILURE (this proves they're testing real issues)

## Test Files

### 1. Cross-Service Auth Token Validation
**File**: `test_cross_service_auth_token_validation.py`

Tests that tokens from the auth service are properly validated by the backend service.

**Expected Failures**:
- Auth service may not be running
- JWT secrets may not be synchronized between services
- Token validation middleware may not be implemented
- Expired/malformed token handling may be missing
- User context propagation may not work

### 2. User Session Persistence Across Service Restarts
**File**: `test_user_session_persistence_restart.py`

Tests that user sessions survive service restarts through Redis persistence.

**Expected Failures**:
- Session storage in Redis may not be implemented
- Session validation logic may not exist
- Service restart may not preserve sessions
- Activity tracking may be missing
- Session security validation may be incomplete

### 3. OAuth Flow Database State Consistency
**File**: `test_oauth_database_consistency.py`

Tests that OAuth callbacks create user records consistently across both auth DB and main DB.

**Expected Failures**:
- Dual database user creation may not be implemented
- Partial failure rollback may not work
- Concurrent OAuth handling may have race conditions
- Transaction isolation may not be implemented
- Data validation may not be synchronized

### 4. PostgreSQL Connection Pool Exhaustion
**File**: `test_postgresql_connection_pool_exhaustion.py`

Tests that connection pool exhaustion is properly handled and that the system can recover.

**Expected Failures**:
- Pool exhaustion handling may not be implemented
- Connection timeout logic may not work
- Pool recovery after exhaustion may fail
- Connection leak detection may be missing
- Health monitoring may not be available

### 5. Cross-Database Transaction Consistency
**File**: `test_cross_database_transaction_consistency.py`

Tests that operations across PostgreSQL and ClickHouse maintain ACID properties.

**Expected Failures**:
- Distributed transaction coordination may not exist
- Rollback across databases may not work
- Data type consistency may not be enforced
- Foreign key coordination may be missing
- Deadlock detection across databases may not work

## Running the Tests

```bash
# Run all Red Team Tier 1 tests (expect failures)
python -m pytest netra_backend/tests/integration/red_team/tier1_catastrophic/ -v

# Run individual test files
python -m pytest netra_backend/tests/integration/red_team/tier1_catastrophic/test_cross_service_auth_token_validation.py -v
python -m pytest netra_backend/tests/integration/red_team/tier1_catastrophic/test_user_session_persistence_restart.py -v
python -m pytest netra_backend/tests/integration/red_team/tier1_catastrophic/test_oauth_database_consistency.py -v
python -m pytest netra_backend/tests/integration/red_team/tier1_catastrophic/test_postgresql_connection_pool_exhaustion.py -v
python -m pytest netra_backend/tests/integration/red_team/tier1_catastrophic/test_cross_database_transaction_consistency.py -v

# Run with full output to see failure details
python -m pytest netra_backend/tests/integration/red_team/tier1_catastrophic/ -v -s
```

## Prerequisites

### Required Services
- PostgreSQL database (running and accessible)
- Redis server (running and accessible)  
- Auth service (running on localhost:8001 or configured URL)
- Backend service (the main application)
- ClickHouse (for cross-database transaction tests)

### Required Configuration
- `DATABASE_URL` - PostgreSQL connection string
- `REDIS_URL` - Redis connection string
- `JWT_SECRET_KEY` - Must be consistent between auth service and backend
- `AUTH_SERVICE_URL` - URL to auth service (default: http://localhost:8001)
- `CLICKHOUSE_ENABLED` - Set to true for ClickHouse tests

### Environment Setup
```bash
# Set test environment
export TESTING=1
export ENVIRONMENT=testing
export LOG_LEVEL=ERROR

# Database connections
export DATABASE_URL="postgresql://test:test@localhost:5432/netra_test"
export REDIS_URL="redis://localhost:6379/1"

# Auth service configuration  
export JWT_SECRET_KEY="test-jwt-secret-key-for-testing-only-must-be-32-chars"
export AUTH_SERVICE_URL="http://localhost:8001"

# ClickHouse (optional)
export CLICKHOUSE_ENABLED=true
export CLICKHOUSE_URL="clickhouse://localhost:8123/test"
```

## Understanding Test Results

### Expected Outcome: FAILURE
These tests are **supposed to fail initially**. Each failure exposes a real gap in the system:

- **FAIL**: Proves the test is validating real functionality that doesn't exist yet
- **SKIP**: Service or database not available (need to fix environment)
- **ERROR**: Test infrastructure issue (need to fix test setup)
- **PASS**: Either the functionality actually works, or the test needs to be made more strict

### Common Failure Patterns
1. **Service Not Running**: Auth service, Redis, or database not available
2. **Configuration Mismatch**: JWT secrets, database URLs, or service URLs incorrect
3. **Missing Implementation**: The feature being tested doesn't exist yet
4. **Partial Implementation**: Feature exists but doesn't handle edge cases
5. **Integration Gaps**: Services work individually but not together

## Business Value

Each test validates critical functionality that directly impacts:

- **Platform Stability**: System doesn't crash under normal load
- **User Trust**: Authentication and sessions work reliably
- **Data Integrity**: User data is consistent across databases
- **Service Availability**: System handles resource exhaustion gracefully
- **Regulatory Compliance**: Data transactions maintain ACID properties

## Next Steps After Failures

1. **Analyze Failures**: Understand which specific functionality is missing
2. **Prioritize Fixes**: Focus on the most critical gaps first
3. **Implement Missing Features**: Build the functionality the tests expect
4. **Re-run Tests**: Verify fixes work by seeing tests pass
5. **Add Monitoring**: Implement monitoring for the tested scenarios

## Test Philosophy

> "If it doesn't fail, it's not testing anything real"

These Red Team tests intentionally push the system beyond its current capabilities to expose gaps before they become production issues. The goal is not to pass all tests immediately, but to systematically identify and fix critical system gaps.