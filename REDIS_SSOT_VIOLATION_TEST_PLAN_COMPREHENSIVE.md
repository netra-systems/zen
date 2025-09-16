# Redis SSOT Violation Remediation Test Plan
**Issue:** Redis SSOT violations causing WebSocket 1011 errors blocking Golden Path
**Business Impact:** $500K+ ARR chat functionality at risk
**Current State:** 102 violations, 85% WebSocket error probability, 0% staging success rate

## Test Plan Overview

This plan proves the correlation between Redis SSOT violations and WebSocket failures, then validates the remediation approach. Tests are designed to **FAIL INITIALLY** to prove the problem exists.

### Current Evidence
- **Redis Violations:** 102 total (55 deprecated imports + 47 direct instantiations)
- **Competing Managers:** 12 different Redis implementations
- **WebSocket Success Rate:** 0% in staging (from latest test report)
- **Backend Status:** DOWN (503/500 errors)
- **Auth Status:** DOWN (503 errors, timeouts)

## Phase 1: Baseline Violation Detection Tests 🔍

**Objective:** Confirm current violation count and document specific locations

### Test 1.1: Redis Violation Scanner Baseline
```bash
# Run existing violation scanner
cd /c/netra-apex
python netra_backend/scripts/scan_redis_violations.py --detailed

# Expected Result: FAIL with ~102 violations
# Success Criteria: Reports 102 violations with specific file locations
```

### Test 1.2: Mission Critical Violation Detection
```bash
# Run mission critical violation tests
python tests/unified_test_runner.py \
  --category mission_critical \
  --test-pattern "*redis*violation*" \
  --no-fast-fail

# Expected Result: FAIL - detects violations
# Success Criteria: Tests fail showing specific violations by type
```

### Test 1.3: Violation Classification Analysis
```bash
# Get JSON output for analysis
python netra_backend/scripts/scan_redis_violations.py --json > redis_violations_baseline.json

# Validate violation types
python -c "
import json
with open('redis_violations_baseline.json') as f:
    data = json.load(f)
print(f'Total: {data[\"total_violations\"]}')
print('By type:', {v['violation_type']: len([vv for vv in data['violations'] if vv['violation_type'] == v['violation_type']]) for v in data['violations']})
"

# Expected Result: Shows breakdown of violation types
# Success Criteria: Confirms 43+ direct instantiation violations
```

**Files to Examine:**
- `/netra_backend/scripts/scan_redis_violations.py` (scanner)
- `/netra_backend/tests/mission_critical/test_redis_import_violations.py` (tests)
- Output: `redis_violations_baseline.json`

## Phase 2: WebSocket Connection Correlation Tests 🔌

**Objective:** Prove Redis violations correlate with WebSocket 1011 errors

### Test 2.1: WebSocket Connection Stability Test (NO DOCKER)
```bash
# Test WebSocket connectivity without Docker dependency
python tests/unified_test_runner.py \
  --category integration \
  --test-pattern "*websocket*connection*" \
  --no-docker \
  --real-services

# Expected Result: FAIL with 1011 errors
# Success Criteria: Demonstrates 0% success rate matches our analysis
```

### Test 2.2: Redis Connection Pool Fragmentation Test
```bash
# Test Redis connection handling
python tests/unified_test_runner.py \
  --category unit \
  --test-pattern "*redis*connection*" \
  --no-fast-fail

# Expected Result: FAIL showing multiple connection pools
# Success Criteria: Detects 12+ competing Redis managers
```

### Test 2.3: WebSocket 1011 Error Pattern Analysis
```bash
# Run specific 1011 error tests
python netra_backend/tests/unit/websocket_core/test_websocket_1011_error_prevention.py -v

# Expected Result: FAIL demonstrating 1011 error patterns
# Success Criteria: Shows correlation with Redis initialization
```

### Test 2.4: Agent Execution Reliability Test
```bash
# Test agent execution through WebSocket (core Golden Path)
python tests/unified_test_runner.py \
  --category integration \
  --test-pattern "*agent*execution*" \
  --real-services \
  --no-docker

# Expected Result: FAIL due to WebSocket unreliability
# Success Criteria: Shows 70% failure rate correlates with Redis issues
```

**Files to Test:**
- `/tests/validation/test_issue_849_websocket_1011_fix.py`
- `/netra_backend/tests/unit/websocket_core/test_websocket_1011_error_prevention.py`
- WebSocket integration tests

