# Test Plan for Issue #1278 - Database Connectivity and FastAPI Lifespan Validation

**Issue**: #1278 - GCP-regression | P0 | Application startup failure in staging environment
**Created**: 2025-09-15
**Priority**: P0 Critical
**Category**: Infrastructure/Application Startup/Database Connectivity

## Executive Summary

This test plan addresses the database connectivity and FastAPI lifespan issues identified in Issue #1278 comprehensive audit. Based on audit findings showing **infrastructure issues but correct code implementation**, this plan focuses on reproducing and validating the database timeout and startup sequence failures to confirm whether infrastructure fixes resolve the application startup issues.

## Audit Context & Root Cause Analysis

### **Five Whys Analysis Results**:
1. **Why 1**: SMD Phase 3 (DATABASE) consistently timing out after 35.0s
2. **Why 2**: Database connection attempts to Cloud SQL timing out despite proper configuration
3. **Why 3**: Infrastructure-level socket connection failures to Cloud SQL VPC connector
4. **Why 4**: Platform-level VPC connector or Cloud SQL instance instability
5. **Why 5**: Cloud SQL instance `netra-staging:us-central1:staging-shared-postgres` experiencing platform-level connectivity issues

### **Key Findings**:
- ✅ **Application Code**: Correctly implemented (SMD, timeouts, lifespan management)
- ❌ **Infrastructure**: VPC connector → Cloud SQL connectivity broken at platform level
- ✅ **Configuration**: Proper 35.0s timeout for staging Cloud SQL compatibility
- ❌ **Platform**: Confirmed infrastructure failure requiring immediate escalation

## Test Categories & Strategy

Following `reports/testing/TEST_CREATION_GUIDE.md` and `CLAUDE.md` testing best practices:

### **Test Hierarchy (Business Value Focus)**:
```
Real E2E with Real Cloud SQL (MAXIMUM VALUE - Infrastructure Validation)
    ↓
Integration with Real Services (GOOD - System Validation)
    ↓
Unit with Minimal Mocks (ACCEPTABLE - Fast Feedback)
```

### **Test Categories Planned**:
1. **Unit Tests**: Database timeout configuration validation (no Docker)
2. **Integration Tests**: Database connectivity with real services (no Docker)
3. **E2E Staging Tests**: Complete startup sequence validation on real GCP staging environment

## 1. Unit Test Plan

### **File**: `tests/unit/issue_1278_database_connectivity_timeout_validation.py`

**Business Value Justification (BVJ)**:
- **Segment**: Platform/Internal (System Validation)
- **Business Goal**: Validate timeout configuration correctness
- **Value Impact**: Confirms timeout settings match Cloud SQL requirements
- **Strategic Impact**: Prevents configuration-related startup failures

**Test Cases**:

#### 1.1 Database Timeout Configuration Validation
```python
def test_staging_timeout_configuration_cloud_sql_compatibility():
    """Validate staging timeouts are sufficient for Cloud SQL VPC connector."""
    staging_config = get_database_timeout_config('staging')

    # Validate 35.0s timeout is configured (per Issue #1263 fix)
    assert staging_config['initialization_timeout'] == 35.0
    assert staging_config['connection_timeout'] == 15.0
    assert staging_config['pool_timeout'] == 15.0
```

#### 1.2 FastAPI Lifespan Error Handling Validation
```python
def test_deterministic_startup_error_handling():
    """Validate DeterministicStartupError raises and prevents degraded startup."""
    # Test that SMD Phase 3 failures properly raise DeterministicStartupError
    # Test that lifespan manager correctly handles these errors (line 71-76)
```

#### 1.3 SMD Phase Dependency Validation
```python
def test_smd_phase_3_database_timeout_error_messaging():
    """Validate SMD Phase 3 provides proper Cloud SQL error messaging."""
    # Test error message generation (lines 1012-1018 in smd.py)
    # Validate Cloud SQL-specific error context
```

### **Execution Environment**: No Docker required, uses test configuration

---

## 2. Integration Test Plan

### **File**: `tests/integration/issue_1278_database_connectivity_integration_comprehensive.py`

**Business Value Justification (BVJ)**:
- **Segment**: Platform/Internal (System Integration)
- **Business Goal**: Validate database connectivity components work together
- **Value Impact**: Confirms application startup sequence with real database attempts
- **Strategic Impact**: Validates readiness for infrastructure fixes

**Test Cases**:

