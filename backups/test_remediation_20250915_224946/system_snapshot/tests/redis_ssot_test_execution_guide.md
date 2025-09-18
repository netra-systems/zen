# Redis SSOT Test Execution Guide - GitHub Issue #190

## Overview
This guide provides execution commands for the 3 new critical Redis SSOT tests created for GitHub Issue #190 consolidation validation.

## Test Files Created

### 1. Redis Manager Consolidation Unit Test
**File:** `/tests/unit/redis_ssot/test_redis_manager_consolidation_unit.py`
**Purpose:** Validates 4→1 Redis manager consolidation works correctly
**Critical Functions:**
- Validates single Redis manager handles all operations (connection, caching, health checks)
- Tests connection pool sharing across components
- Verifies configuration consistency maintained
- Confirms memory usage reduced vs multiple managers
- Validates all Redis operations (get/set/delete/ping) work through single manager

### 2. Import Migration Validation Integration Test  
**File:** `/tests/integration/redis_ssot/test_redis_import_migration_integration.py`
**Purpose:** Validates all 76 files importing Redis managers use single SSOT
**Critical Functions:**
- Scans all Python files for Redis manager imports
- Validates imports point to primary SSOT (netra_backend.app.redis_manager)
- Detects violations (imports to db/redis_manager, cache/redis_cache_manager, etc.)
- Ensures no duplicate Redis manager instantiations
- **This test will FAIL until consolidation is complete**

### 3. WebSocket-Redis SSOT Integration Test
**File:** `/tests/integration/redis_ssot/test_websocket_redis_ssot_integration.py`  
**Purpose:** Critical for Golden Path - prevents 1011 WebSocket errors
**Critical Functions:**
- Tests agent state persistence using single Redis manager
- Validates WebSocket events use SSOT Redis operations
- Tests connection stability during WebSocket handshake
- Verifies no race conditions between WebSocket and Redis connections
- Tests user session isolation with single Redis manager

## Test Execution Commands

### Using Unified Test Runner (Recommended)

#### Run All Redis SSOT Tests
```bash
python tests/unified_test_runner.py --pattern "*redis_ssot*"
```

#### Run Unit Tests Only
```bash
python tests/unified_test_runner.py --category unit --pattern "*redis_ssot*"
```

#### Run Integration Tests Only
```bash
python tests/unified_test_runner.py --category integration --pattern "*redis_ssot*"
```

#### Run with Real Redis Services
```bash
python tests/unified_test_runner.py --real-services --pattern "*redis_ssot*"
```

#### Run Mission Critical Redis Tests (including existing)
```bash
python tests/unified_test_runner.py --category mission_critical --pattern "*redis*"
```

### Direct PyTest Execution (Alternative)

#### Individual Test Files
```bash
# Unit test
python -m pytest tests/unit/redis_ssot/test_redis_manager_consolidation_unit.py -v

# Import migration test  
python -m pytest tests/integration/redis_ssot/test_redis_import_migration_integration.py -v

# WebSocket integration test
python -m pytest tests/integration/redis_ssot/test_websocket_redis_ssot_integration.py -v
```

#### All Redis SSOT Tests
```bash
python -m pytest tests/unit/redis_ssot/ tests/integration/redis_ssot/ -v
```

### Test with Coverage
```bash
python tests/unified_test_runner.py --coverage --pattern "*redis_ssot*"
```

## Expected Test Behavior

### Current State (Expected FAILURES until consolidation complete)

1. **Redis Manager Consolidation Unit Test:**
   - ❌ FAILS: `test_duplicate_managers_still_exist()` - Will pass after consolidation
   - ✅ PASSES: `test_single_redis_manager_exists()` - Primary SSOT exists
   - ✅ PASSES: Connection pool and configuration tests

2. **Import Migration Integration Test:**
   - ❌ FAILS: `test_no_violation_imports_exist()` - 76 files need migration
   - ❌ FAILS: `test_all_files_use_ssot_imports()` - Low SSOT adoption rate
   - ✅ PASSES: Import scanning and analysis functions

3. **WebSocket-Redis SSOT Integration Test:**
   - ✅ PASSES: Most tests (if SSOT Redis manager is functional)
   - ⚠️ MAY FAIL: Connection stability if Redis configuration issues exist
   - ✅ PASSES: User isolation and memory leak prevention tests

### Post-Consolidation State (Expected SUCCESS)

After GitHub Issue #190 consolidation is complete:
- ✅ ALL tests should PASS
- ✅ No duplicate Redis managers detected
- ✅ All imports use SSOT pattern
- ✅ WebSocket stability validated
- ✅ User isolation maintained
- ✅ Memory leaks prevented

## Integration with Existing Test Suite

### Mission Critical Test Integration
These tests integrate with existing mission critical Redis tests:
```bash
python tests/mission_critical/test_redis_validation_ssot_critical.py
```

### Test Categories
- **Unit:** `tests/unit/redis_ssot/`
- **Integration:** `tests/integration/redis_ssot/`
- **Mission Critical:** Integrated with existing critical Redis tests

### Continuous Integration
Add to CI pipeline:
```yaml
- name: Redis SSOT Validation Tests
  run: python tests/unified_test_runner.py --pattern "*redis_ssot*" --real-services
```

## Business Value Validation

Each test validates specific business value:

1. **Consolidation Test:** Reduces memory usage and connection chaos
2. **Import Migration Test:** Eliminates 76-file import inconsistency
3. **WebSocket Integration Test:** Protects $500K+ ARR Golden Path user flow

## Troubleshooting

### Common Issues

1. **Redis Not Available:**
   ```
   Error: Redis libraries not available - Redis fixtures will fail
   ```
   **Solution:** Set `USE_REAL_SERVICES=true` or install redis libraries

2. **Import Errors:**
   ```
   Error: Cannot import SSOT RedisManager
   ```
   **Solution:** Ensure primary SSOT Redis manager exists and is importable

3. **Connection Failures:**
   ```
   Error: Redis connection unstable
   ```
   **Solution:** Check Redis service is running and accessible

### Debug Mode
Run with verbose output:
```bash
python tests/unified_test_runner.py --pattern "*redis_ssot*" --verbose
```

## Documentation References

- **Primary SSOT:** `/netra_backend/app/redis_manager.py`
- **GitHub Issue:** [#190 - Redis Manager Consolidation](https://github.com/issue/190)
- **Golden Path:** `docs/GOLDEN_PATH_USER_FLOW_COMPLETE.md`
- **SSOT Base Test:** `test_framework/ssot/base_test_case.py`

## Success Criteria

✅ **Test Creation Complete**
- 3 new Redis SSOT tests created
- Tests follow SSOT framework patterns
- Business value clearly documented
- Integration with unified test runner verified

🎯 **Consolidation Success Metrics**
- All Redis SSOT tests pass
- 0 duplicate Redis managers detected  
- 100% SSOT import adoption rate
- WebSocket 1011 errors eliminated
- Memory usage optimized vs multiple managers

---

**Created:** 2025-09-10
**GitHub Issue:** #190  
**Business Impact:** Protects $500K+ ARR Golden Path user flow
**Test Strategy:** 20% of Redis SSOT test validation coverage