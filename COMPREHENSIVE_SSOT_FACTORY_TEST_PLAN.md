# 🚨 COMPREHENSIVE SSOT FACTORY TEST PLAN
## CRITICAL: Golden Path Factory Initialization Failures - Test Plan for SSOT Validation Issues

**MISSION CRITICAL CONTEXT**: WebSocket manager factory fails SSOT validation, causing 1011 errors that break chat functionality (our $500K+ ARR core business value).

**ROOT CAUSE**: Critical infrastructure classes lack proper SSOT implementation, creating validation failures that prevent proper Factory initialization.

---

## 📋 EXECUTIVE SUMMARY

This test plan identifies specific SSOT validation failures in the Factory Pattern implementation that cause:

1. **Factory Initialization Failures** - WebSocket manager factory fails SSOT validation
2. **1011 WebSocket Errors** - Breaking chat functionality  
3. **Golden Path Disruption** - Users cannot access core AI chat features
4. **Business Revenue Impact** - $500K+ ARR threatened by broken user flows

**TEST PHILOSOPHY**: Create failing tests that REPRODUCE the SSOT issues to prove they exist, then validate fixes.

---

## 🎯 IDENTIFIED SSOT VALIDATION POINTS

Based on codebase analysis, these are the critical SSOT validation points that are failing:

### 1. WebSocketBridgeFactory SSOT Validation Issues
**Location**: `netra_backend/app/services/websocket_bridge_factory.py`
**Problem**: Factory fails SSOT validation when creating user emitters
**Error Pattern**: `"Factory SSOT validation failed"`

### 2. ExecutionEngineFactory Dependency Validation  
**Location**: `netra_backend/app/agents/supervisor/execution_engine_factory.py`
**Problem**: WebSocket bridge validation fails during factory initialization  
**Error Pattern**: `"ExecutionEngineFactory requires websocket_bridge during initialization"`

### 3. UserExecutionContext SSOT Compliance
**Location**: `netra_backend/app/services/user_execution_context.py`
**Problem**: Context validation fails with placeholder values
**Error Pattern**: `"Invalid user context for engine creation"`

### 4. UnifiedToolDispatcherFactory Request Scoping
**Location**: Factory classes using UnifiedToolDispatcherFactory pattern
**Problem**: Request-scoped isolation not properly implemented
**Error Pattern**: Tool dispatcher creation fails validation

### 5. WebSocketManagerFactory SSOT ID Validation
**Location**: `netra_backend/app/websocket_core/websocket_manager_factory.py`  
**Problem**: SSOT ID generation and validation failures
**Error Pattern**: `"WebSocket factory SSOT validation failed"`

---

## 📊 TEST STRUCTURE OVERVIEW

```
├── Unit Tests (Reproduce SSOT Validation Failures)
│   ├── test_websocket_bridge_factory_ssot_validation_fails.py
│   ├── test_execution_engine_factory_ssot_validation_fails.py  
│   ├── test_user_execution_context_ssot_validation_fails.py
│   ├── test_unified_tool_dispatcher_factory_ssot_validation_fails.py
│   └── test_websocket_manager_factory_ssot_validation_fails.py
│
├── Integration Tests (Non-Docker Service Interactions)
│   ├── test_factory_integration_ssot_validation_failures.py
│   ├── test_websocket_factory_initialization_ssot_failures.py
│   └── test_execution_pipeline_ssot_validation_failures.py  
│
└── E2E Tests (GCP Staging Golden Path)
    ├── test_golden_path_ssot_validation_e2e.py
    ├── test_websocket_connection_ssot_compliance_e2e.py
    └── test_multi_user_factory_isolation_ssot_e2e.py
```

---

## 🧪 DETAILED TEST PLANS

## UNIT TESTS - SSOT Validation Failure Reproduction

### 1. WebSocketBridgeFactory SSOT Validation Failures

**File**: `tests/unit/factories/test_websocket_bridge_factory_ssot_validation_fails.py`

**Purpose**: Reproduce SSOT validation failures in WebSocket bridge factory that cause 1011 errors.

**Key Test Scenarios** (Initially FAILING):

