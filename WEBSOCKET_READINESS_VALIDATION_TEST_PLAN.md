# WebSocket Readiness Validation SSOT Test Plan

**Date**: 2025-09-09  
**Issue**: WebSocket readiness validation SSOT violations causing 25.01s timeout failures  
**Status**: COMPREHENSIVE TEST PLAN  
**Priority**: MISSION CRITICAL

## Executive Summary

**ROOT CAUSE**: GCP WebSocket readiness validation fails due to SSOT violations - multiple validation paths with inconsistent timeouts causing 25.01s failures that exceed GCP Cloud Run's ~10s health check expectations.

**BUSINESS IMPACT**: 
- Staging environment unstable for Golden Path validation
- WebSocket connections failing with 1011 errors
- Chat functionality completely broken for users
- Developer productivity blocked due to unreliable health checks

**TEST STRATEGY**: Build comprehensive test suite that FAILS initially (proving the issue exists) and PASSES after implementing SSOT consolidation and timeout coordination fixes.

## Problem Analysis

### Current SSOT Violations

1. **Multiple Redis Validation Paths**:
   - Health endpoint validates Redis directly (2-5s timeout)
   - WebSocket validator validates Redis again (30s timeout in GCP)
   - No coordination between validation results

2. **Inconsistent Timeout Management**:
   - Health route expects 10s total completion
   - WebSocket validator has 30s+ timeouts inappropriate for health checks
   - No unified timeout coordination manager

3. **Sequential Blocking Validation**:
   - All validations run sequentially instead of dependency-aware parallel execution
   - Single slow component blocks entire readiness check

### Evidence from System Analysis

**File**: `netra_backend/app/routes/health.py:408`
```python
# Current problematic flow:
websocket_readiness_status = await _check_gcp_websocket_readiness()  # 30s+ timeout
```

**File**: `netra_backend/app/websocket_core/gcp_initialization_validator.py:117`
```python
# Root cause: Excessive timeout for health checks
timeout_seconds=30.0 if self.is_gcp_environment else 10.0,  # TOO LONG for health checks
```

## Comprehensive Test Plan

### Phase 1: Unit Tests - Timeout Configuration Validation

**File**: `netra_backend/tests/unit/websocket_core/test_websocket_readiness_timeout_unit.py`

#### Test Categories

```python
class TestWebSocketReadinessTimeoutConfiguration:
    """Unit tests for WebSocket readiness timeout SSOT validation."""
    
    def test_gcp_redis_timeout_inappropriate_for_health_checks(self):
        """MUST FAIL INITIALLY - Test GCP Redis timeout is too long for health checks."""
        # Current: 30s timeout
        # Expected: ≤3s timeout for health checks
        # Validates SSOT violation in timeout configuration
        
    def test_health_check_timeout_coordination_missing(self):
        """MUST FAIL INITIALLY - Test lack of timeout coordination between components."""
        # Current: No coordination between 10s health expectation and 30s validator reality
        # Expected: Unified timeout management
        
    def test_redis_validation_duplication_detection(self):
        """MUST FAIL INITIALLY - Test detection of duplicate Redis validation."""
        # Current: Redis validated in health route AND WebSocket validator
        # Expected: Single Redis validation with result sharing
        
    def test_staging_environment_timeout_configuration(self):
        """Test staging-specific timeout configuration requirements."""
        # Staging should have fast timeouts for rapid feedback
        
    def test_production_vs_health_check_timeout_differentiation(self):
        """Test different timeout configs for production operations vs health checks."""
        # Health checks need fast timeouts, production operations can be longer
```

#### Mock Strategy
```python
# Use minimal mocks - focus on configuration validation
@pytest.fixture
def mock_gcp_environment():
    """Mock GCP environment detection for testing."""
    return True

@pytest.fixture  
def mock_websocket_validator_config():
    """Mock validator configuration for isolation testing."""
    # Only mock configuration, not service behavior
```

### Phase 2: Integration Tests - Health Endpoint Performance

**File**: `netra_backend/tests/integration/health/test_health_ready_performance_integration.py`

#### Test Categories

