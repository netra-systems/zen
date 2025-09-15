# Test Plan: Issue #605 - GCP Cold Start WebSocket E2E Test Infrastructure

**Business Value Justification:**
- **Segment**: Platform/Enterprise - Critical infrastructure validation
- **Business Goal**: Stability - Prevent $500K+ ARR loss from WebSocket failures in production
- **Value Impact**: Ensure reliable GCP cold start WebSocket performance for chat functionality
- **Strategic Impact**: Protect Golden Path user experience during GCP cold start scenarios

## Context Analysis

**Current Issue Status** (from previous analysis):
- **Event Loop API Incompatibility**: `websockets.connect()` timeout parameter incompatible with current asyncio event loop
- **Class Inheritance Mismatch**: Tests inherit from `BaseE2ETest` instead of `StagingTestBase` 
- **GCP Connectivity Issues**: JSON parsing errors and authentication header stripping
- **Success Rate**: 20% (1/5 tests passing) - indicating systematic infrastructure problems

**Root Causes Identified:**
1. **Asyncio Event Loop Incompatibility**: Modern WebSocket libraries expect different event loop patterns
2. **Authentication Header Stripping**: GCP Load Balancer configuration strips critical headers
3. **Cold Start Timing Issues**: WebSocket connections failing during GCP Cloud Run cold starts
4. **Test Infrastructure Gaps**: Missing comprehensive test coverage for staging environment scenarios

## Test Strategy: FAILING TESTS FIRST

**Philosophy**: Create tests that FAIL initially to prove issues exist, then can pass after fixes are implemented.

### Phase 1: Unit Tests (Non-Docker) - Validate API Compatibility

**Objective**: Identify and prove WebSocket API incompatibilities in isolation

#### 1.1 WebSocket Connection API Compatibility Tests

**File**: `tests/unit/issue_605/test_websocket_api_compatibility.py`

**Test Cases**:
```python
class TestWebSocketAPICompatibility(SSotBaseTestCase):
    """Unit tests for WebSocket API compatibility issues causing Issue #605 failures."""
    
    async def test_websockets_connect_timeout_parameter_compatibility(self):
        """
        FAILING TEST: Prove websockets.connect() timeout parameter incompatibility.
        
        Expected to FAIL initially due to Event Loop API incompatibility.
        """
        # Test different timeout parameter patterns that fail
        
    async def test_asyncio_event_loop_websocket_compatibility(self):
        """
        FAILING TEST: Test asyncio event loop patterns with WebSocket connections.
        
        Expected to FAIL due to event loop API changes.
        """
        
    def test_websocket_library_version_compatibility_matrix(self):
        """
        TEST: Validate WebSocket library versions and their API compatibility.
        
        This should PASS and document the compatibility matrix.
        """
```

#### 1.2 Test Class Inheritance Compatibility Tests  

**File**: `tests/unit/issue_605/test_staging_test_base_inheritance.py`

**Test Cases**:
```python
class TestStagingTestBaseInheritance(SSotBaseTestCase):
    """Unit tests for staging test base class inheritance issues."""
    
    def test_baseE2etest_vs_staging_test_base_inheritance_conflict(self):
        """
        FAILING TEST: Prove inheritance mismatch between BaseE2ETest and StagingTestBase.
        
        Expected to FAIL due to class inheritance conflicts.
        """
        
    def test_staging_test_base_method_availability(self):
        """
        TEST: Validate StagingTestBase provides required methods for E2E tests.
        """
        
    def test_async_test_method_compatibility(self):
        """
        FAILING TEST: Test async method patterns in different base classes.
        
        Expected to show incompatibility issues.
        """
```

#### 1.3 GCP Authentication Header Validation Tests

**File**: `tests/unit/issue_605/test_gcp_header_validation.py`