#### 2.1 Database Manager Initialization with Cloud SQL Timeouts
```python
async def test_database_manager_initialization_timeout_behavior():
    """Test DatabaseManager with staging timeout configuration."""
    # Use real database connection attempts with 35.0s timeout
    # Should either succeed (if infrastructure fixed) or timeout appropriately
    # NO MOCKS - real Cloud SQL connection attempts
```

#### 2.2 SMD Phase 3 Integration Testing
```python
async def test_smd_phase_3_database_initialization_integration():
    """Test complete SMD Phase 3 execution with real database."""
    # Execute actual SMD Phase 3 with staging configuration
    # Monitor for 35.0s timeout behavior
    # Validate error propagation to FastAPI lifespan
```

#### 2.3 FastAPI Lifespan Manager Integration
```python
async def test_fastapi_lifespan_deterministic_startup_failure_handling():
    """Test lifespan manager behavior during SMD failures."""
    # Simulate SMD Phase 3 failure conditions
    # Validate lifespan manager error handling (lines 62-76)
    # Confirm no degraded startup allowed
```

#### 2.4 Database Connection Pool Timeout Validation
```python
async def test_database_connection_pool_cloud_sql_timeout_handling():
    """Test connection pool behavior with Cloud SQL VPC connector."""
    # Test connection pool establishment with 15.0s pool_timeout
    # Validate socket establishment timing
    # Monitor for "/cloudsql/..." socket path connectivity
```

### **Execution Environment**: Real PostgreSQL + Redis services, no Docker required

---

## 3. E2E Staging Test Plan

### **File**: `tests/e2e_staging/issue_1278_complete_startup_sequence_staging_validation.py`

**Business Value Justification (BVJ)**:
- **Segment**: Platform/Critical (Revenue Protection)
- **Business Goal**: Validate complete application startup in real staging
- **Value Impact**: $500K+ ARR validation pipeline functionality
- **Strategic Impact**: Critical P0 outage resolution validation

**Test Cases**:

#### 3.1 Complete Application Startup Sequence Reproduction
```python
async def test_complete_application_startup_sequence_staging():
    """Test complete 7-phase SMD startup sequence in staging environment."""
    # Test against real staging endpoints:
    # - https://netra-backend-staging-701982941522.us-central1.run.app
    # Monitor complete startup sequence:
    # ✅ Phase 1 (INIT) - Initialization
    # ✅ Phase 2 (DEPENDENCIES) - Dependencies loaded
    # ❌ Phase 3 (DATABASE) - Connection timeout (issue reproduction)
    # Track timing and failure patterns
```

#### 3.2 Cloud SQL Connectivity Validation
```python
async def test_cloud_sql_vpc_connector_connectivity_staging():
    """Test direct Cloud SQL connectivity through VPC connector."""
    # Test connection to: netra-staging:us-central1:staging-shared-postgres
    # Socket path: /cloudsql/netra-staging:us-central1:staging-shared-postgres/.s.PGSQL.5432
    # Validate 35.0s timeout behavior
    # Monitor for platform-level connectivity issues
```

#### 3.3 Health Endpoint Startup Dependency Validation
```python
async def test_health_endpoints_database_dependency_staging():
    """Test health endpoints during database connectivity issues."""
    # Test /health, /health/ready, /health/database endpoints
    # Validate response during SMD Phase 3 failures
    # Monitor for 503 Service Unavailable responses
```

#### 3.4 Container Exit Code Validation
```python
async def test_container_exit_code_3_startup_failure_staging():
    """Test container termination behavior during startup failures."""
    # Monitor container logs for "Container called exit(3)"
    # Validate graceful shutdown during SMD Phase 3 timeout
    # Confirm no resource leaks or hanging processes
```

### **Execution Environment**: Real GCP staging environment (Cloud Run + Cloud SQL)

---

## 4. Performance & Timing Validation Tests

### **File**: `tests/integration/issue_1278_database_timing_performance_validation.py`

**Test Cases**:

#### 4.1 Database Connection Timing Benchmarks
```python
async def test_database_connection_timing_cloud_sql_benchmarks():
    """Benchmark database connection times for Cloud SQL optimization."""
    # Measure connection establishment timing
    # Validate 35.0s timeout provides adequate buffer
    # Monitor for consistent timeout vs sporadic failures
```

#### 4.2 SMD Phase Performance Monitoring
```python
async def test_smd_phase_timing_performance_monitoring():
    """Monitor SMD phase execution timing patterns."""
    # Track Phase 1-7 execution times
    # Identify performance bottlenecks
    # Validate timeout configurations are appropriate
```

---

## 5. Error Scenario & Recovery Tests

### **File**: `tests/integration/issue_1278_error_scenarios_recovery_validation.py`