```python
class TestHealthReadyEndpointPerformance:
    """Integration tests for /health/ready endpoint performance with real services."""
    
    @pytest.mark.integration
    @pytest.mark.real_services  
    @pytest.mark.timeout(15)  # 15s to allow for measurement + buffer
    async def test_health_ready_completes_within_10s_requirement(self):
        """MUST FAIL INITIALLY - Test /health/ready completes within GCP requirement."""
        # Current: Times out after 25.01s
        # Expected: Completes within 10s
        # Uses real services via --real-services flag
        
    async def test_websocket_validator_performance_bottleneck(self):
        """MUST FAIL INITIALLY - Test WebSocket validator is performance bottleneck."""
        # Measure: Individual component timing
        # Current: WebSocket validator takes 25s+ due to Redis timeout
        # Expected: WebSocket validator completes in <5s
        
    async def test_sequential_vs_parallel_validation_timing(self):
        """Test timing difference between sequential and parallel validation."""
        # Current: All validations sequential
        # Proposed: Independent validations in parallel
        
    async def test_redis_validation_timeout_impact_measurement(self):
        """MUST FAIL INITIALLY - Measure Redis timeout impact on total response time."""
        # Current: 30s Redis timeout dominates response time
        # Expected: 3s Redis timeout enables fast response
```

#### Real Service Requirements
```python
# Use real services for authentic timing measurements
@pytest.fixture(scope="session")
async def real_services_stack():
    """Real services stack for integration testing."""
    # Uses unified test runner's --real-services infrastructure
    # PostgreSQL, Redis, Auth service all real
    
async def test_with_real_redis_connection():
    """Test with real Redis to measure actual network latency."""
    # No mocks - actual Redis connection timing
```

### Phase 3: Performance Tests - Timeout Measurement

**File**: `tests/performance/test_websocket_readiness_timing_benchmarks.py`

#### Test Categories

```python
class TestWebSocketReadinessTimingBenchmarks:
    """Performance benchmarks with precise timing measurement."""
    
    @pytest.mark.performance
    async def test_baseline_websocket_readiness_timing(self):
        """Establish baseline timing for WebSocket readiness validation."""
        # Measure: Each validation component individually
        # Create performance baseline for regression detection
        
    async def test_timeout_cascade_failure_reproduction(self):
        """MUST FAIL INITIALLY - Reproduce the 25.01s timeout cascade failure."""
        # Simulate exact conditions causing the timeout
        # Current: Should fail after 25.01s
        # Expected: Should complete successfully in <10s after fix
        
    async def test_concurrent_health_check_performance(self):
        """Test WebSocket readiness under concurrent health check load."""
        # Simulate load balancer health check frequency
        # Ensure no race conditions under load
        
    async def test_environment_specific_timeout_benchmarks(self):
        """Benchmark timeout performance across different environments."""
        # Test: local, staging, production timeout configurations
        # Validate environment-appropriate performance
```

#### Timing Validation Patterns
```python
from test_framework.validation.timing_validator import TimingValidator

class TestTimingValidation:
    async def test_with_precise_timing_measurement(self):
        """Use existing TimingValidator for precise measurements."""
        validator = TimingValidator()
        
        with validator.time_context("websocket_readiness"):
            # Actual validation call
            pass
            
        # Validate timing requirements
        assert validator.get_duration("websocket_readiness") < 10.0
```

### Phase 4: E2E Tests - Staging Environment Reproduction

**File**: `tests/e2e/websocket/test_websocket_readiness_timeout_reproduction_e2e.py`

#### Test Categories

```python
class TestWebSocketReadinessTimeoutReproductionE2E:
    """E2E tests reproducing exact staging environment conditions."""
    
    @pytest.mark.e2e
    @pytest.mark.staging  
    @pytest.mark.real_services
    async def test_staging_health_ready_timeout_reproduction(self):
        """MUST FAIL INITIALLY - Reproduce exact 25.01s timeout in staging."""
        # Direct test against staging endpoint
        # URL: https://netra-backend-staging-701982941522.us-central1.run.app/health/ready
        # Current: Should timeout after 25.01s
        # Expected: Should succeed in <10s after fix
        
    async def test_websocket_connection_after_health_check_success(self):
        """Test WebSocket connection works after successful health check."""
        # Validates end-to-end business value
        # Health check success → WebSocket connection success → Chat works
        
    async def test_gcp_cloud_run_readiness_probe_simulation(self):
        """Simulate GCP Cloud Run readiness probe behavior."""
        # Replicate exact GCP load balancer conditions
        # Timing: 10s timeout, probe frequency, etc.
        
    async def test_multi_user_websocket_after_readiness_fix(self):
        """Test multi-user WebSocket isolation after readiness validation fix."""
        # Ensure fix doesn't break user context isolation
        # Uses authenticated WebSocket connections
```