```python
class TestWebSocketBridgeFactorySSotValidationFailures(BaseTestCase):
    """Test cases that reproduce SSOT validation failures in WebSocketBridgeFactory."""
    
    @pytest.mark.unit
    def test_factory_initialization_without_ssot_connection_pool_fails(self):
        """MUST FAIL: Factory should fail SSOT validation without proper connection pool."""
        # This test MUST fail initially to prove the SSOT issue exists
        factory = WebSocketBridgeFactory()
        
        with pytest.raises(RuntimeError, match="Factory not configured - call configure\\(\\) first"):
            # This should fail because factory lacks SSOT-compliant connection pool
            await factory.create_user_emitter("user_123", "thread_456", "conn_789")
    
    @pytest.mark.unit 
    def test_user_emitter_creation_fails_ssot_websocket_validation(self):
        """MUST FAIL: User emitter creation should fail SSOT WebSocket validation."""
        factory = WebSocketBridgeFactory()
        
        # Configure with mock connection pool that fails SSOT validation
        mock_pool = MockConnectionPool(websocket=None)  # No real WebSocket
        mock_registry = MockAgentRegistry()
        factory.configure(mock_pool, mock_registry, None)
        
        with pytest.raises(RuntimeError, match="No active WebSocket connection found"):
            # This should fail because mock connections don't pass SSOT validation
            await factory.create_user_emitter("user_123", "thread_456", "conn_789")
    
    @pytest.mark.unit
    def test_factory_metrics_ssot_validation_fails(self):
        """MUST FAIL: Factory metrics should fail SSOT validation without proper initialization."""
        factory = WebSocketBridgeFactory()
        
        # Get metrics without proper SSOT configuration
        metrics = factory.get_factory_metrics()
        
        # This should fail because metrics should require SSOT validation
        assert metrics['emitters_created'] == 0
        assert 'ssot_validation_status' not in metrics  # This proves SSOT validation is missing
```

### 2. ExecutionEngineFactory SSOT Dependency Validation Failures

**File**: `tests/unit/factories/test_execution_engine_factory_ssot_validation_fails.py`

**Key Test Scenarios** (Initially FAILING):

```python
class TestExecutionEngineFactorySSotValidationFailures(BaseTestCase):
    """Test cases that reproduce SSOT validation failures in ExecutionEngineFactory."""
    
    @pytest.mark.unit
    def test_factory_initialization_without_websocket_bridge_fails_ssot_validation(self):
        """MUST FAIL: Factory initialization should enforce SSOT WebSocket bridge requirement."""
        with pytest.raises(ExecutionEngineFactoryError, match="ExecutionEngineFactory requires websocket_bridge"):
            # This should fail with proper SSOT validation error
            ExecutionEngineFactory(websocket_bridge=None)
    
    @pytest.mark.unit
    async def test_user_engine_creation_fails_ssot_context_validation(self):
        """MUST FAIL: User engine creation should fail SSOT context validation."""
        mock_websocket_bridge = MockWebSocketBridge()
        factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        # Create context with invalid SSOT values
        invalid_context = UserExecutionContext(
            user_id="placeholder_user",  # SSOT violation - placeholder value
            thread_id="default_thread",  # SSOT violation - default value
            run_id="registry_run",       # SSOT violation - registry value
            request_id="temp_request"    # SSOT violation - temp value
        )
        
        with pytest.raises(ExecutionEngineFactoryError, match="Invalid user context"):
            # This should fail because context contains SSOT-forbidden placeholder values
            await factory.create_for_user(invalid_context)
    
    @pytest.mark.unit
    def test_websocket_emitter_creation_fails_ssot_bridge_validation(self):
        """MUST FAIL: WebSocket emitter creation should fail SSOT bridge validation."""  
        # Create factory with mock bridge that lacks SSOT validation
        mock_bridge = MockWebSocketBridge(ssot_compliant=False)
        factory = ExecutionEngineFactory(websocket_bridge=mock_bridge)
        
        context = create_valid_user_execution_context()
        
        with pytest.raises(ExecutionEngineFactoryError, match="WebSocket emitter creation failed"):
            # This should fail because mock bridge doesn't pass SSOT validation
            await factory.create_for_user(context)
```

