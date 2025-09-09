# WebSocket Race Condition Comprehensive Test Plan

**MISSION CRITICAL: $500K+ ARR Chat Functionality Protection**

## Executive Summary

This test plan addresses WebSocket race condition failures identified through Five Whys analysis that impact core chat functionality. The root causes stem from incomplete WebSocket lifecycle management in GCP Cloud Run environments, causing systematic failures every 2-3 minutes that break the primary business value delivery mechanism.

## Business Context

**Revenue Impact**: $500K+ ARR at risk due to chat functionality failures  
**User Impact**: WebSocket connection failures prevent real-time AI interactions  
**Root Cause**: Incomplete WebSocket lifecycle management in GCP staging environment  
**Unified Root Cause**: GCP Cloud Run timing gaps between network handshake and application state readiness

## Identified Root Causes & Test Strategy

### Root Cause 1: Connection State Race Condition
**Symptom**: "Need to call 'accept' first" errors every 2-3 minutes  
**Technical Root**: GCP Cloud Run timing gaps between local WebSocket state changes and network handshake completion

### Root Cause 2: MessageHandlerService Constructor Mismatch  
**Symptom**: "unexpected keyword argument 'websocket_manager'" errors  
**Technical Root**: Multiple WebSocket initialization patterns with different parameter signatures violating SSOT

### Root Cause 3: GCP Readiness Validation Failures
**Symptom**: 22+ second validation timeouts, connections rejected  
**Technical Root**: Readiness validation logic not calibrated for staging environment infrastructure

### Root Cause 4: Systematic Heartbeat Timeouts
**Symptom**: Every 2-minute heartbeat failures  
**Technical Root**: Misalignment between GCP infrastructure settings and application heartbeat config

### Root Cause 5: Connection Response Send Failures
**Symptom**: "Failed to send connection response" warnings  
**Technical Root**: Incomplete bidirectional handshake validation allows operations before full send/receive capability

## Test Suite Architecture

### Testing Requirements Compliance
- **ALL e2e tests MUST use real authentication** (JWT/OAuth) per CLAUDE.md Section 15 mandate
- **NO mocks in integration/e2e tests** - use real services only  
- **Docker services automatically managed** by UnifiedDockerManager
- **Alpine containers by default** for 50% faster execution
- **User context isolation** using Factory pattern from USER_CONTEXT_ARCHITECTURE.md

### Test Infrastructure Dependencies
- PostgreSQL (Test: 5434, Dev: 5432) 
- Redis (Test: 6381, Dev: 6379)
- Backend Service (8000)
- Auth Service (8081)
- Real LLM APIs for E2E tests
- GCP Cloud Run staging environment

## Detailed Test Plan

## 1. UNIT TESTS (15-20 tests total)

### 1.1 WebSocket Accept Timing Validation Tests (5 tests)

**File**: `/netra_backend/tests/unit/websocket_race_conditions/test_accept_timing_validation.py`

**Test Cases**:

1. **`test_accept_call_timing_validation`**
   - Validates WebSocket accept() is called before any message operations
   - Uses mock WebSocket to simulate timing violations
   - Expected Result: Exception raised when operations attempted before accept()

2. **`test_connection_state_transition_timing`** 
   - Tests connection state machine transitions under rapid timing changes
   - Simulates GCP Cloud Run network timing variations
   - Expected Result: State transitions maintain consistency regardless of timing

3. **`test_accept_with_concurrent_operations`**
   - Tests accept() call protection against concurrent message operations
   - Uses threading to simulate race conditions
   - Expected Result: Operations queue properly until accept() completes

4. **`test_gcp_network_handshake_simulation`**
   - Simulates GCP-specific network handshake delays
   - Tests local state vs network state synchronization
   - Expected Result: Local state waits for network handshake confirmation

5. **`test_accept_timeout_handling`**
   - Tests behavior when accept() call times out in Cloud Run
   - Validates proper error handling and connection cleanup
   - Expected Result: Clean failure without resource leaks

### 1.2 MessageHandlerService Constructor Tests (4 tests)

**File**: `/netra_backend/tests/unit/websocket_race_conditions/test_message_handler_constructor.py`

1. **`test_constructor_parameter_validation`**
   - Tests all valid constructor parameter combinations
   - Validates SSOT parameter signature consistency
   - Expected Result: All valid combinations succeed

2. **`test_invalid_parameter_combinations`**
   - Tests invalid parameter combinations that cause constructor failures
   - Validates proper error messages for debugging
   - Expected Result: Clear error messages for invalid combinations

