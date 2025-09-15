# 🧪 TEST PLAN: WebSocket Core Interface Compatibility (Issue #727)

## Executive Summary
**Scope**: Create targeted unit, integration, and e2e staging tests to reproduce and resolve interface compatibility issues between WebSocket tests and UnifiedWebSocketManager after SSOT consolidation.

**Root Cause Analysis**: Tests expect synchronous factory methods returning manager instances, but current implementation returns coroutines. Additionally, missing protocol compliance validation causing AttributeError exceptions.

---

## 🔍 Interface Compatibility Issues Identified

### Issue 1: Async/Sync Interface Mismatch
**Current Problem**: `create_websocket_manager()` returns `coroutine` instead of manager instance

**Evidence**:
```python
# Expected by tests:
manager = create_websocket_manager(context)
assert hasattr(manager, 'user_context')

# Actual behavior:
manager = create_websocket_manager(context)  # Returns <coroutine object>
# AssertionError: 'coroutine' object has no attribute 'user_context'
```

**Impact**: 4/5 tests failing in `test_websocket_manager_signature_regression.py`

### Issue 2: Missing Five Whys Critical Methods
**Current Problem**: Protocol compliance validation fails due to missing interface methods

**Evidence**:
```python
# Missing methods from WebSocketManagerProtocol:
- get_connection_id_by_websocket(websocket) -> Optional[ConnectionID]
- update_connection_thread(connection_id, thread_id) -> bool
```

**Impact**: Protocol validation tests unable to collect, breaking integration test suite

### Issue 3: Import Path Fragmentation
**Current Problem**: Multiple import paths causing confusion in test dependencies

**Evidence**:
```python
# Deprecated imports causing warnings:
from netra_backend.app.websocket_core import WebSocketManager  # Deprecated
# vs
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager  # Correct
```

---

## 🎯 Test Strategy: Three-Phase Approach

### Phase 1: Unit Tests (Non-Docker) - Foundation Layer
**Duration**: 2-3 days
**Focus**: Core interface compatibility and method signature validation

#### 1.1 Factory Interface Unit Tests
**File**: `tests/unit/websocket_core/test_websocket_factory_interface_compatibility.py`

**Test Coverage**:
- ✅ Factory method returns proper instance type (not coroutine)
- ✅ Factory method accepts both positional and keyword arguments
- ✅ Factory method validates UserExecutionContext parameter types
- ✅ Factory method preserves user isolation between calls
- ✅ Factory method error handling for invalid inputs

**Key Tests**:
```python
def test_factory_returns_manager_instance_not_coroutine():
    """Ensure factory returns actual manager, not coroutine."""
    context = create_test_context()
    manager = create_websocket_manager(context)

    # CRITICAL: Should not be coroutine
    assert not asyncio.iscoroutine(manager)
    assert hasattr(manager, 'user_context')
    assert isinstance(manager, UnifiedWebSocketManager)

def test_factory_accepts_both_call_patterns():
    """Test both positional and keyword argument patterns."""
    context = create_test_context()

    # Both should work identically
    manager1 = create_websocket_manager(context)
    manager2 = create_websocket_manager(user_context=context)

    assert type(manager1) == type(manager2)
    assert manager1.user_context.user_id == manager2.user_context.user_id
```

#### 1.2 Protocol Compliance Unit Tests
**File**: `tests/unit/websocket_core/test_unified_manager_protocol_compliance.py`

**Test Coverage**:
- ✅ UnifiedWebSocketManager implements WebSocketManagerProtocol
- ✅ All protocol methods exist with correct signatures
- ✅ Five Whys critical methods functionality validation
- ✅ Method return types match protocol specifications
- ✅ Type safety for UserID, ThreadID, ConnectionID parameters