### 3. UserExecutionContext SSOT Compliance Validation Failures

**File**: `tests/unit/context/test_user_execution_context_ssot_validation_fails.py`

**Key Test Scenarios** (Initially FAILING):

```python
class TestUserExecutionContextSSotValidationFailures(BaseTestCase):
    """Test cases that reproduce SSOT validation failures in UserExecutionContext."""
    
    @pytest.mark.unit
    def test_context_creation_with_ssot_forbidden_placeholder_values_fails(self):
        """MUST FAIL: Context creation should reject SSOT-forbidden placeholder values."""
        ssot_forbidden_values = [
            "placeholder_user", "registry_thread", "default_run", "temp_request",
            "example_user", "none_thread", "null_run", "placeholder_123"
        ]
        
        for forbidden_value in ssot_forbidden_values:
            with pytest.raises(InvalidContextError, match="Forbidden placeholder values"):
                # These should fail because they contain SSOT-forbidden placeholder patterns
                UserExecutionContext(
                    user_id=forbidden_value,
                    thread_id="thread_123",
                    run_id="run_456", 
                    request_id="req_789"
                )
    
    @pytest.mark.unit
    def test_context_validation_fails_ssot_id_format_requirements(self):
        """MUST FAIL: Context validation should enforce SSOT ID format requirements."""
        invalid_id_formats = [
            ("", "thread_123", "run_456", "req_789"),           # Empty user_id
            ("user_123", "", "run_456", "req_789"),             # Empty thread_id  
            ("user_123", "thread_123", "", "req_789"),          # Empty run_id
            ("user_123", "thread_123", "run_456", ""),          # Empty request_id
            ("user@invalid", "thread_123", "run_456", "req_789"), # Invalid characters
        ]
        
        for user_id, thread_id, run_id, request_id in invalid_id_formats:
            with pytest.raises(InvalidContextError):
                # These should fail SSOT ID format validation
                validate_user_context(UserExecutionContext(
                    user_id=user_id, thread_id=thread_id,
                    run_id=run_id, request_id=request_id
                ))
    
    @pytest.mark.unit
    def test_context_isolation_validation_fails_ssot_metadata_requirements(self):
        """MUST FAIL: Context isolation should fail SSOT metadata validation."""
        context = UserExecutionContext(
            user_id="user_123",
            thread_id="thread_456", 
            run_id="run_789",
            request_id="req_101112",
            # Missing SSOT-required audit_metadata
            audit_metadata=None  
        )
        
        with pytest.raises(InvalidContextError, match="audit_metadata.*required"):
            # This should fail because SSOT requires audit metadata for isolation
            context._validate_metadata_isolation()
```

### 4. UnifiedToolDispatcherFactory SSOT Request Scoping Failures

**File**: `tests/unit/factories/test_unified_tool_dispatcher_factory_ssot_validation_fails.py`

**Key Test Scenarios** (Initially FAILING):

```python
class TestUnifiedToolDispatcherFactorySSotValidationFailures(BaseTestCase):
    """Test cases that reproduce SSOT validation failures in UnifiedToolDispatcherFactory."""
    
    @pytest.mark.unit
    async def test_request_scoped_dispatcher_creation_fails_ssot_isolation_validation(self):
        """MUST FAIL: Request-scoped dispatcher creation should enforce SSOT isolation."""
        factory = UnifiedToolDispatcherFactory()
        
        # Create context that fails SSOT isolation requirements
        shared_context = UserExecutionContext(
            user_id="user_123",
            thread_id="thread_456",
            run_id="run_789", 
            request_id="req_101112"
        )
        
        # Create multiple dispatchers with same context (SSOT violation)
        dispatcher1 = factory.create_for_request(shared_context)
        dispatcher2 = factory.create_for_request(shared_context)  # Should fail SSOT isolation
        
        # This should fail because SSOT requires unique request-scoped instances
        assert dispatcher1 is not dispatcher2
        assert dispatcher1.user_context is not dispatcher2.user_context  # Should fail
    
    @pytest.mark.unit 
    async def test_tool_execution_fails_ssot_permission_validation(self):
        """MUST FAIL: Tool execution should fail SSOT permission validation."""
        factory = UnifiedToolDispatcherFactory()
        context = create_valid_user_execution_context()
        
        dispatcher = factory.create_for_request(context)
        
        # Create tool request without SSOT-compliant permission validation
        tool_request = {
            "tool_name": "database_query",
            "user_id": "different_user_456",  # Different user - SSOT violation
            "input": {"query": "SELECT * FROM users"}
        }
        
        with pytest.raises(PermissionError, match="SSOT permission validation failed"):
            # This should fail because user_id doesn't match context (SSOT violation)
            await dispatcher.dispatch_tool(tool_request)
```

