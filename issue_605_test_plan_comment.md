# Test Plan for Issue #605 - GCP Cold Start WebSocket E2E Test Infrastructure

## 🎯 Executive Summary

**Current Status**: 20% test success rate (1/5 tests passing)
**Target**: 95%+ test success rate 
**Business Impact**: Protect $500K+ ARR from WebSocket failures

## 🔍 Root Cause Analysis

Based on investigation, Issue #605 has three primary root causes:

### 1. **Event Loop API Incompatibility** 
- `websockets.connect()` timeout parameter incompatible with current asyncio event loop
- Modern WebSocket libraries expect different event loop patterns
- Causing coroutine "never awaited" warnings in test output

### 2. **Class Inheritance Mismatch**
- Tests inherit from `BaseE2ETest` instead of `StagingTestBase` 
- Missing async method compatibility between base classes
- Causing method resolution and execution issues

### 3. **GCP Infrastructure Issues**
- GCP Load Balancer stripping authentication headers (Authorization, X-E2E-Bypass)
- JSON parsing errors from GCP responses during cold start
- WebSocket connection timing issues during Cloud Run cold starts

## 🧪 Test Strategy: "FAILING TESTS FIRST"

**Philosophy**: Create tests that FAIL initially to prove issues exist, then pass after fixes are implemented.

## 📋 Phase 1: Unit Tests (Non-Docker)
**Objective**: Validate API compatibility in isolation

### Test Files to Create:

#### `tests/unit/issue_605/test_websocket_api_compatibility.py`
```python  
async def test_websockets_connect_timeout_parameter_compatibility(self):
    """FAILING TEST: Prove websockets.connect() timeout parameter incompatibility."""
    
async def test_asyncio_event_loop_websocket_compatibility(self):
    """FAILING TEST: Test asyncio event loop patterns with WebSocket connections."""
    
def test_websocket_library_version_compatibility_matrix(self):
    """TEST: Document WebSocket library compatibility matrix."""
```

#### `tests/unit/issue_605/test_staging_test_base_inheritance.py`
```python
def test_baseE2etest_vs_staging_test_base_inheritance_conflict(self):
    """FAILING TEST: Prove inheritance mismatch between BaseE2ETest and StagingTestBase."""
    
async def test_async_test_method_compatibility(self):
    """FAILING TEST: Test async method patterns in different base classes."""
```

#### `tests/unit/issue_605/test_gcp_header_validation.py`  
```python
def test_authorization_header_preservation_patterns(self):
    """TEST: Validate authorization header patterns for GCP."""
    
def test_e2e_bypass_header_validation(self):
    """TEST: Validate E2E bypass header patterns for staging."""
```

## 📋 Phase 2: Integration Tests (Non-Docker)
**Objective**: Validate staging environment connectivity

### Test Files to Create:

#### `tests/integration/issue_605/test_staging_websocket_infrastructure.py`
```python
@pytest.mark.staging
async def test_staging_websocket_connection_establishment(self):
    """FAILING TEST: Test basic WebSocket connection to staging."""
    
@pytest.mark.staging  
async def test_staging_authentication_header_preservation(self):
    """FAILING TEST: Test staging environment preserves auth headers."""
    
@pytest.mark.staging
async def test_staging_websocket_cold_start_timing(self):
    """FAILING TEST: Test WebSocket connection during GCP cold start."""
```

#### `tests/integration/issue_605/test_gcp_connectivity_parsing.py`
```python
@pytest.mark.staging
async def test_gcp_load_balancer_json_response_parsing(self):
    """FAILING TEST: Test JSON parsing from GCP Load Balancer responses."""
    
@pytest.mark.staging
async def test_gcp_cloud_run_websocket_upgrade_handling(self):
    """FAILING TEST: Test WebSocket upgrade handling through GCP Cloud Run."""
```

## 📋 Phase 3: E2E Tests (GCP Staging)
**Objective**: Complete Golden Path validation during cold start

### Test Files to Create:

#### `tests/e2e/issue_605/test_golden_path_websocket_cold_start_e2e.py`
```python
@track_test_timing
@pytest.mark.staging  
@pytest.mark.e2e
async def test_golden_path_user_login_websocket_cold_start(self):
    """FAILING TEST: Complete Golden Path user flow during cold start.
    Flow: Login → WebSocket Connect → Agent Execution → AI Response"""
    
@track_test_timing
@pytest.mark.staging
@pytest.mark.e2e  
async def test_golden_path_websocket_events_during_cold_start(self):
    """FAILING TEST: Test all 5 WebSocket events during cold start.
    Events: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed"""
```

