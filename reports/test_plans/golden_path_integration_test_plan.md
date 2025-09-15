# Golden Path Integration Test Plan - Non-Docker Focus
**Created:** 2025-09-13 | **Agent Session:** agent-session-2025-09-13-1500 | **Issue:** #862

## Executive Summary

**Mission**: Increase Golden Path integration test coverage from 15.3% to 55%+ within 4 weeks to protect $500K+ ARR through comprehensive non-Docker integration testing.

**Strategy**: Focus on integration tests that validate real service interactions without Docker dependencies, using GCP staging environment and localhost services for reliable CI/CD execution.

## Priority P0: WebSocket Infrastructure Integration Tests

### Current State: 18.2% coverage → Target: 65% coverage

#### Test Suite 1: WebSocket Connection Lifecycle
**File**: `tests/integration/golden_path/test_websocket_connection_lifecycle_integration.py`

**Test Scenarios:**
- [ ] **Connection establishment flow**
  - WebSocket handshake with JWT authentication
  - User context creation and isolation
  - Connection state management
- [ ] **Multi-user concurrent connections**
  - 10+ simultaneous users with complete isolation
  - Resource allocation and cleanup per user
  - Connection state independence
- [ ] **Graceful disconnection and cleanup**
  - Proper resource cleanup on disconnect
  - State persistence for reconnection
  - Error handling for abrupt disconnections

#### Test Suite 2: Real-Time Event Delivery Integration
**File**: `tests/integration/golden_path/test_websocket_event_delivery_integration.py`

**Test Scenarios:**
- [ ] **All 5 critical events delivery**
  - `agent_started`: Verify emission when agent begins
  - `agent_thinking`: Validate real-time reasoning updates
  - `tool_executing`: Confirm tool usage transparency
  - `tool_completed`: Verify tool results delivery
  - `agent_completed`: Validate completion notification
- [ ] **Event ordering and timing validation**
  - Correct chronological sequence
  - Performance SLA compliance (events within 5s)
  - Event delivery confirmation system
- [ ] **Multi-user event isolation**
  - Events delivered only to correct users
  - No cross-user event pollution
  - Concurrent event handling

#### Test Suite 3: Authentication Integration Flow
**File**: `tests/integration/golden_path/test_websocket_auth_integration.py`

**Test Scenarios:**
- [ ] **JWT validation with auth service**
  - Real JWT token validation (no mocks)
  - Token refresh and expiration handling
  - Invalid token rejection
- [ ] **User context lifecycle**
  - Context creation from JWT claims
  - Context isolation between users
  - Context cleanup on disconnect
- [ ] **Session management**
  - Session persistence across reconnections
  - Session data integrity
  - Multi-device session handling

## Priority P0: Agent System Integration Tests

### Current State: 12.1% coverage → Target: 55% coverage

#### Test Suite 4: Complete Agent Pipeline Integration
**File**: `tests/integration/golden_path/test_agent_pipeline_integration.py`

**Test Scenarios:**
- [ ] **End-to-end agent workflow**
  - User message → Triage Agent → Data Agent → Optimization Agent → Report Agent
  - Agent handoff validation with state persistence
  - Workflow completion and result compilation
- [ ] **Multi-user agent execution isolation**
  - Concurrent agent executions for different users
  - Resource limits and enforcement per user
  - Agent state isolation and cleanup
- [ ] **Agent error handling and recovery**
  - Agent failure detection and notification
  - Partial result preservation
  - Graceful degradation mechanisms

#### Test Suite 5: WebSocket-Agent Bridge Integration
**File**: `tests/integration/golden_path/test_websocket_agent_bridge_integration.py`

**Test Scenarios:**
- [ ] **Agent execution with real-time events**
  - Agent workflow triggering WebSocket events
  - Event emission during agent processing
  - Agent state synchronization with WebSocket
- [ ] **Agent error propagation**
  - Agent errors communicated via WebSocket
  - Error context and recovery options
  - User notification and feedback
- [ ] **Performance integration**
  - Agent execution performance monitoring
  - WebSocket event delivery performance
  - Resource usage tracking

#### Test Suite 6: Tool Integration Pipeline
**File**: `tests/integration/golden_path/test_tool_integration_pipeline.py`

**Test Scenarios:**
- [ ] **Tool discovery and execution**
  - Tool availability validation
  - Tool execution with real services
  - Tool result processing and formatting
- [ ] **Tool error handling**
  - Tool execution failures
  - Timeout and retry mechanisms
  - Fallback tool selection
- [ ] **Tool-WebSocket integration**
  - Tool execution events via WebSocket
  - Tool result delivery to users
  - Tool performance monitoring

## Priority P1: Services Integration Tests

### Current State: 16.5% coverage → Target: 50% coverage

#### Test Suite 7: Authentication Service Integration
**File**: `tests/integration/golden_path/test_auth_service_integration.py`

**Test Scenarios:**
- [ ] **Complete authentication flow**
  - User login with OAuth/JWT
  - Token validation and refresh
  - Multi-tenant isolation
- [ ] **JWT lifecycle management**
  - Token creation and validation
  - Token refresh mechanisms
  - Token revocation and cleanup
- [ ] **Cross-service authentication**
  - Auth service → WebSocket → Agent pipeline
  - Consistent user identity across services
  - Permission and role validation

#### Test Suite 8: Database Integration
**File**: `tests/integration/golden_path/test_database_integration.py`

**Test Scenarios:**
- [ ] **User data persistence**
  - User data storage and retrieval
  - Data integrity and validation
  - Multi-user data isolation