---

## INTEGRATION TESTS - Factory Interaction SSOT Validation Failures

### 1. Factory Integration SSOT Validation Failures

**File**: `tests/integration/factories/test_factory_integration_ssot_validation_failures.py`

**Key Test Scenarios** (Initially FAILING):

```python
class TestFactoryIntegrationSSotValidationFailures(BaseIntegrationTest):
    """Integration tests that reproduce SSOT validation failures across factories."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_execution_engine_websocket_factory_integration_fails_ssot_validation(self, real_services_fixture):
        """MUST FAIL: Integration between ExecutionEngineFactory and WebSocketBridgeFactory should enforce SSOT."""
        db = real_services_fixture["db"] 
        redis = real_services_fixture["redis"]
        
        # Create ExecutionEngineFactory without SSOT-compliant WebSocket bridge
        mock_websocket_bridge = MockWebSocketBridge(ssot_compliant=False)
        execution_factory = ExecutionEngineFactory(websocket_bridge=mock_websocket_bridge)
        
        context = await create_real_user_execution_context(db=db)
        
        with pytest.raises(ExecutionEngineFactoryError, match="WebSocket.*SSOT.*validation"):
            # This should fail because WebSocket bridge doesn't meet SSOT requirements
            await execution_factory.create_for_user(context)
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_factory_connection_pool_integration_fails_ssot_validation(self, real_services_fixture):
        """MUST FAIL: WebSocket factory + connection pool integration should enforce SSOT connection validation."""
        redis = real_services_fixture["redis"]
        
        # Create WebSocketBridgeFactory with non-SSOT connection pool
        websocket_factory = WebSocketBridgeFactory()
        mock_connection_pool = MockConnectionPool()
        mock_agent_registry = MockAgentRegistry()
        
        # Configure with mocks that don't enforce SSOT validation
        websocket_factory.configure(mock_connection_pool, mock_agent_registry, None)
        
        with pytest.raises(RuntimeError, match="No active WebSocket connection found"):
            # This should fail because connection pool doesn't provide SSOT-compliant connections
            await websocket_factory.create_user_emitter("user_123", "thread_456", "conn_789")
    
    @pytest.mark.integration
    async def test_tool_dispatcher_execution_engine_integration_fails_ssot_isolation(self):
        """MUST FAIL: Tool dispatcher + execution engine integration should enforce SSOT isolation."""
        # Create execution engine with real dependencies
        websocket_bridge = await create_real_websocket_bridge()
        execution_factory = ExecutionEngineFactory(websocket_bridge=websocket_bridge)
        
        context1 = create_valid_user_execution_context(user_id="user_123")
        context2 = create_valid_user_execution_context(user_id="user_456")
        
        engine1 = await execution_factory.create_for_user(context1)
        engine2 = await execution_factory.create_for_user(context2)
        
        # Attempt to use engine1's tool dispatcher with engine2's context (SSOT violation)
        tool_dispatcher = engine1._get_tool_dispatcher()  
        
        with pytest.raises(SSotIsolationError, match="Context mismatch.*SSOT isolation"):
            # This should fail because tool dispatcher is bound to different user context
            await tool_dispatcher.dispatch_tool({
                "tool_name": "test_tool",
                "context": context2,  # Wrong context - SSOT violation
                "input": {"test": "data"}
            })
```

### 2. WebSocket Factory Initialization SSOT Failures

**File**: `tests/integration/websocket/test_websocket_factory_initialization_ssot_failures.py`

**Key Test Scenarios** (Initially FAILING):