3. **`test_websocket_manager_injection`**
   - Tests WebSocket manager parameter injection patterns
   - Validates factory pattern consistency
   - Expected Result: Proper manager injection without signature violations

4. **`test_constructor_race_condition_prevention`**
   - Tests constructor parameter validation under concurrent initialization
   - Simulates multiple service initialization attempts
   - Expected Result: Consistent parameter validation across concurrent calls

### 1.3 Bidirectional Handshake Validation Tests (3 tests)

**File**: `/netra_backend/tests/unit/websocket_race_conditions/test_bidirectional_handshake.py`

1. **`test_send_capability_validation`**
   - Tests WebSocket send capability before allowing operations
   - Validates send channel readiness
   - Expected Result: Operations blocked until send capability confirmed

2. **`test_receive_capability_validation`**
   - Tests WebSocket receive capability validation
   - Validates receive channel readiness before message processing
   - Expected Result: Message processing queued until receive ready

3. **`test_full_bidirectional_handshake`**
   - Tests complete bidirectional handshake validation
   - Validates both send and receive channels before operations
   - Expected Result: Operations only proceed after full bidirectional confirmation

### 1.4 Heartbeat Configuration Tests (3 tests)

**File**: `/netra_backend/tests/unit/websocket_race_conditions/test_heartbeat_timing.py`

1. **`test_gcp_heartbeat_configuration`**
   - Tests heartbeat timing configuration for GCP Cloud Run
   - Validates heartbeat intervals align with infrastructure limits
   - Expected Result: Heartbeat config within GCP NEG limits

2. **`test_heartbeat_timeout_calculation`**
   - Tests heartbeat timeout calculation logic
   - Validates timeout values prevent false positives
   - Expected Result: Timeouts account for GCP infrastructure delays

3. **`test_heartbeat_failure_recovery`**
   - Tests heartbeat failure detection and recovery
   - Validates connection recovery after heartbeat timeouts
   - Expected Result: Clean recovery without connection corruption

## 2. INTEGRATION TESTS (8-10 tests total)

### 2.1 WebSocket + Redis + Auth Integration Tests (4 tests)

**File**: `/netra_backend/tests/integration/websocket_race_conditions/test_websocket_redis_auth_integration.py`

1. **`test_websocket_redis_connection_race`**
   - Tests WebSocket connection with Redis state synchronization
   - Uses real Redis and WebSocket services
   - **AUTH REQUIRED**: Uses E2EAuthHelper for JWT authentication
   - Expected Result: WebSocket and Redis state remain synchronized

2. **`test_auth_validation_with_redis_delay`**
   - Tests authentication validation when Redis responses are delayed
   - Simulates Redis network delays common in Cloud Run
   - **AUTH REQUIRED**: Tests real JWT validation flow
   - Expected Result: Auth validation succeeds despite Redis delays

3. **`test_websocket_session_persistence`**
   - Tests WebSocket session persistence in Redis during connection issues
   - Validates session recovery after temporary disconnections
   - **AUTH REQUIRED**: Uses authenticated sessions
   - Expected Result: Sessions persist and recover properly

4. **`test_concurrent_user_isolation`**
   - Tests multi-user WebSocket connections with Redis state isolation
   - Validates user isolation during race conditions
   - **AUTH REQUIRED**: Multiple authenticated users
   - Expected Result: User state isolation maintained under load

### 2.2 Multi-User Isolation Tests (3 tests)

**File**: `/netra_backend/tests/integration/websocket_race_conditions/test_multi_user_isolation.py`

1. **`test_connection_id_isolation_under_race`**
   - Tests connection ID isolation during concurrent connections
   - Prevents connection ID mixups during race conditions
   - **AUTH REQUIRED**: Multiple authenticated users
   - Expected Result: Each user gets unique connection ID

2. **`test_message_routing_isolation`**
   - Tests message routing isolation during race conditions
   - Validates messages reach correct users
   - **AUTH REQUIRED**: Multiple authenticated users  
   - Expected Result: No message cross-contamination

3. **`test_state_machine_isolation`**
   - Tests WebSocket state machine isolation per user
   - Validates state machines don't interfere with each other
   - **AUTH REQUIRED**: Multiple authenticated users
   - Expected Result: Independent state machine progression

### 2.3 Agent Event Delivery Integration Tests (3 tests)

**File**: `/netra_backend/tests/integration/websocket_race_conditions/test_agent_event_delivery.py`

