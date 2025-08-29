# E2E Test Failures Report

## Process Overview
- **Process A**: Continuously running e2e tests and tracking failures
- **Process B**: Spawning sub-agents to fix failures (max 3 concurrent)

## Current Status
- Database test event loop issue: FIXED
- E2E tests: Need comprehensive scan and fixes

## Known Issues

### 1. Database Tests
- **Issue**: Event loop error in test_clickhouse_workload.py
- **Status**: FIXED
- **Fix**: Converted to async autouse fixture

### 2. E2E Test Collection
- **Issue**: Many e2e tests don't have proper test_ prefixes or pytest markers
- **Status**: PENDING
- **Action**: Need to scan and fix all test files

### 3. Test Infrastructure
- **Issue**: Tests timing out when running with real LLM
- **Status**: PENDING
- **Action**: Need to optimize test execution

## Sub-Agent Tasks

### Active Fixes (0/3 slots used)
- None currently active

### Pending Fixes
1. Fix e2e test class naming conventions
2. Add proper pytest markers to all e2e tests
3. Fix test collection issues
4. Optimize test timeout settings
5. Fix real LLM integration for tests

## Next Steps
1. Scan all e2e test files for issues
2. Create fix tasks for each issue type
3. Spawn sub-agents to fix issues in parallel
4. Re-run tests after each fix
5. Continue until all tests pass