```python
class TestWebSocketFactoryInitializationSSotFailures(BaseIntegrationTest):
    """Integration tests for WebSocket factory initialization SSOT validation failures."""
    
    @pytest.mark.integration
    @pytest.mark.real_services
    async def test_websocket_manager_factory_ssot_id_validation_fails(self, real_services_fixture):
        """MUST FAIL: WebSocket manager factory should fail SSOT ID validation."""
        redis = real_services_fixture["redis"]
        
        # Create factory with invalid SSOT configuration
        factory = WebSocketManagerFactory(enable_ssot_validation=True)
        
        # Attempt to create manager with SSOT-forbidden ID patterns
        forbidden_ids = ["placeholder_user", "default_thread", "registry_ws", "temp_connection"]
        
        for forbidden_id in forbidden_ids:
            with pytest.raises(FactoryInitializationError, match="SSOT.*validation.*failed"):
                # Should fail because IDs contain forbidden SSOT patterns
                await factory.create_websocket_manager(
                    user_id=forbidden_id,
                    thread_id="thread_123",
                    websocket_id="ws_456"
                )
    
    @pytest.mark.integration 
    @pytest.mark.real_services
    async def test_websocket_bridge_factory_real_connection_validation_fails(self, real_services_fixture):
        """MUST FAIL: WebSocket bridge factory should enforce real connection SSOT validation."""
        db = real_services_fixture["db"]
        redis = real_services_fixture["redis"]
        
        factory = WebSocketBridgeFactory()
        connection_pool = WebSocketConnectionPool()
        agent_registry = AgentRegistry()
        
        factory.configure(connection_pool, agent_registry, None)
        
        # Attempt to create emitter without real WebSocket connection
        with pytest.raises(RuntimeError, match="No active WebSocket connection found"):
            # Should fail because no real WebSocket connection exists (SSOT requirement)
            await factory.create_user_emitter("user_123", "thread_456", "nonexistent_conn")
```

---

## E2E TESTS - Golden Path SSOT Validation Failures

### 1. Golden Path SSOT Validation E2E

**File**: `tests/e2e/golden_path/test_golden_path_ssot_validation_e2e.py`

**Key Test Scenarios** (Initially FAILING):

```python
class TestGoldenPathSSotValidationE2E(BaseE2ETest):
    """E2E tests that reproduce SSOT validation failures in golden path user flow."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.gcp_staging
    async def test_golden_path_websocket_connection_fails_ssot_factory_validation(self, real_services, authenticated_user):
        """MUST FAIL: Golden path WebSocket connection should fail SSOT factory validation."""
        user = authenticated_user
        
        # Attempt to establish WebSocket connection through golden path
        websocket_url = f"{real_services['websocket_url']}/ws/{user.id}"
        
        async with self.websocket_client(websocket_url, user.token) as websocket:
            # Send agent execution request
            await websocket.send_json({
                "type": "execute_agent",
                "agent": "cost_optimizer", 
                "message": "Analyze my costs",
                "user_id": user.id,
                "thread_id": "placeholder_thread"  # SSOT violation
            })
            
            # Should receive 1011 error due to SSOT factory validation failure
            response = await websocket.receive_json()
            
            assert response["type"] == "error"
            assert response["code"] == 1011
            assert "Factory SSOT validation failed" in response["message"]
    
    @pytest.mark.e2e
    @pytest.mark.real_services  
    @pytest.mark.gcp_staging
    async def test_multi_user_golden_path_fails_ssot_isolation_validation(self, real_services):
        """MUST FAIL: Multi-user golden path should fail SSOT isolation validation."""
        # Create two users
        user1 = await self.create_test_user("user1@test.com")
        user2 = await self.create_test_user("user2@test.com") 
        
        websocket_url_base = real_services['websocket_url']
        
        # Establish WebSocket connections for both users
        async with self.websocket_client(f"{websocket_url_base}/ws/{user1.id}", user1.token) as ws1:
            async with self.websocket_client(f"{websocket_url_base}/ws/{user2.id}", user2.token) as ws2:
                
                # Send agent requests simultaneously (stress test SSOT isolation)
                await asyncio.gather(
                    ws1.send_json({
                        "type": "execute_agent",
                        "agent": "cost_optimizer",
                        "message": "User 1 cost analysis",
                        "thread_id": "shared_thread_123"  # SSOT violation - shared thread
                    }),
                    ws2.send_json({
                        "type": "execute_agent", 
                        "agent": "cost_optimizer",
                        "message": "User 2 cost analysis",
                        "thread_id": "shared_thread_123"  # SSOT violation - same thread
                    })
                )
                
                # Should fail due to SSOT isolation violation
                response1 = await ws1.receive_json()
                response2 = await ws2.receive_json()
                
                # At least one should fail SSOT isolation validation
                error_responses = [r for r in [response1, response2] if r.get("type") == "error"]
                assert len(error_responses) > 0
                assert any("SSOT isolation" in r.get("message", "") for r in error_responses)
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.gcp_staging
    async def test_agent_execution_pipeline_fails_ssot_context_validation(self, real_services, authenticated_user):
        """MUST FAIL: Agent execution pipeline should fail SSOT context validation."""
        user = authenticated_user
        websocket_url = f"{real_services['websocket_url']}/ws/{user.id}"
        
        async with self.websocket_client(websocket_url, user.token) as websocket:
            # Send agent request with SSOT-invalid context
            await websocket.send_json({
                "type": "execute_agent",
                "agent": "cost_optimizer",
                "message": "Analyze costs",
                "context": {
                    "user_id": "placeholder_user_456",    # SSOT violation - placeholder
                    "thread_id": "registry_thread_789",   # SSOT violation - registry  
                    "run_id": "default_run_101112",       # SSOT violation - default
                    "request_id": "temp_req_131415"       # SSOT violation - temp
                }
            })
            
            # Should fail SSOT context validation
            response = await websocket.receive_json()
            
            assert response["type"] == "error"
            assert "SSOT.*context.*validation" in response["message"]
            assert "forbidden.*placeholder.*values" in response["message"].lower()
```

