# Issue #144 - Database Table Migration Inconsistency: Comprehensive Test Plan

**Status:** Test strategy complete - Comprehensive plan for reproducing failures and validating service-aware fixes

**Root Cause Confirmed:** Golden Path Validator architectural mismatch between monolithic assumptions and microservice reality

## Test Strategy Overview

### Architectural Problem
**Current State:** Golden Path Validator expects `user_sessions` table in backend database but sessions managed by Auth Service with `auth_sessions` table

**Service Boundary Violation:** Validator checks wrong service database, causing false failures in microservice architecture

## Test Categories

### 1. Failing Tests (Current State Reproduction)

#### 1.1 Monolithic Assumptions Tests ❌
**File:** `netra_backend/tests/unit/core/service_dependencies/test_golden_path_validator_monolithic_flaw.py`

**Purpose:** DESIGNED TO FAIL - Expose architectural violations

**Key Tests:**
- `test_user_auth_tables_validation_fails_with_correct_service_boundaries()`
- `test_service_boundary_violation_evidence()`
- `test_validator_assumes_monolithic_database_schema()`

**Expected:** FAIL (proves architectural problem)

#### 1.2 Service Boundary Violation Tests ❌
**File:** `netra_backend/tests/integration/golden_path/test_golden_path_service_boundaries.py`

**Purpose:** Integration-level validation of service isolation violations

**Expected:** FAIL (demonstrates cross-service database access)

### 2. Service-Aware Validation Tests (Post-Remediation Success)

#### 2.1 HTTP Service Health Tests ✅
**File:** `tests/integration/test_service_health_client_validation.py`

**Purpose:** Validate proper service-to-service communication via HTTP

**Key Tests:**
- Auth Service health endpoint validation
- Backend Service health endpoint validation
- Service isolation verification (no direct database access)

**Expected:** PASS after ServiceHealthClient migration

#### 2.2 Modernized Validator Tests ✅
**File:** `tests/unit/test_golden_path_validator_service_aware.py`

**Purpose:** Unit tests for service-aware validator logic

**Key Tests:**
- ServiceHealthClient integration
- Environment context detection
- HTTP endpoint routing by service type

**Expected:** PASS after migration complete

### 3. End-to-End Staging Validation

#### 3.1 Golden Path Flow Tests ✅
**File:** `tests/e2e/staging/test_golden_path_validation_staging_current.py`

**Purpose:** Complete user authentication and session flow validation

**Expected:** PASS after service-aware implementation

## Test Execution Plan

### Phase 1: Validate Current Failures
```bash
# Confirm architectural problems exist
python -m pytest netra_backend/tests/unit/core/service_dependencies/test_golden_path_validator_monolithic_flaw.py -v

# Verify service boundary violations
python -m pytest netra_backend/tests/integration/golden_path/test_golden_path_service_boundaries.py -v
```

### Phase 2: Implement Service-Aware Fixes
```bash
# Test HTTP-based service validation
python -m pytest tests/integration/test_service_health_client_validation.py -v

# Test modernized validator
python -m pytest tests/unit/test_golden_path_validator_service_aware.py -v
```

### Phase 3: End-to-End Validation
```bash
# Comprehensive staging flow test
python -m pytest tests/e2e/staging/test_golden_path_validation_staging_current.py -v
```

## Test Difficulty Assessment

**Complexity Level:** Medium-High (7/10)

**Challenges:**
- Deep microservice architecture understanding required
- Service integration with HTTP client mocking
- Environment context injection (staging vs localhost)
- Legacy migration with backward compatibility

**Time Estimate:** 2-3 development days
- Day 1: Reproduce and validate current architectural failures
- Day 2: Implement and test service-aware validation framework
- Day 3: End-to-end staging validation and deployment verification

## Expected Test Patterns

### Before Remediation
```
❌ Monolithic validation tests: FAIL (architectural violations exposed)
❌ Service boundary tests: FAIL (proving cross-service database access)
❌ Golden Path staging tests: FAIL (false negatives from wrong validation)

SUCCESS CRITERIA: Tests fail for correct architectural reasons
```

### After Remediation
```
✅ Service-aware validation tests: PASS (HTTP service communication)
✅ HTTP health client tests: PASS (proper service isolation)
✅ Golden Path staging tests: PASS (correct validation flow)
❌ Monolithic validation tests: STILL FAIL (proving fix prevents boundary violations)

SUCCESS CRITERIA: Service-aware tests pass, monolithic boundary violations still prevented
```

## Technical Implementation Targets

### Priority 1: Complete ServiceHealthClient Migration
- **File:** `C:\netra-apex\netra_backend\app\core\service_dependencies\golden_path_validator.py:252-263`
- **Action:** Update PostgreSQL validation to use ServiceHealthClient
- **Impact:** Eliminate direct database access for auth table validation

### Priority 2: Auth Service Integration
- **Method:** `_validate_user_auth_tables`
- **Change:** Migrate from backend database check to Auth Service HTTP endpoint
- **Result:** Respect service boundaries for session management

### Priority 3: Service Boundary Enforcement
- **Validation:** Remove monolithic assumptions from GOLDEN_PATH_REQUIREMENTS
- **Testing:** Ensure cross-service validation uses service APIs only
- **Monitoring:** Add service boundary violation detection

## Business Impact Validation

**Current Impact:** Golden Path validation fails despite working microservices, blocking deployment pipeline with false negatives

**Post-Fix Impact:** Accurate validation of service health without boundary violations, enabling reliable deployment automation

**Test Coverage:** Complete validation of user login → JWT validation → session management → agent execution flow

---

**Next Action:** Execute Phase 1 tests to confirm current architectural failures, then proceed with service-aware implementation

🤖 Generated with [Claude Code](https://claude.ai/code)

Co-Authored-By: Claude <noreply@anthropic.com>