**Test Cases**:
```python
class TestGCPHeaderValidation(SSotBaseTestCase):
    """Unit tests for GCP authentication header handling."""
    
    def test_authorization_header_preservation_patterns(self):
        """
        TEST: Validate authorization header patterns that should be preserved.
        """
        
    def test_websocket_upgrade_header_requirements(self):
        """  
        TEST: Document WebSocket upgrade header requirements for GCP.
        """
        
    def test_e2e_bypass_header_validation(self):
        """
        TEST: Validate E2E bypass header patterns for staging tests.
        """
```

### Phase 2: Integration Tests (Non-Docker) - Staging Environment Validation

**Objective**: Validate staging environment connectivity without Docker dependencies

#### 2.1 Staging Environment Connectivity Tests

**File**: `tests/integration/issue_605/test_staging_websocket_infrastructure.py`

**Test Cases**:
```python
class TestStagingWebSocketInfrastructure(SSotBaseTestCase):
    """Integration tests for staging WebSocket infrastructure without Docker."""
    
    @pytest.mark.staging
    async def test_staging_websocket_connection_establishment(self):
        """
        FAILING TEST: Test basic WebSocket connection to staging environment.
        
        Expected to FAIL initially due to infrastructure issues.
        """
        
    @pytest.mark.staging  
    async def test_staging_authentication_header_preservation(self):
        """
        FAILING TEST: Test that staging environment preserves auth headers.
        
        Expected to FAIL due to GCP Load Balancer configuration.
        """
        
    @pytest.mark.staging
    async def test_staging_websocket_cold_start_timing(self):
        """
        FAILING TEST: Test WebSocket connection during GCP cold start scenarios.
        
        Expected to FAIL due to cold start timing issues.
        """
```

#### 2.2 WebSocket Event Delivery Integration Tests

**File**: `tests/integration/issue_605/test_websocket_event_delivery_staging.py`

**Test Cases**:
```python
class TestWebSocketEventDeliveryStaging(SSotBaseTestCase):
    """Integration tests for WebSocket event delivery in staging environment."""
    
    @pytest.mark.staging
    async def test_agent_events_delivery_during_cold_start(self):
        """
        FAILING TEST: Test agent events delivery during GCP cold start.
        
        Expected to FAIL due to cold start WebSocket timing issues.
        """
        
    @pytest.mark.staging
    async def test_websocket_event_sequence_completeness(self):
        """
        FAILING TEST: Test complete WebSocket event sequence delivery.
        
        Expected to FAIL due to missing events during cold start.
        """
        
    @pytest.mark.staging
    async def test_concurrent_user_websocket_isolation(self):
        """
        FAILING TEST: Test WebSocket isolation during concurrent cold starts.
        
        Expected to FAIL due to race conditions.
        """
```

#### 2.3 JSON Parsing and GCP Connectivity Tests

**File**: `tests/integration/issue_605/test_gcp_connectivity_parsing.py`

**Test Cases**:
```python  
class TestGCPConnectivityParsing(SSotBaseTestCase):
    """Integration tests for GCP connectivity and JSON parsing issues."""
    
    @pytest.mark.staging
    async def test_gcp_load_balancer_json_response_parsing(self):
        """
        FAILING TEST: Test JSON parsing from GCP Load Balancer responses.
        
        Expected to FAIL due to malformed JSON from load balancer.
        """
        
    @pytest.mark.staging
    async def test_gcp_cloud_run_websocket_upgrade_handling(self):
        """
        FAILING TEST: Test WebSocket upgrade handling through GCP Cloud Run.
        
        Expected to FAIL due to upgrade header issues.
        """
        
    @pytest.mark.staging  
    def test_gcp_staging_environment_configuration(self):
        """
        TEST: Validate GCP staging environment configuration for WebSocket.
        
        This should PASS and document current configuration.
        """
```

### Phase 3: E2E Tests (GCP Staging) - Golden Path Validation

**Objective**: End-to-end validation of complete Golden Path user flow during GCP cold start scenarios

#### 3.1 Golden Path WebSocket Cold Start Tests