### 2. WebSocket Connection SSOT Compliance E2E

**File**: `tests/e2e/websocket/test_websocket_connection_ssot_compliance_e2e.py`

**Key Test Scenarios** (Initially FAILING):

```python
class TestWebSocketConnectionSSotComplianceE2E(BaseE2ETest):
    """E2E tests for WebSocket connection SSOT compliance validation."""
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.gcp_staging  
    async def test_websocket_factory_creation_fails_ssot_bridge_validation(self, real_services):
        """MUST FAIL: WebSocket factory creation should fail SSOT bridge validation in staging."""
        # This test validates that staging environment properly enforces SSOT validation
        
        # Create test user
        user = await self.create_test_user("ssot-test@example.com")
        websocket_url = f"{real_services['websocket_url']}/ws/{user.id}"
        
        # Attempt connection with invalid WebSocket factory configuration
        try:
            async with self.websocket_client(websocket_url, user.token) as websocket:
                # Send message that triggers factory creation
                await websocket.send_json({
                    "type": "ping",
                    "force_factory_recreation": True,  # Force factory validation
                    "ssot_validation_level": "strict"
                })
                
                response = await asyncio.wait_for(websocket.receive_json(), timeout=5.0)
                
                # Should fail with SSOT factory validation error
                if response.get("type") == "error":
                    assert "Factory SSOT validation failed" in response.get("message", "")
                else:
                    pytest.fail("Expected SSOT factory validation failure, but connection succeeded")
                    
        except ConnectionAbortedError as e:
            # Expected - connection should be aborted due to SSOT validation failure
            assert "1011" in str(e) or "SSOT" in str(e)
    
    @pytest.mark.e2e
    @pytest.mark.real_services
    @pytest.mark.performance
    async def test_websocket_event_delivery_fails_ssot_isolation_under_load(self, real_services):
        """MUST FAIL: WebSocket event delivery should fail SSOT isolation under load."""
        # Create multiple users for load testing
        users = []
        for i in range(5):
            user = await self.create_test_user(f"load-test-{i}@example.com")
            users.append(user)
        
        websocket_url_base = real_services['websocket_url']
        
        # Establish connections for all users
        websockets = []
        try:
            for user in users:
                ws = await self.websocket_client(f"{websocket_url_base}/ws/{user.id}", user.token).__aenter__()
                websockets.append(ws)
            
            # Send simultaneous agent requests to stress SSOT isolation
            tasks = []
            for i, ws in enumerate(websockets):
                task = asyncio.create_task(ws.send_json({
                    "type": "execute_agent",
                    "agent": "triage_agent",
                    "message": f"Load test message {i}",
                    "stress_ssot_isolation": True
                }))
                tasks.append(task)
            
            await asyncio.gather(*tasks)
            
            # Collect responses and validate SSOT isolation
            responses = []
            for ws in websockets:
                response = await asyncio.wait_for(ws.receive_json(), timeout=10.0)
                responses.append(response)
            
            # Should have SSOT isolation failures under load
            error_count = sum(1 for r in responses if r.get("type") == "error")
            assert error_count > 0, "Expected SSOT isolation failures under load"
            
            ssot_errors = [r for r in responses 
                          if r.get("type") == "error" and "SSOT" in r.get("message", "")]
            assert len(ssot_errors) > 0, "Expected explicit SSOT validation errors"
            
        finally:
            # Cleanup connections
            for ws in websockets:
                try:
                    await ws.__aexit__(None, None, None)
                except:
                    pass
```