**Key Tests**:
```python
def test_five_whys_critical_methods_exist():
    """Validate Five Whys critical methods are implemented."""
    manager = create_test_manager()

    # These methods MUST exist (root cause of original Five Whys)
    assert hasattr(manager, 'get_connection_id_by_websocket')
    assert hasattr(manager, 'update_connection_thread')

    # Signature validation
    assert callable(getattr(manager, 'get_connection_id_by_websocket'))
    assert callable(getattr(manager, 'update_connection_thread'))

def test_protocol_compliance_runtime_validation():
    """Ensure manager passes protocol compliance checks."""
    manager = create_test_manager()

    # Use protocol validator from protocols.py
    validation_result = WebSocketManagerProtocolValidator.validate_manager_protocol(manager)

    assert validation_result['compliant'], f"Protocol violations: {validation_result['missing_methods']}"
    assert len(validation_result['missing_methods']) == 0
    assert len(validation_result['invalid_signatures']) == 0
```

#### 1.3 User Isolation Security Unit Tests
**File**: `tests/unit/websocket_core/test_user_isolation_security_validation.py`

**Test Coverage**:
- ✅ Factory creates isolated manager instances per user
- ✅ UserExecutionContext prevents cross-user data leakage
- ✅ Connection state isolation between concurrent users
- ✅ Event delivery isolation validation
- ✅ Memory cleanup prevents context bleeding

### Phase 2: Integration Tests (Non-Docker) - System Interaction Layer
**Duration**: 2-3 days
**Focus**: Cross-component interactions and real WebSocket connections

#### 2.1 Factory Integration Tests
**File**: `tests/integration/websocket_core/test_factory_manager_integration.py`

**Test Coverage**:
- ✅ Factory-created managers integrate with UnifiedWebSocketEmitter
- ✅ Factory-created managers work with AgentRegistry
- ✅ Factory-created managers handle real UserExecutionContext
- ✅ Factory integration with WebSocket route handlers
- ✅ Factory error propagation to calling components

#### 2.2 Protocol Integration Tests
**File**: `tests/integration/websocket_core/test_protocol_system_integration.py`

**Test Coverage**:
- ✅ Protocol-compliant managers work with WebSocket routes
- ✅ Five Whys critical methods integration with agent execution
- ✅ Protocol validation in startup sequence
- ✅ Protocol compliance monitoring during operation
- ✅ Error recovery when protocol methods fail

#### 2.3 Golden Path Integration Tests
**File**: `tests/integration/websocket_core/test_golden_path_websocket_integration.py`

**Test Coverage**:
- ✅ Complete agent execution with WebSocket events
- ✅ All 5 critical WebSocket events (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed)
- ✅ Multi-user concurrent agent execution
- ✅ WebSocket connection lifecycle with agent workflows
- ✅ Error handling maintains Golden Path functionality

### Phase 3: E2E Staging Tests - Real Environment Validation
**Duration**: 1-2 days
**Focus**: Production-like validation on GCP staging

#### 3.1 Staging WebSocket Factory Tests
**File**: `tests/e2e/websocket_core/test_factory_staging_validation.py`

**Test Coverage**:
- ✅ Factory method works in GCP Cloud Run environment
- ✅ Real OAuth user context integration
- ✅ Staging database connectivity with factory-created managers
- ✅ Real WebSocket connections through load balancer
- ✅ Production-like error scenarios and recovery

#### 3.2 Staging Golden Path Tests
**File**: `tests/e2e/websocket_core/test_golden_path_staging_validation.py`

**Test Coverage**:
- ✅ Complete end-to-end user flow on staging
- ✅ Real agent execution with WebSocket events
- ✅ Multi-browser concurrent user simulation
- ✅ WebSocket reconnection scenarios
- ✅ Performance validation under realistic load

---

## 🛠️ Implementation Approach

### Testing Best Practices Compliance