**File**: `tests/e2e/issue_605/test_golden_path_websocket_cold_start_e2e.py`

**Test Cases**:
```python
class TestGoldenPathWebSocketColdStartE2E(StagingTestBase):
    """E2E tests for Golden Path user flow during GCP cold start scenarios."""
    
    @track_test_timing
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_golden_path_user_login_websocket_cold_start(self):
        """
        FAILING TEST: Complete Golden Path user flow during cold start.
        
        Flow: Login → WebSocket Connect → Agent Execution → AI Response
        Expected to FAIL due to cold start WebSocket timing issues.
        """
        
    @track_test_timing  
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_golden_path_websocket_events_during_cold_start(self):
        """
        FAILING TEST: Test all 5 WebSocket events during cold start.
        
        Events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
        Expected to FAIL due to event delivery timing issues.
        """
        
    @track_test_timing
    @pytest.mark.staging  
    @pytest.mark.e2e
    async def test_golden_path_multi_user_cold_start_isolation(self):
        """
        FAILING TEST: Test multi-user Golden Path during simultaneous cold starts.
        
        Expected to FAIL due to user isolation issues during cold start.
        """
```

#### 3.2 WebSocket Infrastructure Recovery Tests

**File**: `tests/e2e/issue_605/test_websocket_infrastructure_recovery_e2e.py`

**Test Cases**:
```python
class TestWebSocketInfrastructureRecoveryE2E(StagingTestBase):
    """E2E tests for WebSocket infrastructure recovery patterns."""
    
    @track_test_timing
    @pytest.mark.staging
    @pytest.mark.e2e  
    async def test_websocket_recovery_after_cold_start_failure(self):
        """
        FAILING TEST: Test WebSocket recovery after cold start connection failure.
        
        Expected to FAIL initially, should pass after recovery mechanisms implemented.
        """
        
    @track_test_timing
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_websocket_graceful_degradation_cold_start(self):
        """
        FAILING TEST: Test graceful degradation during cold start issues.
        
        Expected to FAIL initially due to lack of degradation mechanisms.
        """
        
    @track_test_timing  
    @pytest.mark.staging
    @pytest.mark.e2e
    async def test_websocket_reconnection_after_gcp_infrastructure_issue(self):
        """
        FAILING TEST: Test WebSocket reconnection after GCP infrastructure issues.
        
        Expected to FAIL due to missing reconnection logic.
        """
```

#### 3.3 Performance and Scalability E2E Tests  

**File**: `tests/e2e/issue_605/test_websocket_cold_start_performance_e2e.py`

**Test Cases**:
```python
class TestWebSocketColdStartPerformanceE2E(StagingTestBase):
    """E2E performance tests for WebSocket cold start scenarios."""
    
    @track_test_timing
    @pytest.mark.staging
    @pytest.mark.performance
    async def test_websocket_cold_start_performance_benchmarks(self):
        """
        FAILING TEST: Benchmark WebSocket connection times during cold start.
        
        Expected to FAIL due to excessive cold start connection times.
        """
        
    @track_test_timing
    @pytest.mark.staging  
    @pytest.mark.performance
    async def test_websocket_scalability_during_concurrent_cold_starts(self):
        """
        FAILING TEST: Test WebSocket scalability during concurrent cold starts.
        
        Expected to FAIL due to resource contention during cold starts.
        """
        
    @track_test_timing
    @pytest.mark.staging
    @pytest.mark.performance  
    async def test_websocket_memory_usage_during_cold_start(self):
        """
        FAILING TEST: Monitor memory usage during WebSocket cold start scenarios.
        
        Expected to FAIL due to memory leaks or excessive usage.
        """
```

## Test Infrastructure Requirements

### Unit Test Infrastructure

**Dependencies**:
- `test_framework.ssot.base_test_case.SSotBaseTestCase`
- Mock WebSocket connections (for API testing only)
- asyncio event loop testing utilities

**Configuration**:
- No external service dependencies
- Fast execution (< 1 second per test)
- Isolated environment testing

