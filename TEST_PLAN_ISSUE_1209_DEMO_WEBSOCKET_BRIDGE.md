# Test Plan: Issue #1209 - DemoWebSocketBridge Missing `is_connection_active` Method

**Issue**: DemoWebSocketBridge missing `is_connection_active` method causing AttributeError when UnifiedWebSocketEmitter tries to validate connections.

**Context**: The `UnifiedWebSocketEmitter` calls `self.manager.is_connection_active(self.user_id)` on line 388, but the `DemoWebSocketBridge` class in `/netra_backend/app/routes/demo_websocket.py` doesn't implement this method, causing an AttributeError during demo chat flows.

## 🎯 OBJECTIVES

1. **Create failing tests** that reproduce the exact issue
2. **Validate WebSocket event flow** from demo → agent execution → WebSocket events
3. **Ensure interface compliance** for DemoWebSocketBridge
4. **Test without Docker dependencies** (unit/integration only, or E2E on staging GCP)

## 📋 TEST STRATEGY

### 1. **UNIT TESTS** (High Priority)

#### Test File: `netra_backend/tests/unit/demo/test_demo_websocket_bridge_interface.py`

**Purpose**: Test DemoWebSocketBridge interface compliance and reproduce the exact AttributeError

**Test Cases**:

1. **test_demo_websocket_bridge_missing_is_connection_active_method**
   - **OBJECTIVE**: Reproduce the exact AttributeError from issue
   - **SETUP**: Create DemoWebSocketBridge instance without implementing `is_connection_active`
   - **ACTION**: Call UnifiedWebSocketEmitter with DemoWebSocketBridge as manager
   - **ASSERTION**: Verify AttributeError is raised with message "has no attribute 'is_connection_active'"
   - **STATUS**: MUST FAIL FIRST, then pass after fix

2. **test_demo_websocket_bridge_interface_compliance**
   - **OBJECTIVE**: Validate that DemoWebSocketBridge implements WebSocketProtocol interface
   - **SETUP**: Create DemoWebSocketBridge instance
   - **ACTION**: Check for required methods: `is_connection_active`, `get_connection_health`, etc.
   - **ASSERTION**: Verify all required methods exist and return expected types
   - **STATUS**: Should pass after implementing missing methods

3. **test_unified_websocket_emitter_demo_bridge_integration**
   - **OBJECTIVE**: Test UnifiedWebSocketEmitter integration with DemoWebSocketBridge
   - **SETUP**: Create DemoWebSocketBridge with implemented `is_connection_active`
   - **ACTION**: Create UnifiedWebSocketEmitter with demo bridge as manager
   - **ASSERTION**: Verify emitter can call `is_connection_active` without error
   - **STATUS**: Should pass after fix

4. **test_demo_websocket_bridge_connection_validation**
   - **OBJECTIVE**: Test connection state validation logic
   - **SETUP**: Create DemoWebSocketBridge with various connection states
   - **ACTION**: Call `is_connection_active` with different user IDs
   - **ASSERTION**: Verify correct boolean return based on connection state
   - **STATUS**: Should pass after implementing method

#### Test File: `netra_backend/tests/unit/demo/test_demo_websocket_adapter_compliance.py`

**Purpose**: Test the inner WebSocketAdapter class compliance with expected interface

**Test Cases**:

1. **test_websocket_adapter_all_event_methods**
   - Verify all 5 critical WebSocket events are implemented:
     - `notify_agent_started`
     - `notify_agent_thinking`
     - `notify_tool_executing`
     - `notify_tool_completed`
     - `notify_agent_completed`

2. **test_websocket_adapter_event_data_structure**
   - Verify events have correct data structure with timestamp, type, etc.

### 2. **INTEGRATION TESTS** (Medium Priority)

#### Test File: `netra_backend/tests/integration/demo/test_demo_websocket_events_flow.py`

**Purpose**: Test complete demo chat flow end-to-end without Docker dependencies

**Test Cases**:

1. **test_demo_chat_flow_websocket_events_integration**
   - **OBJECTIVE**: Validate complete demo flow from request to WebSocket events
   - **SETUP**: Mock FastAPI WebSocket and demo endpoint
   - **ACTION**: Send chat message through demo endpoint
   - **ASSERTION**: Verify all 5 critical events are emitted in correct sequence
   - **ISOLATION**: No Docker, use mock databases/LLM

2. **test_demo_websocket_bridge_agent_execution_integration**
   - **OBJECTIVE**: Test demo bridge integration with real agent execution
   - **SETUP**: Create demo bridge with mock supervisor agent
   - **ACTION**: Execute agent workflow through demo bridge
   - **ASSERTION**: Verify WebSocket events are triggered during agent execution
   - **ISOLATION**: Use test database, mock LLM