#### E2E Authentication Requirements
```python
# ALL E2E tests MUST use authentication per CLAUDE.md
from test_framework.ssot.e2e_auth_helper import get_authenticated_client

class TestAuthenticatedE2E:
    async def test_with_real_authentication(self):
        """E2E test using real authentication flow."""
        async with get_authenticated_client() as client:
            # Real JWT tokens, real OAuth flow
            # No auth mocking allowed in E2E tests
            pass
```

### Phase 5: SSOT Compliance Tests - Validation Logic Consolidation

**File**: `tests/unit/websocket_core/test_websocket_readiness_ssot_compliance_unit.py`

#### Test Categories

```python
class TestWebSocketReadinessSSotCompliance:
    """Tests validating SSOT compliance for WebSocket readiness logic."""
    
    def test_single_redis_validation_path_enforcement(self):
        """MUST FAIL INITIALLY - Test enforcement of single Redis validation path."""
        # Current: Multiple Redis validation paths
        # Expected: Single canonical Redis validation with result sharing
        
    def test_unified_timeout_manager_usage(self):
        """MUST FAIL INITIALLY - Test usage of unified timeout manager."""
        # Current: Scattered timeout configurations
        # Expected: Single timeout manager SSOT
        
    def test_websocket_validator_factory_ssot_pattern(self):
        """Test WebSocket validator follows factory SSOT patterns."""
        # Validate factory pattern usage for user isolation
        # Ensure no singleton anti-patterns
        
    def test_health_check_coordinator_ssot_compliance(self):
        """Test health check coordination follows SSOT principles."""
        # Single coordinator for health check orchestration
        # No duplicate health check logic
```

#### SSOT Pattern Validation
```python
# Test SSOT patterns per CLAUDE.md requirements
class TestSSotPatterns:
    def test_websocket_readiness_single_source_of_truth(self):
        """Validate WebSocket readiness has single canonical implementation."""
        # Search for duplicate implementations
        # Ensure all code paths use same validation logic
        
    def test_timeout_configuration_single_source(self):
        """Validate timeout configuration has single authoritative source."""
        # No scattered timeout constants
        # Single configuration manager for all timeouts
```

### Phase 6: Regression Prevention Tests

**File**: `tests/regression/test_websocket_readiness_regression_prevention.py`

#### Test Categories

```python
class TestWebSocketReadinessRegressionPrevention:
    """Regression tests ensuring fix doesn't break existing functionality."""
    
    async def test_basic_health_endpoint_unchanged(self):
        """Test /health endpoint continues working after readiness fix."""
        
    async def test_database_health_endpoint_unchanged(self):
        """Test /health/database endpoint continues working after readiness fix."""
        
    async def test_websocket_agent_events_still_work(self):
        """MISSION CRITICAL - Test WebSocket agent events still work after fix."""
        # Validate all 5 required agent events:
        # agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        
    async def test_multi_user_isolation_preserved(self):
        """Test user context isolation preserved after readiness validation changes."""
        # Factory pattern validation
        # No shared state introduced by timeout fixes
        
    async def test_authentication_flows_unchanged(self):
        """Test authentication flows unaffected by WebSocket readiness changes."""
```

## Test Execution Strategy

### Phase 1: Issue Reproduction (All Tests Should FAIL)

```bash
# Run tests demonstrating current SSOT violations
python tests/unified_test_runner.py --category unit --filter websocket_readiness_timeout
python tests/unified_test_runner.py --category integration --filter health_ready_performance --real-services
python tests/unified_test_runner.py --category e2e --filter websocket_readiness_timeout --staging --real-services

# Expected result: Tests FAIL, proving the issue exists
```

### Phase 2: SSOT Consolidation Implementation

**Timeout Management SSOT**:
1. Create `WebSocketReadinessTimeoutManager` SSOT class
2. Consolidate all timeout configurations into single source
3. Implement environment-aware timeout coordination

**Validation Logic SSOT**:
1. Create `UnifiedReadinessValidator` consolidating health + WebSocket validation
2. Eliminate duplicate Redis validation paths  
3. Implement result sharing between health endpoint and WebSocket validator