## Phase 3: SSOT Factory Pattern Validation Tests ✅

**Objective:** Test the remedy - Redis factory singleton behavior

### Test 3.1: Redis Singleton Factory Test
```bash
# Test SSOT Redis manager singleton behavior
python -c "
from netra_backend.app.redis_manager import redis_manager
import id
manager1 = redis_manager
manager2 = redis_manager
print(f'Same instance: {id(manager1) == id(manager2)}')
print(f'Manager type: {type(manager1)}')
"

# Expected Result: PASS when SSOT is implemented
# Success Criteria: Same instance ID confirms singleton pattern
```

### Test 3.2: User Context Isolation Test
```bash
# Test proper user context isolation with Redis
python tests/unified_test_runner.py \
  --category unit \
  --test-pattern "*user*isolation*redis*" \
  --no-fast-fail

# Expected Result: FAIL initially (shows isolation issues)
# Success Criteria: After fix, confirms isolated user contexts
```

### Test 3.3: Connection Pool Stability Test
```bash
# Test Redis connection pool under load
python tests/mission_critical/test_redis_ssot_consolidation.py::RedisSSOTConsolidationTests::test_single_connection_pool_validation -v

# Expected Result: FAIL initially (multiple pools)
# Success Criteria: After fix, shows single stable pool
```

**Files to Validate:**
- `/netra_backend/app/redis_manager.py` (SSOT implementation)
- `/tests/mission_critical/test_redis_ssot_consolidation.py`

## Phase 4: Integration Stability Tests 🔄

**Objective:** System stability and Golden Path restoration

### Test 4.1: Service Startup Integration Test
```bash
# Test service startup without Redis conflicts
python tests/unified_test_runner.py \
  --category integration \
  --test-pattern "*service*startup*" \
  --real-services \
  --no-docker

# Expected Result: FAIL initially (startup conflicts)
# Success Criteria: Clean startup sequence after SSOT fix
```

### Test 4.2: Cross-Service Redis Integration Test
```bash
# Test Redis SSOT across services (Auth, Backend, etc.)
python tests/integration/redis_ssot/test_redis_import_migration_integration.py -v

# Expected Result: FAIL initially (conflicting Redis usage)
# Success Criteria: Unified Redis usage across services
```

### Test 4.3: Golden Path End-to-End Test (NO DOCKER)
```bash
# Test complete Golden Path without Docker
python tests/unified_test_runner.py \
  --category e2e \
  --test-pattern "*golden*path*" \
  --no-docker \
  --real-services

# Expected Result: FAIL initially (WebSocket reliability issues)
# Success Criteria: 95%+ success rate after Redis SSOT fix
```

### Test 4.4: Memory Usage Optimization Test
```bash
# Test memory usage with consolidated Redis
python tests/mission_critical/test_redis_ssot_consolidation.py::RedisSSOTConsolidationTests::test_memory_optimization -v

# Expected Result: Shows 75% memory reduction after consolidation
# Success Criteria: Confirms resource optimization
```

## Test Execution Order and Commands

### Pre-Execution Setup
```bash
# Ensure in correct environment
cd /c/netra-apex
export ENVIRONMENT=staging
export NO_DOCKER=true

# Verify test infrastructure
python tests/unified_test_runner.py --check-infrastructure
```

### Execute in Order (ALL EXPECTED TO FAIL INITIALLY)

#### Step 1: Baseline Evidence Collection
```bash
# 1.1 - Get violation count
python netra_backend/scripts/scan_redis_violations.py --detailed | tee redis_violation_baseline.txt

# 1.2 - Mission critical violation detection
python tests/unified_test_runner.py --category mission_critical --test-pattern "*redis*violation*" --no-fast-fail

# 1.3 - Get structured violation data
python netra_backend/scripts/scan_redis_violations.py --json > redis_violations_baseline.json
```

#### Step 2: WebSocket Correlation Proof
```bash
# 2.1 - WebSocket connection test (should show 0% success)
python tests/unified_test_runner.py --category integration --test-pattern "*websocket*connection*" --no-docker --real-services

# 2.2 - Redis connection fragmentation test
python tests/unified_test_runner.py --category unit --test-pattern "*redis*connection*" --no-fast-fail

# 2.3 - 1011 error pattern analysis
python netra_backend/tests/unit/websocket_core/test_websocket_1011_error_prevention.py -v

# 2.4 - Agent execution reliability test
python tests/unified_test_runner.py --category integration --test-pattern "*agent*execution*" --real-services --no-docker
```