---

## 📝 TEST EXECUTION STRATEGY

### Phase 1: Unit Test Execution (Prove SSOT Issues Exist)
```bash
# Run SSOT validation failure tests - These MUST fail initially
python tests/unified_test_runner.py --category unit --pattern "*ssot*validation*fails*"

# Expected Result: ALL tests should FAIL with SSOT validation errors
# This proves the SSOT issues exist in the codebase
```

### Phase 2: Integration Test Execution (Validate Service Interactions)
```bash  
# Run integration tests with real services
python tests/unified_test_runner.py --category integration --real-services --pattern "*factory*ssot*"

# Expected Result: Tests should FAIL with factory initialization errors
# This proves SSOT issues affect service integration
```

### Phase 3: E2E Test Execution (Golden Path Validation)
```bash
# Run E2E tests against GCP staging
python tests/unified_test_runner.py --category e2e --env staging --pattern "*golden*path*ssot*"

# Expected Result: Tests should FAIL with 1011 WebSocket errors  
# This proves SSOT issues break the golden path user flow
```

---

## 🔧 TEST FRAMEWORK INTEGRATION

### SSOT Testing Patterns Integration

**File**: `test_framework/ssot/ssot_validation_helpers.py`

```python
"""SSOT validation helpers for comprehensive testing."""

from typing import Dict, List, Any, Optional
import pytest
from dataclasses import dataclass

@dataclass
class SSotValidationResult:
    """Result of SSOT validation testing."""
    is_valid: bool
    violations: List[str] 
    error_details: Optional[Dict[str, Any]] = None

class SSotValidationTester:
    """Helper class for testing SSOT validation failures."""
    
    FORBIDDEN_PLACEHOLDER_PATTERNS = [
        "placeholder_", "registry_", "default_", "temp_", "example_",
        "none_", "null_", "mock_", "test_", "dummy_"
    ]
    
    @staticmethod
    def create_ssot_violating_context(violation_type: str) -> Dict[str, Any]:
        """Create context that violates SSOT requirements."""
        violations = {
            "placeholder_user_id": {"user_id": "placeholder_user_123"},
            "registry_thread_id": {"thread_id": "registry_thread_456"}, 
            "default_run_id": {"run_id": "default_run_789"},
            "temp_request_id": {"request_id": "temp_request_101112"},
            "empty_values": {"user_id": "", "thread_id": None},
            "invalid_format": {"user_id": "user@invalid#format"}
        }
        return violations.get(violation_type, {})
    
    @staticmethod
    def validate_factory_ssot_compliance(factory_instance: Any) -> SSotValidationResult:
        """Validate factory instance for SSOT compliance."""
        violations = []
        
        # Check for SSOT-required methods
        required_methods = ["configure", "get_factory_metrics", "cleanup"]
        for method in required_methods:
            if not hasattr(factory_instance, method):
                violations.append(f"Missing SSOT-required method: {method}")
        
        # Check for SSOT validation in initialization
        if not hasattr(factory_instance, "_ssot_validation_enabled"):
            violations.append("Missing SSOT validation flag")
        
        return SSotValidationResult(
            is_valid=len(violations) == 0,
            violations=violations
        )

def assert_ssot_validation_failure(expected_error_pattern: str):
    """Decorator to assert that a test fails with expected SSOT validation error."""
    def decorator(test_func):
        async def wrapper(*args, **kwargs):
            with pytest.raises((RuntimeError, ExecutionEngineFactoryError, InvalidContextError), 
                               match=expected_error_pattern):
                await test_func(*args, **kwargs)
        return wrapper
    return decorator
```