#### `tests/e2e/issue_605/test_websocket_infrastructure_recovery_e2e.py`
```python
@track_test_timing
@pytest.mark.staging
@pytest.mark.e2e
async def test_websocket_recovery_after_cold_start_failure(self):
    """FAILING TEST: Test WebSocket recovery after cold start connection failure."""
    
@track_test_timing
@pytest.mark.staging  
@pytest.mark.e2e
async def test_websocket_graceful_degradation_cold_start(self):
    """FAILING TEST: Test graceful degradation during cold start issues."""
```

## 🎯 Success Metrics

### Unit Test Success
- **API Compatibility**: 100% of WebSocket API compatibility tests documented
- **Inheritance Issues**: Clear identification of base class conflicts  
- **Header Validation**: Complete GCP header requirements documentation

### Integration Test Success
- **Staging Connectivity**: Successful connection to staging WebSocket endpoints
- **Authentication**: Headers preserved through GCP Load Balancer
- **Event Delivery**: Complete WebSocket event sequence delivered
- **Cold Start Timing**: Measurable improvement in cold start connection times

### E2E Test Success  
- **Golden Path**: 100% Golden Path user flow success during cold start
- **WebSocket Events**: All 5 critical events delivered during cold start scenarios
- **Multi-User**: Proper user isolation during concurrent cold starts
- **Performance**: Cold start WebSocket connection < 5 seconds
- **Recovery**: Successful WebSocket recovery after infrastructure failures

## 📅 Implementation Timeline

### Week 1: Unit Tests
- Create unit test directory structure  
- Implement WebSocket API compatibility tests
- Document current failures and incompatibilities

### Week 2: Integration Tests
- Implement staging WebSocket infrastructure tests
- Validate staging environment configuration
- Document GCP Load Balancer issues

### Week 3: E2E Tests  
- Implement Golden Path cold start E2E tests
- Performance benchmarking and monitoring
- Full staging environment validation

### Week 4: Issue Resolution
- Fix WebSocket API compatibility issues
- Resolve GCP Load Balancer configuration
- Validate 95%+ test success rate achievement

## ⚠️ Critical Requirements

### Test Infrastructure  
- **No Docker Dependencies**: All tests must run without Docker to avoid Issue #420 conflicts
- **Real Services**: Integration and E2E tests must use real staging services  
- **0-Second Prevention**: All E2E tests must use `@track_test_timing` decorator
- **SSOT Compliance**: All tests inherit from `SSotBaseTestCase`

### Authentication
- **Real JWT**: All tests use real authentication as per CLAUDE.MD Section 7.3
- **E2E Bypass Headers**: Staging tests use proper E2E bypass patterns
- **Header Preservation**: Validate GCP Load Balancer preserves auth headers

### Business Value Protection
- **Golden Path Priority**: Focus on user login → AI response flow
- **WebSocket Events**: Ensure all 5 critical events are delivered  
- **Multi-User Isolation**: Prevent user contamination during cold starts
- **Performance Monitoring**: Track and optimize cold start times

## 📄 Deliverables

1. **Comprehensive Test Plan**: ✅ `TEST_PLAN_ISSUE_605.md` (Created)
2. **Unit Test Suite**: 3 test files covering API compatibility 
3. **Integration Test Suite**: 3 test files covering staging connectivity
4. **E2E Test Suite**: 3 test files covering Golden Path validation
5. **Performance Benchmarks**: Cold start timing and scalability metrics
6. **Documentation Updates**: DoD checklist and test execution guides

## 🔧 Next Steps

1. **Immediate**: Create unit test directory structure and first failing tests
2. **Week 1**: Complete unit test implementation and document failures
3. **Week 2**: Implement integration tests for staging environment  
4. **Week 3**: Create comprehensive E2E test suite for Golden Path
5. **Week 4**: Fix identified issues and achieve 95%+ test success rate

This test plan provides systematic validation of WebSocket E2E test infrastructure while protecting the business-critical Golden Path user experience during GCP cold start scenarios.

---

**Test Plan Document**: Complete test plan available at `TEST_PLAN_ISSUE_605.md`
**Implementation Status**: Ready to begin Phase 1 unit test implementation