#### SSOT Test Infrastructure
```python
# All tests must inherit from SSOT base classes
from test_framework.ssot.base_test_case import SSotBaseTestCase, SSotAsyncTestCase

class TestWebSocketFactoryInterface(SSotAsyncTestCase):
    """SSOT-compliant test class for WebSocket factory validation."""

    async def setUp(self):
        """Set up test environment with proper isolation."""
        await super().setUp()
        self.test_context = self.create_isolated_user_context()
```

#### Real Service Integration
```python
# No mocks for integration/e2e tests - use real WebSocket connections
async def test_real_websocket_connection_integration(self):
    """Test with actual WebSocket connection, no mocks."""
    # Create real WebSocket connection for testing
    websocket = await self.create_real_websocket_connection()

    # Test actual manager interaction
    manager = create_websocket_manager(self.test_context)
    await manager.add_connection(websocket)

    # Validate real event delivery
    event_sent = await manager.emit_critical_event("test_user", "agent_started", {})
    assert event_sent is True
```

#### User Context Isolation
```python
# Ensure proper user isolation in all tests
def test_concurrent_user_isolation(self):
    """Validate user isolation between concurrent manager instances."""
    context1 = UserExecutionContext("user_1", "thread_1", "run_1")
    context2 = UserExecutionContext("user_2", "thread_2", "run_2")

    manager1 = create_websocket_manager(context1)
    manager2 = create_websocket_manager(context2)

    # Managers should be completely isolated
    assert manager1.user_context.user_id != manager2.user_context.user_id
    assert id(manager1) != id(manager2)
```

### Test Categories Targeting

| Category | Tests | Focus | Docker Required |
|----------|-------|-------|-----------------|
| **Unit** | 35-45 | Interface compatibility | ❌ No |
| **Integration** | 25-35 | Cross-component | ❌ No |
| **E2E Staging** | 15-25 | Real environment | ❌ No (GCP) |

### Success Metrics

#### Quantitative Targets
- **Unit Test Coverage**: 70%+ on UnifiedWebSocketManager core methods
- **Integration Test Coverage**: 60%+ on factory → manager → events flow
- **E2E Coverage**: 50%+ on Golden Path user workflows
- **Regression Prevention**: 0 failing tests in existing WebSocket test suite

#### Qualitative Outcomes
- ✅ All interface compatibility issues reproduced and validated
- ✅ Factory method returns proper instances (not coroutines)
- ✅ Protocol compliance validation passes consistently
- ✅ Five Whys critical methods functionality confirmed
- ✅ User isolation security validated under concurrent load
- ✅ Golden Path WebSocket events work end-to-end

---

## 🔧 Test Infrastructure Requirements

### Dependencies
```bash
# Test execution through unified runner
python tests/unified_test_runner.py --category websocket --real-services

# Real service validation
python tests/unified_test_runner.py --category integration --no-docker

# Staging environment tests
python tests/unified_test_runner.py --category e2e --prefer-staging
```

### Environment Setup
- **Local Development**: Unit tests only, no external dependencies
- **CI Integration**: Integration tests with real service connections
- **Staging Validation**: E2E tests against staging.netra.ai environment

### Test Data Management
```python
# Use real-like test data, avoid "test_" patterns
USER_ID_EXAMPLES = [
    "105945141827451681156",  # Google OAuth format
    "github_user_98765432101",  # GitHub OAuth format
    "auth0_user_abc123def456"   # Auth0 format
]

THREAD_ID_EXAMPLES = [
    "thread_2025_09_13_abc123",
    "conversation_xyz789",
    "workflow_integration_456"
]
```

---

## 🎯 Specific Issues to Reproduce and Resolve

### Issue Reproduction Tests

#### 1. Coroutine Return Issue
```python
def test_reproduce_coroutine_return_bug():
    """Reproduce the exact error from failing tests."""
    context = UserExecutionContext("user_123", "thread_456", "run_789")

    # This should NOT return a coroutine
    result = create_websocket_manager(context)

    # Reproduce exact assertion that's currently failing
    assert not asyncio.iscoroutine(result), f"Expected manager, got coroutine: {type(result)}"
    assert hasattr(result, 'user_context'), f"Manager missing user_context attribute"
```