### Integration with Existing Test Framework

**File**: `test_framework/base_ssot_test.py`

```python
"""Base test class for SSOT validation testing."""

from test_framework.base_integration_test import BaseIntegrationTest
from test_framework.ssot.ssot_validation_helpers import SSotValidationTester, SSotValidationResult

class BaseSSotValidationTest(BaseIntegrationTest):
    """Base class for SSOT validation testing with helper methods."""
    
    def setUp(self):
        super().setUp()
        self.ssot_tester = SSotValidationTester()
    
    def assert_ssot_violation(self, factory_instance, expected_violations: List[str]):
        """Assert that factory instance has expected SSOT violations."""
        result = self.ssot_tester.validate_factory_ssot_compliance(factory_instance)
        
        assert not result.is_valid, "Expected SSOT violations but factory is valid"
        
        for expected in expected_violations:
            assert any(expected in violation for violation in result.violations), \
                f"Expected SSOT violation '{expected}' not found. Got: {result.violations}"
    
    def create_ssot_violating_user_context(self, violation_type: str):
        """Create UserExecutionContext that violates SSOT requirements."""
        violation_data = self.ssot_tester.create_ssot_violating_context(violation_type)
        
        base_context = {
            "user_id": "user_123",
            "thread_id": "thread_456", 
            "run_id": "run_789",
            "request_id": "req_101112"
        }
        base_context.update(violation_data)
        
        return UserExecutionContext(**base_context)
```

---

## 🎯 SUCCESS CRITERIA

### Tests MUST Initially Fail to Prove Issues Exist

1. **Unit Tests**: ALL SSOT validation tests MUST fail initially
   - WebSocketBridgeFactory SSOT validation failures
   - ExecutionEngineFactory dependency validation failures  
   - UserExecutionContext SSOT compliance failures
   - UnifiedToolDispatcherFactory request scoping failures

2. **Integration Tests**: Factory integration tests MUST fail
   - Factory initialization with SSOT validation failures
   - WebSocket factory + connection pool SSOT failures
   - Tool dispatcher + execution engine SSOT isolation failures

3. **E2E Tests**: Golden path tests MUST fail with 1011 errors
   - WebSocket connection failures due to Factory SSOT validation
   - Multi-user isolation failures under SSOT validation
   - Agent execution pipeline SSOT context validation failures

### After SSOT Implementation Fixes

1. **All tests should pass** after proper SSOT classes are implemented
2. **Factory initialization should succeed** with SSOT-compliant dependencies  
3. **Golden path should work** without 1011 WebSocket errors
4. **Multi-user isolation should be maintained** under all load conditions

---

## 📊 COVERAGE METRICS

Target coverage for SSOT validation points:

- **WebSocketBridgeFactory**: 100% of SSOT validation paths
- **ExecutionEngineFactory**: 100% of dependency validation paths  
- **UserExecutionContext**: 100% of SSOT compliance validation paths
- **Factory Integration**: 100% of inter-factory SSOT validation paths
- **Golden Path Flow**: 100% of WebSocket factory initialization paths

---

## 🚨 CRITICAL NOTES

1. **Tests MUST fail initially** - This proves the SSOT issues exist
2. **No mocks in E2E tests** - Use real GCP staging environment
3. **Real services in integration tests** - Use actual database/Redis connections
4. **Comprehensive error validation** - Verify exact SSOT error messages
5. **Performance impact testing** - Validate SSOT compliance under load

**BUSINESS IMPACT**: These tests validate the infrastructure that enables $500K+ ARR through reliable chat functionality. Failing SSOT validation breaks the core user experience.