- [ ] **Transaction management**
  - ACID transaction compliance
  - Rollback scenarios and recovery
  - Concurrent access handling
- [ ] **State persistence**
  - Conversation state management
  - Agent execution state persistence
  - Session data consistency

#### Test Suite 9: State Persistence Integration
**File**: `tests/integration/golden_path/test_state_persistence_integration.py`

**Test Scenarios:**
- [ ] **Conversation management**
  - Conversation thread persistence
  - Message history and retrieval
  - Thread state across sessions
- [ ] **Agent execution state**
  - Agent progress persistence
  - Partial result storage
  - Recovery from interruptions
- [ ] **Resource cleanup**
  - State cleanup on user disconnect
  - Resource deallocation
  - Memory leak prevention

## Implementation Strategy

### Non-Docker Test Architecture

#### 1. GCP Staging Integration
- **Purpose**: End-to-end validation with production-like environment
- **Services**: Real GCP services (Cloud Run, Cloud SQL, Redis)
- **Authentication**: Real OAuth/JWT flows
- **Benefits**: Most realistic testing environment

#### 2. Local Service Integration
- **Purpose**: Fast feedback loops during development
- **Services**: Local backend, auth service, databases
- **Connections**: Real HTTP/WebSocket connections to localhost
- **Benefits**: Rapid iteration and debugging

#### 3. Controlled External Mocking
- **Purpose**: Isolate external dependencies while keeping core services real
- **Mock**: LLM APIs, payment services, external notifications
- **Real**: Backend, auth, database, WebSocket, agent system
- **Benefits**: Reliable tests without external service dependencies

### Test Infrastructure Requirements

#### Base Test Class
```python
class GoldenPathIntegrationTestCase(SSotAsyncTestCase):
    """Base class for golden path integration tests."""

    async def asyncSetUp(self):
        """Set up real services for integration testing."""
        # Initialize real database connections
        # Set up WebSocket test client
        # Configure authentication for testing
        # Prepare test data isolation

    async def asyncTearDown(self):
        """Clean up resources after test."""
        # Close database connections
        # Clean up test data
        # Disconnect WebSocket clients
        # Reset service states
```

#### Performance SLA Enforcement
- **WebSocket Connection**: ≤2s establishment time
- **First Event Delivery**: ≤5s from agent start
- **Complete Agent Pipeline**: ≤60s total execution
- **Database Operations**: ≤1s for standard queries
- **Memory Usage**: ≤500MB per user session

#### Error Scenario Coverage
- **Network failures**: Connection drops, timeouts
- **Service failures**: Auth service down, database unavailable
- **Data corruption**: Invalid messages, malformed requests
- **Resource exhaustion**: Memory limits, connection limits
- **Concurrent access**: Race conditions, deadlocks

### Test Execution Strategy

#### Phase 1 (Week 1-2): WebSocket Infrastructure
1. **Test Suite 1**: Connection lifecycle integration
2. **Test Suite 2**: Event delivery integration
3. **Test Suite 3**: Authentication integration
4. **Target**: 65% WebSocket infrastructure coverage

#### Phase 2 (Week 2-3): Agent System Integration
1. **Test Suite 4**: Agent pipeline integration
2. **Test Suite 5**: WebSocket-Agent bridge integration
3. **Test Suite 6**: Tool integration pipeline
4. **Target**: 55% Agent system coverage

#### Phase 3 (Week 3-4): Services Integration
1. **Test Suite 7**: Authentication service integration
2. **Test Suite 8**: Database integration
3. **Test Suite 9**: State persistence integration
4. **Target**: 50% Services layer coverage

#### Phase 4 (Week 4): Validation & Optimization
1. **End-to-end validation**: Complete golden path flows
2. **Performance optimization**: SLA compliance validation
3. **Error scenario testing**: Comprehensive failure scenarios
4. **Target**: 55%+ overall golden path coverage

## Success Metrics

### Coverage Targets
- **WebSocket Infrastructure**: 22,458+ lines protected (65% of 34,551)
- **Agent Orchestration**: 46,750+ lines protected (55% of 85,000)
- **Services Layer**: 27,500+ lines protected (50% of 55,000)
- **Total Protection**: 96,708+ lines validated

### Business Value Protection
- **$500K+ ARR Validation**: Complete user journey reliability
- **Multi-User Scalability**: 10+ concurrent users with isolation
- **Real-Time Experience**: WebSocket event SLA compliance
- **System Resilience**: Comprehensive error handling validation
- **Performance Assurance**: Response time threshold enforcement

### Quality Assurance
- **Test Reliability**: ≥95% test pass rate
- **Test Coverage**: ≥55% golden path integration coverage
- **Performance Compliance**: 100% SLA adherence
- **Error Handling**: 100% error scenario coverage
- **Documentation**: Complete test documentation and runbooks

## Risk Mitigation

### Technical Risks
- **Service Dependencies**: Use staging environment as fallback
- **Test Flakiness**: Implement retry mechanisms and timeouts
- **Resource Constraints**: Implement resource cleanup and limits
- **Performance Issues**: Monitor and optimize continuously

### Business Risks
- **Revenue Impact**: Prioritize P0 critical paths first
- **User Experience**: Focus on real-time and performance aspects
- **System Stability**: Validate error handling thoroughly
- **Scalability**: Test concurrent user scenarios extensively

---

**Implementation Start**: Week of 2025-09-16
**Completion Target**: Week of 2025-10-14
**Business Impact**: Protect $500K+ ARR through comprehensive golden path validation
**Strategic Priority**: P0 - Critical revenue protection and user experience reliability