3. **test_demo_websocket_bridge_error_handling**
   - **OBJECTIVE**: Test error handling when WebSocket connection fails
   - **SETUP**: Create demo bridge with simulated connection failures
   - **ACTION**: Attempt agent execution with failing WebSocket
   - **ASSERTION**: Verify proper error handling and recovery mechanisms

### 3. **E2E STAGING TESTS** (If needed)

#### Test File: `tests/e2e/staging/test_demo_websocket_bridge_staging.py`

**Purpose**: Test actual demo endpoint with real WebSocket events on staging GCP

**Test Cases**:

1. **test_staging_demo_websocket_connection**
   - **OBJECTIVE**: Validate real demo WebSocket endpoint on staging
   - **SETUP**: Connect to staging demo WebSocket endpoint
   - **ACTION**: Send test chat message
   - **ASSERTION**: Verify all events received and connection remains stable

## 🔧 IMPLEMENTATION REQUIREMENTS

### Test Infrastructure Setup

```python
# Base test class following SSOT patterns
from test_framework.ssot.base_test_case import SSotBaseTestCase
from test_framework.ssot.mock_factory import SSotMockFactory

class DemoWebSocketBridgeTestBase(SSotBaseTestCase):
    """Base class for demo WebSocket bridge tests."""

    async def asyncSetUp(self):
        await super().asyncSetUp()
        self.mock_factory = SSotMockFactory()
        self.demo_bridge = None
        self.mock_websocket = None

    def create_demo_websocket_bridge(self, has_is_connection_active=False):
        """Create DemoWebSocketBridge for testing."""
        # Implementation details...

    def create_mock_websocket(self):
        """Create mock WebSocket for testing."""
        # Implementation details...
```

### Mock Objects Required

1. **MockDemoWebSocketBridge**: Simulate missing `is_connection_active` method
2. **MockWebSocketAdapter**: Test the inner adapter class
3. **MockUnifiedWebSocketEmitter**: Verify calls to manager methods
4. **MockSupervisorAgent**: Test agent execution integration
5. **MockUserExecutionContext**: Provide test context data

### Test Data Setup

```python
# Test user context for demo scenarios
DEMO_TEST_CONTEXT = {
    'user_id': 'demo_user_test_001',
    'thread_id': 'demo_thread_001',
    'run_id': 'demo_run_001',
    'request_id': 'demo_req_001',
    'demo_mode': True
}

# Expected WebSocket events for validation
EXPECTED_DEMO_EVENTS = [
    'agent_started',
    'agent_thinking',
    'tool_executing',
    'tool_completed',
    'agent_completed'
]
```

## ✅ SUCCESS CRITERIA

### Tests Must:

1. **REPRODUCE THE ISSUE**:
   - At least one test must fail with the exact AttributeError: `'DemoWebSocketBridge' object has no attribute 'is_connection_active'`

2. **VALIDATE THE FIX**:
   - All tests pass after implementing the missing `is_connection_active` method
   - Method returns appropriate boolean based on connection state

3. **PREVENT REGRESSION**:
   - Tests catch if method is accidentally removed
   - Tests validate return type and behavior

4. **INTERFACE COMPLIANCE**:
   - Verify DemoWebSocketBridge implements all required WebSocket manager methods
   - Validate compatibility with UnifiedWebSocketEmitter expectations

### Test Execution Requirements:

- **Unit Tests**: Run without Docker dependencies
- **Integration Tests**: Use test database, mock LLM calls
- **E2E Tests**: Only on staging GCP if absolutely necessary
- **All Tests**: Follow SSOT test infrastructure patterns

## 🎯 BUSINESS VALUE VALIDATION

These tests protect **$500K+ ARR** by ensuring:

1. **Demo Experience**: Potential customers can experience chat functionality
2. **Agent Events**: All 5 critical WebSocket events work in demo mode
3. **Interface Stability**: Demo bridge stays compatible with core WebSocket infrastructure
4. **Error Prevention**: Catch interface compliance issues before production

## 📊 TEST METRICS

- **Target Coverage**: 100% of DemoWebSocketBridge interface methods
- **Critical Events**: 100% validation of all 5 WebSocket events
- **Error Scenarios**: 95% coverage of error handling paths
- **Integration Points**: 100% validation of agent-WebSocket coordination

## 🔄 EXECUTION PLAN

1. **Phase 1**: Create failing unit tests that reproduce AttributeError
2. **Phase 2**: Implement missing `is_connection_active` method
3. **Phase 3**: Validate tests pass and add integration tests
4. **Phase 4**: Run staging validation if needed

This test plan ensures Issue #1209 is thoroughly validated and prevents similar interface compliance issues in the future.