1. **`test_agent_events_during_race_conditions`**
   - Tests all 5 required agent events during WebSocket race conditions
   - Validates: agent_started, agent_thinking, tool_executing, tool_completed, agent_completed
   - **AUTH REQUIRED**: Uses authenticated agent execution context
   - Expected Result: All agent events delivered despite race conditions

2. **`test_event_ordering_during_handshake_delay`**
   - Tests event ordering when handshake is delayed
   - Validates events queue and deliver in correct order
   - **AUTH REQUIRED**: Uses authenticated WebSocket connection
   - Expected Result: Event ordering preserved during delays

3. **`test_event_delivery_timeout_handling`**
   - Tests event delivery when WebSocket is temporarily unavailable
   - Validates event queuing and retry mechanisms
   - **AUTH REQUIRED**: Uses authenticated connection
   - Expected Result: Events eventually delivered after connection recovery

## 3. E2E GCP STAGING TESTS (5-8 tests total)

### 3.1 Real GCP Cloud Run Environment Tests (4 tests)

**File**: `/tests/e2e/gcp_staging/test_websocket_race_conditions.py`

1. **`test_real_user_websocket_connection_gcp`**
   - Tests real user WebSocket connections in actual GCP Cloud Run
   - Uses staging environment with real infrastructure delays
   - **AUTH REQUIRED**: Real OAuth flow with staging credentials
   - Expected Result: Connections succeed within 15-second GCP NEG limits

2. **`test_agent_execution_websocket_events_staging`**
   - Tests complete agent execution with WebSocket events in staging
   - Validates all 5 agent events reach real frontend
   - **AUTH REQUIRED**: Full staging authentication flow
   - Expected Result: Real chat interactions work end-to-end

3. **`test_connection_recovery_cloud_run`**
   - Tests connection recovery after GCP Cloud Run container cycling
   - Simulates container restarts and connection restoration
   - **AUTH REQUIRED**: Persistent authentication across restarts
   - Expected Result: Connections recover automatically

4. **`test_heartbeat_behavior_gcp_neg`**
   - Tests heartbeat behavior within GCP Network Endpoint Group limits
   - Validates heartbeat timing works with real GCP infrastructure
   - **AUTH REQUIRED**: Long-running authenticated connections
   - Expected Result: Heartbeats succeed consistently without timeouts

### 3.2 High-Concurrency Staging Tests (4 tests)

**File**: `/tests/e2e/gcp_staging/test_high_concurrency_race_conditions.py`

1. **`test_10_simultaneous_users_staging`**
   - Tests 10+ simultaneous WebSocket connections in staging
   - Validates system handles concurrent load
   - **AUTH REQUIRED**: 10 authenticated users with real OAuth
   - Expected Result: All users get working chat connections

2. **`test_rapid_connect_disconnect_staging`**
   - Tests rapid connection cycling to trigger race conditions
   - Simulates real-world user behavior patterns
   - **AUTH REQUIRED**: Authenticated rapid connections
   - Expected Result: No connection state corruption

3. **`test_message_burst_during_handshake`**
   - Tests message bursts arriving during connection handshake
   - Validates message queuing and delivery
   - **AUTH REQUIRED**: Authenticated message sending
   - Expected Result: All messages delivered after handshake completion

4. **`test_staging_infrastructure_limits`**
   - Tests behavior at staging infrastructure limits
   - Validates graceful degradation under resource constraints
   - **AUTH REQUIRED**: Resource-intensive authenticated operations
   - Expected Result: Graceful handling of resource limits

## Test Difficulty Requirements

### Stress Tests (Intentionally Trigger Race Conditions)
- **Connection Storm Tests**: 50+ simultaneous connections within 1 second
- **Timing Manipulation Tests**: Artificial delays to trigger specific race windows
- **Resource Exhaustion Tests**: Push connections to infrastructure limits
- **Network Partition Tests**: Simulate GCP network delays and partitions

### Chaos Tests (Simulate GCP Infrastructure Issues)
- **Container Restart Tests**: Simulate GCP Cloud Run container cycling
- **Network Delay Tests**: Simulate GCP NEG delays and timeouts
- **Service Unavailability Tests**: Simulate dependent service failures
- **Authentication Service Delays**: Simulate OAuth provider delays

### Timing-Sensitive Tests (Millisecond-Level Validation)
- **Handshake Timing Tests**: Validate handshake completion within precise windows
- **Event Ordering Tests**: Validate event delivery order within millisecond precision
- **State Transition Tests**: Validate state machine timing consistency
- **Authentication Flow Timing**: Validate auth completion timing

## Implementation Approach