#### 2. Missing Method Issue
```python
def test_reproduce_missing_method_error():
    """Reproduce Five Whys critical method missing error."""
    manager = create_websocket_manager(create_test_context())

    # These should exist and be callable
    assert hasattr(manager, 'get_connection_id_by_websocket'), "Missing Five Whys critical method"
    assert hasattr(manager, 'update_connection_thread'), "Missing Five Whys critical method"

    # Should be able to call them without errors
    fake_websocket = Mock()
    connection_id = manager.get_connection_id_by_websocket(fake_websocket)
    assert connection_id is None or isinstance(connection_id, (str, ConnectionID))
```

### Integration Issue Resolution

#### 1. Agent Registry Integration
```python
async def test_agent_registry_websocket_manager_integration():
    """Ensure factory-created managers work with AgentRegistry."""
    from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry

    manager = create_websocket_manager(create_test_context())
    registry = AgentRegistry()

    # This integration should work without errors
    registry.set_websocket_manager(manager)

    # Validate proper event delivery chain
    agent = registry.create_agent("test_agent")
    await agent.execute_with_websocket_events()
```

#### 2. WebSocket Route Integration
```python
async def test_websocket_route_handler_integration():
    """Test integration with actual WebSocket route handlers."""
    from netra_backend.app.routes.websocket import websocket_endpoint

    # Create real WebSocket connection for testing
    test_client = create_test_client()
    websocket = await test_client.websocket_connect("/ws")

    # Factory-created manager should handle route integration
    manager = create_websocket_manager(create_test_context())

    # Validate complete request handling
    await websocket.send_json({"action": "start_agent", "agent_type": "test"})
    response = await websocket.receive_json()

    assert response["event_type"] == "agent_started"
```

---

## 🚀 Implementation Timeline

### Week 1: Unit Test Foundation
- **Day 1-2**: Factory interface compatibility tests
- **Day 3-4**: Protocol compliance validation tests
- **Day 5**: User isolation security tests

### Week 2: Integration & E2E Validation
- **Day 1-2**: Cross-component integration tests
- **Day 3-4**: Golden Path integration tests
- **Day 5**: Staging environment E2E tests

### Week 3: Validation & Documentation
- **Day 1-2**: Complete test suite execution and debugging
- **Day 3**: Performance validation and optimization
- **Day 4-5**: Documentation updates and test plan refinement

---

## ✅ Definition of Done

### Test Suite Completion Criteria
- [ ] All 75+ new tests pass consistently (>99% success rate)
- [ ] Zero regression in existing WebSocket test suite
- [ ] Coverage targets achieved (Unit: 70%, Integration: 60%, E2E: 50%)
- [ ] All interface compatibility issues reproduced and resolved
- [ ] Factory method returns proper instances (not coroutines)
- [ ] Protocol compliance validation passes for UnifiedWebSocketManager
- [ ] Five Whys critical methods functionality validated
- [ ] User isolation security confirmed under concurrent scenarios
- [ ] Golden Path WebSocket events work end-to-end on staging

### Business Value Protection
- [ ] **$500K+ ARR WebSocket infrastructure** validated and protected
- [ ] **Chat functionality (90% platform value)** confirmed operational
- [ ] **Multi-user isolation** security verified
- [ ] **Golden Path events** (agent_started, agent_thinking, tool_executing, tool_completed, agent_completed) validated
- [ ] **Production readiness** confirmed through staging tests

This comprehensive test plan will ensure robust coverage of WebSocket core infrastructure while protecting the critical business value delivered through chat functionality.

---

*Generated for Issue #727 - WebSocket Core Coverage Analysis*
*Priority: P0/Critical - Golden Path Infrastructure*
*Business Impact: $500K+ ARR Protection*