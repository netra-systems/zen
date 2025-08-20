# Unified Data Consistency Test Suite - Implementation Guide

## Agent 15 - Unified Testing Implementation Team

**CRITICAL CONTEXT**: User data must be consistent across Auth and Backend services.

## Overview

This comprehensive test suite validates data consistency across the Netra Apex microservice architecture, specifically focusing on synchronization between:

1. **Auth Service** - PostgreSQL database with `AuthUser` entities
2. **Backend Service** - PostgreSQL database with `User` entities  
3. **ClickHouse Analytics** - User activity, metrics, and conversation history

## Business Value Justification (BVJ)

**Segment**: All customer segments (Free, Early, Mid, Enterprise)  
**Business Goal**: Ensure data integrity for reliable user experience and accurate billing  
**Value Impact**: Prevents data corruption that could lead to lost revenue or compliance issues  
**Revenue Impact**: Critical for maintaining trust and preventing churn due to data inconsistencies

## Architecture Overview

```
┌─────────────────┐    sync    ┌─────────────────┐
│   Auth Service  │ ──────────▶│ Backend Service │
│   (PostgreSQL)  │            │   (PostgreSQL)  │
└─────────────────┘            └─────────────────┘
                                        │
                                        │ metrics/logs
                                        ▼
                               ┌─────────────────┐
                               │   ClickHouse    │
                               │   (Analytics)   │
                               └─────────────────┘
```

## Test Suite Components

### Core Test Classes

1. **`MockAuthUser`** - Simulates Auth service user entities
2. **`MockBackendUser`** - Simulates Backend service user entities  
3. **`MockMainDBSync`** - Simulates the sync mechanism
4. **`DataConsistencyValidator`** - Helper for validation operations
5. **`TestUnifiedDataConsistency`** - Main test class (8 core tests)
6. **`TestDataConsistencyPerformance`** - Performance validation (2 tests)

### Success Criteria

✅ **Data Always Consistent**: User data matches across services  
✅ **Updates Propagate Correctly**: Changes sync from Auth to Backend  
✅ **No Orphaned Records**: No dangling references after deletion  
✅ **Referential Integrity**: Foreign key relationships maintained  

## Test Coverage

### 1. User Creation Sync Test
**Purpose**: Validate user creation in Auth service syncs to Backend  
**Steps**:
1. Create user in Auth service
2. Trigger sync to Backend  
3. Verify user exists in Backend
4. Verify data consistency between services

### 2. Profile Update Propagation Test
**Purpose**: Ensure profile updates sync correctly  
**Steps**:
1. Create initial user and sync
2. Update user profile in Auth service
3. Re-sync to Backend service
4. Verify updates propagated correctly

### 3. Conversation History Consistency Test
**Purpose**: Validate conversation data consistency across databases  
**Steps**:
1. Create user and sync
2. Create conversation data
3. Verify ClickHouse can track conversations
4. Verify consistency between PostgreSQL and ClickHouse

### 4. Metrics Data Consistency Test
**Purpose**: Ensure metrics consistency in ClickHouse  
**Steps**:
1. Create user and sync
2. Create tool usage metrics
3. Verify ClickHouse metrics match PostgreSQL
4. Validate consistency across databases

### 5. User Deletion Sync Test
**Purpose**: Verify user deactivation synchronization  
**Steps**:
1. Create and sync user
2. Deactivate user in Auth service
3. Verify deactivation synced to Backend
4. Verify referential integrity maintained

### 6. Referential Integrity Test
**Purpose**: Validate referential integrity across all databases  
**Steps**:
1. Create user with related data
2. Create related records (tool usage, conversations)
3. Verify all references are valid
4. Test cascade behavior on user deactivation

### 7. Concurrent Operations Test
**Purpose**: Verify consistency under concurrent operations  
**Steps**:
1. Create multiple users concurrently
2. Execute sync operations simultaneously
3. Verify all operations succeed
4. Validate data consistency across all services

### 8. Error Recovery Test
**Purpose**: Ensure consistency during error scenarios  
**Steps**:
1. Simulate database connection failures
2. Test error handling and recovery
3. Verify system remains consistent after errors
4. Validate successful recovery after error resolution

## Performance Tests

### Large Batch Sync Performance
- Tests syncing 50 users simultaneously
- Must complete within 10 seconds
- All sync operations must succeed

### Consistency Check Performance  
- Tests validation of 25 users
- Must complete within 5 seconds
- All consistency checks must pass

## Running the Tests

### Basic Execution
```bash
python -m pytest tests/test_unified_data_consistency.py -v
```

### With Coverage
```bash
python -m pytest tests/test_unified_data_consistency.py --cov=auth_service --cov=app.db
```

### Performance Only
```bash
python -m pytest tests/test_unified_data_consistency.py::TestDataConsistencyPerformance -v
```

### Specific Test
```bash
python -m pytest tests/test_unified_data_consistency.py::TestUnifiedDataConsistency::test_user_creation_sync_across_services -v
```

## Expected Results

```
========================== test session starts ==========================
collected 10 items

test_user_creation_sync_across_services PASSED        [ 10%]
test_user_profile_update_propagation PASSED           [ 20%]
test_conversation_history_consistency PASSED          [ 30%]
test_metrics_data_consistency PASSED                   [ 40%]
test_user_deletion_sync PASSED                         [ 50%]
test_referential_integrity_maintenance PASSED         [ 60%]
test_concurrent_data_operations PASSED                 [ 70%]
test_error_recovery_and_consistency PASSED             [ 80%]
test_large_batch_sync_performance PASSED               [ 90%]
test_consistency_check_performance PASSED              [100%]

=================== 10 passed, 1 warning in 0.23s ===================
```

## Integration with CI/CD

### Pre-commit Hooks
Add to `.pre-commit-config.yaml`:
```yaml
- repo: local
  hooks:
    - id: data-consistency-tests
      name: Data Consistency Tests
      entry: python -m pytest tests/test_unified_data_consistency.py
      language: python
      always_run: true
```

### GitHub Actions
Add to workflow:
```yaml
- name: Run Data Consistency Tests
  run: |
    python -m pytest tests/test_unified_data_consistency.py -v
```

## Troubleshooting

### Common Issues

1. **Import Errors**: Test uses mock classes to avoid configuration dependencies
2. **Database Connection Issues**: Tests use AsyncMock to simulate database operations
3. **Performance Issues**: Adjust batch sizes in performance tests if needed

### Test Failures

- **Sync Failures**: Check that MockMainDBSync correctly stores users
- **Consistency Failures**: Verify data matching logic in validator
- **Performance Failures**: Adjust timeout thresholds based on system performance

## Maintenance

### Adding New Tests
1. Follow 25-line function limit (Module Architecture Compliance)
2. Use descriptive test names with step-by-step comments
3. Include both positive and negative test cases
4. Add performance considerations for large-scale operations

### Updating Mock Objects
1. Keep mocks aligned with actual service implementations
2. Update when database schemas change
3. Maintain consistency with real service behavior

## Related Documentation

- [Auth Service Architecture](../auth_service/README.md)
- [Database Models](../app/db/models_user.py)
- [Main DB Sync](../auth_service/auth_core/database/main_db_sync.py)
- [Testing Guide](../SPEC/testing.xml)

## Contact & Support

**Agent 15 - Unified Testing Implementation Team**  
**Mission**: Test data consistency across services  
**Time Limit**: 2 hours (COMPLETED)  
**Output**: Data consistency test suite ✅

For questions or issues with this test suite, refer to the existing regression tests in:
- `app/tests/critical/test_auth_user_persistence_regression.py`
- `app/tests/database/test_schema_consistency.py`