### Phase 1: Unit Tests (Week 1)
1. Create unit test files with SSOT-compliant structure
2. Implement WebSocket accept timing validation tests
3. Implement MessageHandlerService constructor tests
4. Implement bidirectional handshake validation tests
5. Implement heartbeat configuration tests

### Phase 2: Integration Tests (Week 2)  
1. Create integration test files using BaseIntegrationTest
2. Implement WebSocket + Redis + Auth integration tests with real services
3. Implement multi-user isolation tests with authenticated users
4. Implement agent event delivery integration tests
5. Validate all tests use E2EAuthHelper for authentication

### Phase 3: E2E Staging Tests (Week 3)
1. Create E2E test files for GCP staging environment
2. Implement real GCP Cloud Run environment tests
3. Implement high-concurrency staging tests
4. Configure staging environment OAuth credentials
5. Validate end-to-end chat functionality works

### Phase 4: Test Integration & CI/CD (Week 4)
1. Integrate all test suites with unified_test_runner.py
2. Configure Docker orchestration for test environments
3. Set up CI/CD pipeline with race condition test execution
4. Create test result reporting and failure analysis
5. Document test execution procedures

## Expected Failure Scenarios & Pass Criteria

### Unit Test Pass Criteria
- All WebSocket accept timing validations prevent operations before accept()
- All MessageHandlerService constructor combinations work correctly
- All bidirectional handshake validations prevent premature operations
- All heartbeat configurations align with GCP infrastructure limits

### Integration Test Pass Criteria  
- WebSocket + Redis + Auth integration maintains state consistency
- Multi-user isolation prevents cross-user contamination
- Agent event delivery works correctly during race conditions
- All tests authenticate properly using E2EAuthHelper

### E2E Staging Test Pass Criteria
- Real user WebSocket connections succeed in GCP Cloud Run within 15s
- Complete agent execution with all 5 WebSocket events delivered
- Connection recovery works after GCP container cycling
- High-concurrency tests (10+ users) succeed without failures

## Test Infrastructure Integration

### Existing Infrastructure Usage
- **Base Classes**: Use WebSocketIntegrationTest and BaseIntegrationTest
- **Authentication**: Use E2EAuthHelper for all authenticated connections
- **Docker Management**: Use UnifiedDockerManager for service orchestration
- **Test Configuration**: Follow TEST_ARCHITECTURE_VISUAL_OVERVIEW.md
- **Environment Isolation**: Use IsolatedEnvironment for test env management

### New Infrastructure Components
- **Race Condition Event Capture**: Track timing and race condition events
- **GCP Simulation Helpers**: Simulate Cloud Run specific behaviors
- **Concurrent Connection Managers**: Handle multiple simultaneous connections
- **Timing Validation Utilities**: Measure and validate millisecond-level timing

## Timeline & Priority

### Priority 1 (Critical - Week 1): Unit Tests
Focus on preventing the core race conditions at the component level

### Priority 2 (High - Week 2): Integration Tests  
Validate race condition fixes work across service boundaries

### Priority 3 (High - Week 3): E2E Staging Tests
Ensure fixes work in real GCP Cloud Run environment

### Priority 4 (Medium - Week 4): Test Infrastructure
Integrate with CI/CD and improve test execution automation

## Success Metrics

### Technical Metrics
- **Unit Test Coverage**: 100% of identified race condition scenarios
- **Integration Test Success**: 95%+ pass rate with real services
- **E2E Test Success**: 90%+ pass rate in staging environment
- **Race Condition Detection**: 0 race conditions detected in new tests

### Business Metrics
- **Chat Functionality Uptime**: 99.9%+ WebSocket connection success
- **User Experience**: No "connection failed" errors in staging
- **Agent Event Delivery**: 100% delivery rate of all 5 required events
- **Revenue Protection**: Maintain $500K+ ARR through reliable chat

## Risk Mitigation

### Technical Risks
- **Test Environment Instability**: Use Docker orchestration for consistent environments
- **GCP Staging Access**: Ensure proper OAuth credentials for staging tests
- **Race Condition Complexity**: Start with simple scenarios, add complexity gradually
- **Test Execution Time**: Use parallel execution and Alpine containers

### Business Risks  
- **Feature Development Delay**: Run tests in parallel with development
- **Staging Environment Impact**: Use dedicated test windows for disruptive tests
- **Resource Usage**: Monitor and limit resource-intensive test execution
- **False Positives**: Implement robust test validation to prevent false failures

This comprehensive test plan ensures complete coverage of WebSocket race condition scenarios while maintaining business value protection and following all SSOT compliance requirements from CLAUDE.md.