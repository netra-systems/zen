# Issue #889 WebSocket Manager SSOT Violations - Comprehensive Test Plan

**Created:** 2025-09-15  
**Issue:** [#889 - SSOT WebSocket Manager Duplication Warnings](https://github.com/netra-systems/netra-apex/issues/889)  
**Agent Session:** agent-session-2025-09-15-1430  
**Priority:** P2 (escalated from P3 due to high frequency)  

## Executive Summary

This test plan targets the critical SSOT violations identified in Issue #889, specifically the "Multiple manager instances for user demo-user-001 - potential duplication" warnings appearing consistently in GCP staging logs. The violations indicate that the WebSocket manager factory pattern is bypassing SSOT principles, creating security and performance risks in our $500K+ ARR chat functionality.

### Business Impact
- **Revenue at Risk:** $500K+ ARR dependent on reliable WebSocket chat functionality  
- **User Experience:** Multi-user isolation failures can cause data leakage and poor performance  
- **Regulatory Compliance:** SSOT violations threaten SOC2, HIPAA, and SEC compliance readiness  
- **System Stability:** Duplicate manager instances consume resources and create race conditions  

## Problem Analysis

### Root Cause Identification
Based on analysis of `/Users/anthony/Desktop/netra-apex/netra_backend/app/websocket_core/websocket_manager.py` lines 182-281:

1. **4 Creation Paths:** The `get_websocket_manager()` function has multiple creation paths that can lead to duplication
2. **demo-user-001 Pattern:** 90%+ of violations occur with test/demo user patterns
3. **Factory Bypass:** Direct instantiation bypassing SSOT validation
4. **User Context Issues:** Improper handling when user_context is None or invalid

### Specific Violation Patterns
From GCP logs analysis:
```
"SSOT validation issues (non-blocking): ['Multiple manager instances for user demo-user-001 - potential duplication']"
```

## Test Strategy

### Test Philosophy
Following `/Users/anthony/Desktop/netra-apex/reports/testing/TEST_CREATION_GUIDE.md`:

1. **Tests MUST FAIL Initially** - Reproduce the exact violations seen in production
2. **Real Services Over Mocks** - Use actual WebSocket infrastructure where possible  
3. **Business Value Focus** - Protect chat functionality (90% of platform value)
4. **SSOT Compliance** - Validate proper factory patterns and user isolation

### Test Categories & Execution Requirements

#### 1. Unit Tests (Non-Docker)
**Purpose:** Detect specific SSOT violations in manager creation logic  
**Infrastructure:** None required  
**Expected:** FAIL initially, PASS after remediation  

#### 2. Integration Tests (Non-Docker) 
**Purpose:** Test multi-user scenarios causing isolation violations  
**Infrastructure:** Local services (PostgreSQL, Redis)  
**Expected:** FAIL initially with clear violation messages  

#### 3. E2E Staging Tests (GCP)
**Purpose:** Validate real production scenarios like demo-user-001  
**Infrastructure:** GCP staging environment  
**Expected:** FAIL initially, reproducing exact log patterns  

## Detailed Test Plan

### Phase 1: Unit Tests - Manager Creation Duplication Detection

#### Test File: `tests/unit/websocket_ssot/test_issue_889_manager_duplication_unit.py`

**Test 1.1: Direct Factory Bypass Detection**
```python
async def test_direct_instantiation_bypasses_ssot_factory():
    """
    MUST FAIL INITIALLY: Detect when code bypasses SSOT factory pattern
    
    Business Value: Protects factory pattern integrity for user isolation
    Expected Failure: Should detect multiple manager instances for same user
    """
    # Create multiple managers for same user through different paths
    # Should detect SSOT violation and fail initially
```

**Test 1.2: demo-user-001 Pattern Reproduction**
```python
async def test_demo_user_001_duplication_pattern():
    """
    MUST FAIL INITIALLY: Reproduce exact pattern seen in GCP logs
    
    Business Value: Validates test user patterns don't cause production issues
    Expected Failure: "Multiple manager instances for user demo-user-001"
    """
    # Recreate exact demo-user-001 scenario from logs
    # Should reproduce the violation message exactly
```

**Test 1.3: Null User Context Handling**
```python
async def test_null_user_context_creates_duplicate_managers():
    """
    MUST FAIL INITIALLY: Detect when null context creates multiple test managers
    
    Business Value: Ensures proper test isolation doesn't affect production
    Expected Failure: Multiple test managers created instead of reusing
    """
    # Test scenario where user_context is None
    # Should detect multiple test manager creation
```

**Test 1.4: SSOT Validation Bypass**
```python
async def test_ssot_validation_enhancer_bypass():
    """
    MUST FAIL INITIALLY: Detect when SSOT validation is bypassed
    
    Business Value: Ensures validation always runs in production
    Expected Failure: Manager created without proper SSOT validation
    """
    # Test ImportError scenario for validation enhancer
    # Should detect validation bypass
```

#### Test File: `tests/unit/websocket_ssot/test_issue_889_user_isolation_unit.py`

**Test 1.5: User Context Isolation Violations**
```python
async def test_user_context_contamination():
    """
    MUST FAIL INITIALLY: Detect when user contexts bleed between managers
    
    Business Value: Critical for HIPAA/SOC2 compliance - no data leakage
    Expected Failure: User data contamination detected
    """
    # Create managers for different users
    # Should detect context bleeding between users
```

### Phase 2: Integration Tests - Multi-User Scenario Validation

#### Test File: `tests/integration/websocket_ssot/test_issue_889_manager_duplication_integration.py`

**Test 2.1: Concurrent User Manager Creation**
```python
async def test_concurrent_user_manager_creation_duplication(real_services_fixture):
    """
    MUST FAIL INITIALLY: Detect duplication in concurrent scenarios
    
    Business Value: Ensures scalability and prevents resource waste
    Expected Failure: Multiple managers created for concurrent requests
    """
    # Simulate concurrent requests for same user
    # Should detect manager duplication under load
```

**Test 2.2: Cross-Service Manager Consistency**
```python
async def test_cross_service_manager_consistency(real_services_fixture):
    """
    MUST FAIL INITIALLY: Detect inconsistent manager states across services
    
    Business Value: Ensures consistent WebSocket behavior across platform
    Expected Failure: Manager state inconsistency detected
    """
    # Test manager creation across backend and auth services
    # Should detect consistency violations
```

**Test 2.3: demo-user-001 Integration Scenario**
```python
async def test_demo_user_001_integration_duplication(real_services_fixture):
    """
    MUST FAIL INITIALLY: Reproduce production demo user scenario
    
    Business Value: Validates test patterns don't impact production reliability
    Expected Failure: Exact reproduction of GCP log violation
    """
    # Full integration test with demo-user-001 pattern
    # Should reproduce exact log message from staging
```

### Phase 3: E2E Staging Tests - Production Scenario Validation

#### Test File: `tests/e2e/staging/test_issue_889_websocket_manager_duplication_e2e.py`

**Test 3.1: Staging Environment Violation Reproduction**
```python
async def test_staging_demo_user_001_violation_reproduction():
    """
    MUST FAIL INITIALLY: Reproduce exact staging environment violations
    
    Business Value: Validates fixes work in production-like environment
    Expected Failure: "SSOT validation issues: ['Multiple manager instances for user demo-user-001']"
    """
    # Connect to staging WebSocket infrastructure
    # Should reproduce exact log patterns from GCP
```

**Test 3.2: Golden Path Multi-User Validation**
```python
async def test_golden_path_multi_user_manager_isolation():
    """
    MUST FAIL INITIALLY: Detect isolation failures in complete user flow
    
    Business Value: Protects $500K+ ARR Golden Path functionality
    Expected Failure: User isolation violation in complete chat flow
    """
    # Full Golden Path test with multiple concurrent users
    # Should detect isolation and duplication issues
```

## Test Infrastructure Requirements

### SSOT Base Classes
All tests inherit from SSOT-compliant base classes:
```python
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase
```

### Real Services Fixtures
Integration tests use real infrastructure:
```python
from test_framework.real_services_test_fixtures import (
    real_services_fixture,
    real_db_fixture,
    real_redis_fixture
)
```

### WebSocket Testing Utilities
E2E tests use WebSocket helpers:
```python
from test_framework.websocket_helpers import (
    WebSocketTestClient,
    assert_websocket_events,
    wait_for_agent_completion
)
```

### Environment Configuration
All tests use isolated environment management:
```python
from shared.isolated_environment import IsolatedEnvironment, get_env
```

## Success Criteria

### Initial Test Execution (Must FAIL)
1. **Unit Tests:** 7/7 tests FAIL with clear violation messages
2. **Integration Tests:** 3/3 tests FAIL reproducing production scenarios  
3. **E2E Tests:** 2/2 tests FAIL with exact staging log patterns
4. **Total:** 12/12 tests FAIL initially, proving violations exist

### Post-Remediation (Must PASS)
1. **SSOT Compliance:** All tests PASS after factory pattern fixes
2. **Performance:** No resource leaks from duplicate managers
3. **Isolation:** Clean user context separation validated
4. **Monitoring:** GCP logs show zero "Multiple manager instances" warnings

## Test Execution Commands

### Unit Tests (Fast Feedback)
```bash
# Run Issue #889 unit tests
python tests/unified_test_runner.py --test-pattern "*issue_889*unit*" --category unit

# Specific test files
python tests/unified_test_runner.py --test-file tests/unit/websocket_ssot/test_issue_889_manager_duplication_unit.py
python tests/unified_test_runner.py --test-file tests/unit/websocket_ssot/test_issue_889_user_isolation_unit.py
```

### Integration Tests (Real Services)
```bash
# Run with real PostgreSQL and Redis
python tests/unified_test_runner.py --test-pattern "*issue_889*integration*" --category integration --real-services

# Specific integration test
python tests/unified_test_runner.py --test-file tests/integration/websocket_ssot/test_issue_889_manager_duplication_integration.py --real-services
```

### E2E Staging Tests (Production-like)
```bash
# Run against staging environment
python tests/unified_test_runner.py --test-pattern "*issue_889*e2e*" --category e2e --env staging

# Specific staging test
python tests/unified_test_runner.py --test-file tests/e2e/staging/test_issue_889_websocket_manager_duplication_e2e.py --env staging
```

## Monitoring and Validation

### GCP Log Monitoring
Monitor these log patterns during and after remediation:
```
"SSOT validation issues (non-blocking): ['Multiple manager instances for user demo-user-001 - potential duplication']"
```

### Performance Metrics
Track these indicators:
- WebSocket manager instance count per user
- Memory usage of WebSocket infrastructure  
- Connection establishment time
- Event delivery latency

### Business Metrics
Validate these business outcomes:
- Chat response time consistency
- User session isolation integrity
- Golden Path completion rate
- No user data contamination incidents

## Risk Assessment

### High Risk Areas
1. **Production Impact:** Tests must not affect staging/production systems
2. **Resource Management:** Ensure test cleanup prevents resource leaks
3. **User Data:** No actual user data in test scenarios
4. **Service Dependencies:** Tests should degrade gracefully if services unavailable

### Mitigation Strategies
1. **Isolated Test Environment:** All tests use dedicated test configuration
2. **Cleanup Procedures:** Comprehensive teardown in all test fixtures
3. **Synthetic Data:** Only test data patterns, never real user information
4. **Circuit Breakers:** Tests fail fast if dependencies unavailable

## Implementation Timeline

### Phase 1: Unit Tests (Day 1)
- Create 7 unit tests targeting specific violation patterns
- Focus on manager creation logic and SSOT compliance
- Expected: All tests FAIL initially with clear violation messages

### Phase 2: Integration Tests (Day 2)  
- Create 3 integration tests with real services
- Focus on multi-user scenarios and cross-service consistency
- Expected: Reproduce staging environment violation patterns

### Phase 3: E2E Staging Tests (Day 3)
- Create 2 E2E tests against staging environment
- Focus on Golden Path and demo-user-001 scenarios
- Expected: Exact reproduction of GCP log violations

### Validation & Documentation (Day 4)
- Execute complete test suite and document results
- Update Issue #889 with test execution results
- Prepare remediation recommendations based on test findings

## Documentation Requirements

### Test Results Documentation
- Initial test execution results (proving violations exist)
- Detailed failure analysis with violation patterns
- Performance impact assessment
- Remediation recommendations

### GitHub Issue Updates
- Test plan implementation status
- Test execution results with logs
- Links to specific test files and results
- Next steps for remediation

### SSOT Compliance Reporting
- Integration with existing SSOT compliance tracking
- Updates to master compliance dashboard
- Cross-references with related SSOT issues

---

**Next Steps:**
1. Create unit test files with failing tests
2. Create integration test files with real services
3. Create E2E staging test files
4. Execute test suite and document results
5. Update GitHub Issue #889 with findings

**Success Metric:** 12/12 tests FAIL initially, proving SSOT violations exist, then all PASS after remediation, confirming violation resolution.