#### Step 3: SSOT Validation Preparation
```bash
# 3.1 - Current singleton test (should show multiple instances)
python -c "from netra_backend.app.redis_manager import redis_manager; print(f'Manager: {redis_manager}')"

# 3.2 - User isolation test
python tests/unified_test_runner.py --category unit --test-pattern "*user*isolation*redis*" --no-fast-fail

# 3.3 - Connection pool test
python tests/mission_critical/test_redis_ssot_consolidation.py::RedisSSOTConsolidationTests::test_single_connection_pool_validation -v
```

#### Step 4: Integration Testing
```bash
# 4.1 - Service startup test
python tests/unified_test_runner.py --category integration --test-pattern "*service*startup*" --real-services --no-docker

# 4.2 - Cross-service Redis test
python tests/integration/redis_ssot/test_redis_import_migration_integration.py -v

# 4.3 - Golden Path test
python tests/unified_test_runner.py --category e2e --test-pattern "*golden*path*" --no-docker --real-services

# 4.4 - Memory optimization test
python tests/mission_critical/test_redis_ssot_consolidation.py::RedisSSOTConsolidationTests::test_memory_optimization -v
```

## Expected Failure Patterns (Pre-Remediation)

### Phase 1 Expected Failures
- **Violation Scanner:** Reports 102 violations
- **Mission Critical Tests:** FAIL with violation count
- **JSON Analysis:** Shows 43+ direct instantiation violations

### Phase 2 Expected Failures
- **WebSocket Tests:** 0% success rate, 1011 errors
- **Redis Connection Tests:** Multiple competing pools detected
- **Agent Tests:** 70% failure rate due to connection issues

### Phase 3 Expected Failures
- **Singleton Test:** Multiple Redis instances created
- **User Isolation:** Shared state between users
- **Connection Pool:** Fragmented pools across services

### Phase 4 Expected Failures
- **Service Startup:** Redis initialization conflicts
- **Cross-Service:** Inconsistent Redis usage
- **Golden Path:** WebSocket reliability failures
- **Memory Usage:** High resource consumption

## Success Criteria (Post-Remediation)

### Phase 1 Success
- **Violation Scanner:** 0 violations reported
- **Mission Critical Tests:** PASS - no violations detected
- **JSON Analysis:** Clean compliance report

### Phase 2 Success
- **WebSocket Tests:** 95%+ success rate
- **Redis Connection Tests:** Single connection pool
- **Agent Tests:** 95%+ reliability

### Phase 3 Success
- **Singleton Test:** Same instance ID every time
- **User Isolation:** Proper context separation
- **Connection Pool:** Single stable pool

### Phase 4 Success
- **Service Startup:** Clean initialization
- **Cross-Service:** Unified Redis usage
- **Golden Path:** 95%+ end-to-end success
- **Memory Usage:** 75% reduction in Redis memory

## Test Infrastructure Requirements

### No Docker Constraints
- All tests use `--no-docker` flag
- Real services only (staging GCP or unit/integration)
- No Docker container dependencies

### Test Framework Usage
- Use existing `tests/unified_test_runner.py`
- Follow `test_framework.ssot` patterns
- Real services through `--real-services` flag

### Output Collection
- All test outputs logged to files
- JSON structured data for analysis
- Performance metrics captured

## Validation Steps

1. **Prove Problem Exists:** All tests FAIL initially with expected patterns
2. **Document Violations:** 102+ violations documented with locations
3. **Correlate Failures:** WebSocket 1011 errors correlate with Redis violations
4. **Test Solution:** SSOT patterns fix the violations
5. **Validate Fix:** 95%+ success rates after remediation

## Business Impact Metrics

### Pre-Fix Metrics (Target to Prove)
- Redis SSOT Score: 25/100 (Critical)
- WebSocket Success Rate: 0% (staging evidence)
- Agent Reliability: 70% failure rate
- Memory Usage: High (12 connection pools)

### Post-Fix Target Metrics
- Redis SSOT Score: 95/100 (Excellent)
- WebSocket Success Rate: 95%+
- Agent Reliability: 95%+ success rate
- Memory Usage: 75% reduction

This test plan will definitively prove that Redis SSOT violations are blocking the Golden Path and validate that the remediation approach will restore $500K+ ARR chat functionality.