**Test Cases**:

#### 5.1 Database Connection Failure Recovery
```python
async def test_database_connection_failure_graceful_degradation():
    """Test application behavior during database connectivity failures."""
    # Simulate VPC connector failures
    # Validate error messaging and logging
    # Confirm no silent failures or degraded operation
```

#### 5.2 FastAPI Lifespan Context Breakdown Testing
```python
async def test_fastapi_lifespan_context_breakdown_scenarios():
    """Test lifespan context management during startup failures."""
    # Test generator corruption prevention
    # Validate cleanup operations during failures
    # Monitor for "already running" errors
```

---

## Test Execution Strategy

### **Phase 1: Reproduction & Validation (0-4 hours)**
1. **Execute Unit Tests**: Validate timeout configuration correctness
2. **Execute Integration Tests**: Reproduce database connectivity issues with real services
3. **Execute E2E Staging Tests**: Confirm infrastructure failure reproduction

### **Phase 2: Infrastructure Fix Validation (Post-Infrastructure Fix)**
1. **Re-run E2E Staging Tests**: Validate startup sequence success
2. **Re-run Integration Tests**: Confirm database connectivity restoration
3. **Performance Validation**: Confirm startup timing improvements

### **Success Criteria**

#### **Before Infrastructure Fix** (Expected to FAIL):
- E2E staging tests timeout after 35.0s with database connectivity errors
- Integration tests reproduce SMD Phase 3 failures
- Container exit code 3 observed during startup failures

#### **After Infrastructure Fix** (Expected to PASS):
- Complete 7-phase SMD startup sequence succeeds in <30s
- Database connectivity established within timeout windows
- Health endpoints respond successfully
- Container starts successfully without exit code 3

### **Test Framework Requirements**

Following `TEST_CREATION_GUIDE.md` requirements:

```python
# Required imports for all tests
from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.real_services_test_fixtures import real_services_fixture
from shared.isolated_environment import IsolatedEnvironment

# Test markers
@pytest.mark.integration  # For integration tests
@pytest.mark.e2e_staging  # For staging E2E tests
@pytest.mark.real_services # For tests requiring real services
@pytest.mark.mission_critical # For critical startup sequence tests
```

### **Execution Commands**

```bash
# Unit tests (fast feedback)
python tests/unified_test_runner.py --category unit --test-file tests/unit/issue_1278_*

# Integration tests (real services, no Docker)
python tests/unified_test_runner.py --category integration --real-services --test-file tests/integration/issue_1278_*

# E2E staging tests (real GCP environment)
python tests/unified_test_runner.py --category e2e_staging --env staging --test-file tests/e2e_staging/issue_1278_*

# Complete test suite
python tests/unified_test_runner.py --categories unit integration e2e_staging --real-services --env staging
```

### **Monitoring & Alerting**

- **Alert Trigger**: SMD Phase 3 failure rate >10% in 5-minute window
- **Escalation**: Container exit code 3 >3 occurrences in 10 minutes
- **Business Alert**: Complete startup failure >2 minutes duration

### **Expected Test Outcomes**

#### **Immediate (Before Infrastructure Fix)**:
- Tests **WILL FAIL** - confirming infrastructure issue reproduction
- Validate that application code is correctly implemented
- Demonstrate timing and error patterns match audit findings

#### **Post-Infrastructure Fix**:
- Tests **SHOULD PASS** - confirming infrastructure resolution
- Validate complete startup sequence functionality
- Confirm Golden Path restoration for $500K+ ARR validation pipeline

---

## Documentation & Compliance

### **Test Documentation Requirements**:
- Each test includes **Business Value Justification (BVJ)**
- Follow naming convention: `test_issue_1278_*`
- Include error reproduction patterns
- Document infrastructure dependencies

### **Compliance Checklist**:
- [ ] Tests use real services (no mocks except unit tests)
- [ ] Tests fail properly when infrastructure issues present
- [ ] Tests validate actual business value delivery
- [ ] Tests follow SSOT patterns from test_framework/
- [ ] Tests include proper pytest markers
- [ ] Tests validate WebSocket events (where applicable)

---

**Final Recommendation**: Execute this test plan to **validate infrastructure fix effectiveness** and **confirm application startup restoration**. The tests are designed to FAIL initially (confirming infrastructure issues) and PASS after infrastructure fixes (confirming resolution).

🤖 **Generated with [Claude Code](https://claude.ai/code)**

**Co-Authored-By**: Claude <noreply@anthropic.com>
**Test Plan Session**: `test-plan-issue-1278-20250915`