### Integration Test Infrastructure

**Dependencies**:
- Staging environment connectivity
- Real WebSocket connections to staging
- GCP staging configuration
- Authentication token generation

**Configuration**:  
- Staging environment variables loaded
- Network connectivity to GCP staging
- JWT/OAuth authentication configured
- Timeout handling for staging connectivity

### E2E Test Infrastructure

**Dependencies**:
- Full staging environment (GCP Cloud Run, Load Balancer, etc.)
- Real user authentication
- Complete Golden Path flow
- WebSocket event monitoring

**Configuration**:
- `@track_test_timing` decorator for 0-second test prevention
- Real service connections (no mocks)
- Complete user authentication flow
- Full WebSocket event sequence validation

## Success Metrics

### Unit Test Success Metrics

- **API Compatibility**: 100% of WebSocket API compatibility tests documented
- **Inheritance Issues**: Clear identification of base class conflicts
- **Header Validation**: Complete documentation of GCP header requirements

### Integration Test Success Metrics  

- **Staging Connectivity**: Successful connection to staging WebSocket endpoints
- **Authentication**: Headers properly preserved through GCP Load Balancer
- **Event Delivery**: Complete WebSocket event sequence delivered
- **Cold Start Timing**: Measurable improvement in cold start connection times

### E2E Test Success Metrics

- **Golden Path**: 100% Golden Path user flow success during cold start
- **WebSocket Events**: All 5 critical events delivered during cold start scenarios  
- **Multi-User**: Proper user isolation during concurrent cold starts
- **Performance**: Cold start WebSocket connection < 5 seconds
- **Recovery**: Successful WebSocket recovery after infrastructure failures

## Implementation Order

### Phase 1: Unit Tests (Week 1)
1. Create unit test directory structure
2. Implement WebSocket API compatibility tests  
3. Implement staging test base inheritance tests
4. Implement GCP header validation tests
5. Run tests and document failures

### Phase 2: Integration Tests (Week 2)  
1. Implement staging WebSocket infrastructure tests
2. Implement WebSocket event delivery tests
3. Implement GCP connectivity parsing tests
4. Validate staging environment configuration
5. Run tests and document infrastructure issues

### Phase 3: E2E Tests (Week 3)
1. Implement Golden Path cold start E2E tests
2. Implement WebSocket infrastructure recovery tests  
3. Implement performance and scalability tests
4. Full test suite execution in staging environment
5. Performance benchmarking and optimization

### Phase 4: Issue Resolution (Week 4)
1. Fix WebSocket API compatibility issues
2. Resolve GCP Load Balancer configuration  
3. Implement cold start optimization
4. Validate all tests pass
5. Update success rate from 20% to 95%+

## Risk Mitigation

### Technical Risks
- **Staging Environment Downtime**: Implement graceful degradation testing
- **GCP Configuration Changes**: Version control infrastructure configurations
- **WebSocket Library Updates**: Pin library versions and test compatibility matrix

### Business Risks  
- **Golden Path Failures**: Prioritize critical user flow tests
- **Production Impact**: Never deploy failing WebSocket infrastructure
- **Customer Experience**: Monitor WebSocket performance metrics continuously

## Documentation Updates

### Test Documentation
- Update `DEFINITION_OF_DONE_CHECKLIST.md` with Issue #605 test requirements  
- Document WebSocket API compatibility matrix
- Create GCP staging environment configuration guide

### GitHub Issue Updates
- Update Issue #605 with detailed test plan
- Link to test files and success metrics
- Track progress through test implementation phases

## Conclusion

This comprehensive test plan addresses Issue #605 through systematic validation of WebSocket E2E test infrastructure. The "failing tests first" approach ensures we identify and prove all issues before implementing fixes, protecting the $500K+ ARR business value dependent on reliable chat functionality.

The phased approach allows incremental progress validation while building towards complete Golden Path user flow reliability during GCP cold start scenarios.