**Health Check Coordination**:
1. Create `HealthCheckCoordinator` for managing sequential vs parallel execution
2. Implement timeout budgeting (10s total budget allocation)
3. Add graceful degradation for non-critical services

### Phase 3: Fix Validation (All Tests Should PASS)

```bash
# Run same tests after SSOT consolidation
python tests/unified_test_runner.py --category unit --filter websocket_readiness_timeout
python tests/unified_test_runner.py --category integration --filter health_ready_performance --real-services  
python tests/unified_test_runner.py --category e2e --filter websocket_readiness_timeout --staging --real-services
python tests/unified_test_runner.py --category regression --filter websocket_readiness

# Expected result: Tests PASS, proving the fix works
```

## Specific Implementation Requirements

### SSOT Classes to Create

```python
# Unified timeout management
class WebSocketReadinessTimeoutManager:
    """SSOT for all WebSocket readiness timeout configurations."""
    
    def get_health_check_timeout(self, environment: str) -> float:
        """Get appropriate timeout for health check context."""
        # Health checks: fast timeouts (3s Redis, 2s PostgreSQL)
        
    def get_production_timeout(self, environment: str) -> float:  
        """Get appropriate timeout for production operations."""
        # Production operations: longer timeouts (30s Redis, 15s PostgreSQL)

# Unified validation logic        
class UnifiedReadinessValidator:
    """SSOT for WebSocket readiness validation eliminating duplicates."""
    
    async def validate_redis_once(self) -> ValidationResult:
        """Single Redis validation with result caching/sharing."""
        
    async def validate_with_timeout_coordination(self) -> ReadinessResult:
        """Coordinated validation respecting timeout budgets."""

# Health check coordination
class HealthCheckCoordinator:
    """SSOT for health check orchestration and timeout management."""
    
    async def execute_with_budget(self, checks: List[Check], budget_seconds: float):
        """Execute health checks within total time budget."""
```

### Timeout Requirements by Context

**Health Check Context** (Fast feedback required):
- PostgreSQL: 2s timeout
- Redis: 3s timeout (reduced from 30s)
- ClickHouse: 8s timeout
- Auth validation: 20s timeout  
- **Total budget: 10s maximum**

**Production Operation Context** (Reliability required):
- PostgreSQL: 15s timeout
- Redis: 30s timeout (current, appropriate for production)
- ClickHouse: 45s timeout
- Auth validation: 60s timeout
- **No artificial time budget constraints**

## Success Criteria

### Fix Validation Requirements

1. **All initially-failing tests now PASS** ✅
2. **All regression tests continue to PASS** ✅  
3. **Staging /health/ready responds within 10s** ✅
4. **Redis timeout reduced to 3s for health checks** ✅
5. **WebSocket functionality preserved** ✅
6. **SSOT compliance achieved** ✅
7. **Performance meets business requirements** ✅

### Performance Benchmarks

**Pre-Fix (FAILING state)**:
- /health/ready response time: 25.01s (timeout)
- Redis validation: 30s timeout (inappropriate)
- WebSocket validator: 30s+ total time
- User abandonment: >90% (unacceptable)

**Post-Fix (PASSING state)**:
- /health/ready response time: <10s (success)
- Redis validation: 3s timeout (appropriate)  
- WebSocket validator: <8s total time
- User abandonment: <30% (acceptable)

## Integration with Existing Test Framework

### Use Existing Patterns

- `TimingValidator` for precise timing measurement
- `--real-services` flag for authentic service testing
- `test_framework/ssot/e2e_auth_helper.py` for authenticated E2E tests
- Unified test runner categories for organized execution
- Factory patterns for user context isolation
- WebSocket event validation for business value verification

### Test Categories for Unified Test Runner

```bash
# Organized test execution
--category unit --filter websocket_readiness         # Unit tests
--category integration --filter health_performance   # Integration tests  
--category performance --filter timing_benchmarks   # Performance tests
--category e2e --filter websocket_readiness         # E2E tests
--category regression --filter websocket_readiness   # Regression tests
--category ssot --filter websocket_validation       # SSOT compliance
```

This comprehensive test plan ensures the WebSocket readiness validation SSOT issues are validated from multiple angles, proves the timeout issues exist, validates SSOT consolidation fixes work, and prevents regressions while maintaining all existing business value functionality.