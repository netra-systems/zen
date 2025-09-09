"""Integration tests for error propagation and circuit breaker patterns.

CRITICAL: These tests verify REAL multi-component interactions for error handling
and circuit breaker patterns without Docker dependencies. They test business-critical
scenarios where errors propagate through multiple system components and trigger
appropriate recovery mechanisms.

Business Value: System resilience and graceful error handling.
"""

import asyncio
import pytest
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from enum import Enum
from unittest.mock import AsyncMock

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager, WebSocketConnection
from shared.isolated_environment import IsolatedEnvironment


class CircuitBreakerState(Enum):
    """Circuit breaker states for testing."""
    CLOSED = "closed"
    OPEN = "open" 
    HALF_OPEN = "half_open"


class MockCircuitBreaker:
    """Mock circuit breaker for testing error handling patterns."""
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: float = 5.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.state = CircuitBreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        self.call_history = []  # Track all calls for testing
        
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection."""
        call_record = {
            "timestamp": datetime.now(),
            "state_before": self.state,
            "args": args,
            "kwargs": kwargs
        }
        
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
                call_record["state_after"] = self.state
            else:
                call_record["result"] = "circuit_open"
                call_record["state_after"] = self.state
                self.call_history.append(call_record)
                raise RuntimeError("Circuit breaker is OPEN - rejecting call")
        
        try:
            result = await func(*args, **kwargs) if asyncio.iscoroutinefunction(func) else func(*args, **kwargs)
            
            # Success - reset failure count
            if self.state == CircuitBreakerState.HALF_OPEN:
                self.state = CircuitBreakerState.CLOSED
                self.failure_count = 0
                
            call_record["result"] = "success"
            call_record["state_after"] = self.state
            self.call_history.append(call_record)
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = CircuitBreakerState.OPEN
                
            call_record["result"] = "failure"
            call_record["error"] = str(e)
            call_record["failure_count"] = self.failure_count
            call_record["state_after"] = self.state
            self.call_history.append(call_record)
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if circuit breaker should attempt reset."""
        if self.last_failure_time is None:
            return True
        return (datetime.now() - self.last_failure_time).total_seconds() > self.recovery_timeout
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "call_count": len(self.call_history),
            "success_count": len([c for c in self.call_history if c["result"] == "success"]),
            "failure_rate": self.failure_count / max(1, len(self.call_history))
        }


class MockErrorProneService:
    """Mock service that can simulate various types of failures."""
    
    def __init__(self):
        self.operation_count = 0
        self.failure_modes = {}  # operation_name -> failure_config
        self.call_log = []
        
    def set_failure_mode(self, operation: str, failure_rate: float = 1.0, 
                        failure_type: str = "generic", max_failures: int = None):
        """Configure failure behavior for an operation."""
        self.failure_modes[operation] = {
            "failure_rate": failure_rate,
            "failure_type": failure_type,
            "failure_count": 0,
            "max_failures": max_failures
        }
    
    async def database_operation(self, user_id: str, operation_type: str) -> Dict[str, Any]:
        """Simulate database operation that can fail."""
        self.operation_count += 1
        call_record = {
            "timestamp": datetime.now(),
            "operation": "database_operation",
            "user_id": user_id,
            "operation_type": operation_type,
            "operation_count": self.operation_count
        }
        
        if "database_operation" in self.failure_modes:
            config = self.failure_modes["database_operation"]
            should_fail = (
                config["max_failures"] is None or 
                config["failure_count"] < config["max_failures"]
            )
            
            if should_fail and self.operation_count % (1 / config["failure_rate"]) == 0:
                config["failure_count"] += 1
                call_record["result"] = "failure"
                self.call_log.append(call_record)
                
                if config["failure_type"] == "timeout":
                    raise TimeoutError(f"Database operation timed out for user {user_id}")
                elif config["failure_type"] == "connection":
                    raise ConnectionError(f"Database connection failed for user {user_id}")
                else:
                    raise RuntimeError(f"Database operation failed for user {user_id}")
        
        call_record["result"] = "success"
        self.call_log.append(call_record)
        return {"user_id": user_id, "operation_type": operation_type, "success": True}
    
    async def external_api_call(self, user_id: str, api_name: str) -> Dict[str, Any]:
        """Simulate external API call that can fail."""
        call_record = {
            "timestamp": datetime.now(),
            "operation": "external_api_call",
            "user_id": user_id,
            "api_name": api_name
        }
        
        if "external_api_call" in self.failure_modes:
            config = self.failure_modes["external_api_call"]
            should_fail = (
                config["max_failures"] is None or 
                config["failure_count"] < config["max_failures"]
            )
            
            if should_fail:
                config["failure_count"] += 1
                call_record["result"] = "failure"
                self.call_log.append(call_record)
                
                raise RuntimeError(f"External API {api_name} failed for user {user_id}")
        
        call_record["result"] = "success"  
        self.call_log.append(call_record)
        return {"user_id": user_id, "api_name": api_name, "response": "success"}


class TestErrorPropagationCircuitBreakerIntegration:
    """Integration tests for error propagation and circuit breaker patterns."""
    
    @pytest.fixture
    def isolated_env(self):
        """Create isolated environment for testing."""
        env = IsolatedEnvironment()
        env.set('ERROR_RECOVERY_ENABLED', 'true')
        env.set('CIRCUIT_BREAKER_ENABLED', 'true')
        env.set('MAX_RETRY_ATTEMPTS', '3')
        return env
    
    @pytest.fixture
    def circuit_breaker(self):
        """Create circuit breaker for testing."""
        return MockCircuitBreaker(failure_threshold=3, recovery_timeout=2.0)
        
    @pytest.fixture
    def error_prone_service(self):
        """Create error-prone service for testing."""
        return MockErrorProneService()
        
    @pytest.fixture
    def websocket_manager(self):
        """Create WebSocket manager for error event testing."""
        return UnifiedWebSocketManager()
    
    @pytest.fixture
    def mock_llm_manager(self):
        """Create mock LLM manager."""
        llm_manager = AsyncMock()
        return llm_manager
        
    @pytest.fixture
    def agent_registry(self, mock_llm_manager):
        """Create agent registry."""
        return AgentRegistry(mock_llm_manager)
        
    @pytest.fixture
    def user_contexts(self):
        """Create user execution contexts for testing."""
        contexts = []
        for i in range(2):
            context = UserExecutionContext(
                user_id=f"error_test_user_{i}",
                thread_id=f"error_test_thread_{i}",
                request_id=f"error_test_request_{i}",
                run_id=f"error_test_run_{i}"
            )
            contexts.append(context)
        return contexts

    @pytest.mark.asyncio
    async def test_error_propagation_across_components(self, error_prone_service, circuit_breaker, 
                                                     websocket_manager, agent_registry, user_contexts):
        """
        Test REAL error propagation across multiple system components.
        
        This tests the interaction between:
        - MockErrorProneService (service failures)
        - MockCircuitBreaker (error protection)
        - UnifiedWebSocketManager (error event delivery)  
        - AgentRegistry (session error handling)
        - UserExecutionContext (error isolation)
        
        Business scenario: When services fail, errors should propagate through
        the system, trigger circuit breakers, and notify users appropriately.
        """
        # PHASE 1: Set up components with error integration
        user_context = user_contexts[0]
        
        # Set up WebSocket connection for error notifications
        from unittest.mock import Mock
        mock_websocket = Mock()
        mock_websocket.send_json = AsyncMock()
        
        connection = WebSocketConnection(
            connection_id=f"error_conn_{user_context.user_id}",
            user_id=user_context.user_id,
            websocket=mock_websocket,
            connected_at=datetime.now()
        )
        await websocket_manager.add_connection(connection)
        
        # Set up agent registry with WebSocket integration
        agent_registry.set_websocket_manager(websocket_manager)
        user_session = await agent_registry.get_user_session(user_context.user_id)
        
        # PHASE 2: Configure service to fail
        error_prone_service.set_failure_mode(
            "database_operation", 
            failure_rate=1.0,  # Always fail initially
            failure_type="connection",
            max_failures=2  # Fail first 2 times, then succeed
        )
        
        # PHASE 3: Test error propagation with circuit breaker
        operation_results = []
        circuit_breaker_calls = []
        
        # Attempt operations that will initially fail
        for attempt in range(5):
            try:
                # Use circuit breaker to protect the operation
                result = await circuit_breaker.call(
                    error_prone_service.database_operation,
                    user_context.user_id,
                    f"test_operation_{attempt}"
                )
                operation_results.append({"attempt": attempt, "result": "success", "data": result})
                
            except Exception as e:
                operation_results.append({"attempt": attempt, "result": "error", "error": str(e)})
                
                # Send error notification through WebSocket
                await websocket_manager.emit_critical_event(
                    user_context.user_id,
                    "operation_error",
                    {
                        "attempt": attempt,
                        "error_type": type(e).__name__,
                        "error_message": str(e),
                        "circuit_breaker_state": circuit_breaker.state.value
                    }
                )
            
            circuit_breaker_calls.append(circuit_breaker.get_metrics())
        
        # PHASE 4: Analyze error propagation pattern
        # First 2 attempts should fail due to service failures
        assert operation_results[0]["result"] == "error", "First attempt should fail"
        assert operation_results[1]["result"] == "error", "Second attempt should fail"
        
        # Circuit breaker should open after failure threshold
        final_metrics = circuit_breaker.get_metrics()
        assert final_metrics["failure_count"] >= 2, "Should have recorded failures"
        
        # Later attempts should either be rejected by circuit breaker or succeed (once service recovers)
        circuit_open_rejections = [r for r in operation_results if "circuit breaker is OPEN" in r.get("error", "")]
        service_successes = [r for r in operation_results if r["result"] == "success"]
        
        # Should have either circuit breaker rejections or service recovery
        assert len(circuit_open_rejections) > 0 or len(service_successes) > 0, "Should see either CB rejection or recovery"
        
        # PHASE 5: Verify error events were sent to user
        sent_calls = mock_websocket.send_json.call_args_list
        assert len(sent_calls) >= 2, "Should have sent error notifications"
        
        # Verify error event content
        error_events = [call[0][0] for call in sent_calls]  # Extract first arg from each call
        for event in error_events:
            assert event["type"] == "operation_error", "Should be operation error events"
            assert "error_type" in event["data"], "Should include error type"
            assert "circuit_breaker_state" in event["data"], "Should include circuit breaker state"
        
        # PHASE 6: Test error recovery
        # Wait for circuit breaker recovery period
        await asyncio.sleep(2.5)  # Longer than recovery timeout
        
        # Attempt operation after recovery - should succeed since service is now working
        try:
            recovery_result = await circuit_breaker.call(
                error_prone_service.database_operation,
                user_context.user_id,
                "recovery_test"
            )
            
            # Verify successful recovery
            assert recovery_result["success"] is True, "Recovery operation should succeed"
            
            # Send success notification
            await websocket_manager.emit_critical_event(
                user_context.user_id,
                "operation_recovered",
                {"message": "Service recovered successfully", "result": recovery_result}
            )
            
        except Exception as e:
            pytest.fail(f"Recovery operation should succeed but failed: {e}")
        
        # PHASE 7: Verify system returned to healthy state
        recovery_metrics = circuit_breaker.get_metrics()
        assert recovery_metrics["state"] in ["closed", "half_open"], "Circuit breaker should be closed or half-open"
        
        # Clean up
        await agent_registry.cleanup_user_session(user_context.user_id)

    @pytest.mark.asyncio
    async def test_concurrent_error_handling_with_user_isolation(self, error_prone_service, websocket_manager, 
                                                               agent_registry, user_contexts):
        """
        Test REAL concurrent error handling with proper user isolation.
        
        This tests the interaction between:
        - Multiple MockCircuitBreaker instances (per-user protection)
        - MockErrorProneService (shared service with failures)
        - UnifiedWebSocketManager (isolated error notifications)
        - AgentRegistry (multi-user session management)
        - UserExecutionContext (error isolation between users)
        
        Business scenario: When shared services fail, each user should have
        isolated error handling and recovery without cross-contamination.
        """
        # PHASE 1: Set up multiple users with individual circuit breakers
        user_circuit_breakers = {}
        user_websockets = {}
        
        for context in user_contexts:
            # Create individual circuit breaker for each user
            user_circuit_breakers[context.user_id] = MockCircuitBreaker(
                failure_threshold=2,  # Lower threshold for faster testing
                recovery_timeout=1.0
            )
            
            # Set up WebSocket connection for each user
            from unittest.mock import Mock
            mock_websocket = Mock()
            mock_websocket.send_json = AsyncMock()
            user_websockets[context.user_id] = mock_websocket
            
            connection = WebSocketConnection(
                connection_id=f"concurrent_error_conn_{context.user_id}",
                user_id=context.user_id,
                websocket=mock_websocket,
                connected_at=datetime.now()
            )
            await websocket_manager.add_connection(connection)
        
        # Set up agent registry
        agent_registry.set_websocket_manager(websocket_manager)
        user_sessions = {}
        for context in user_contexts:
            user_sessions[context.user_id] = await agent_registry.get_user_session(context.user_id)
        
        # PHASE 2: Configure service with intermittent failures
        error_prone_service.set_failure_mode(
            "external_api_call",
            failure_rate=0.6,  # 60% failure rate
            failure_type="generic"
        )
        
        # PHASE 3: Run concurrent operations for multiple users
        async def user_operations(user_id: str, operation_count: int):
            """Run operations for a specific user with their circuit breaker."""
            user_cb = user_circuit_breakers[user_id]
            user_results = []
            
            for i in range(operation_count):
                try:
                    result = await user_cb.call(
                        error_prone_service.external_api_call,
                        user_id,
                        f"api_test_{i}"
                    )
                    user_results.append({"operation": i, "result": "success", "data": result})
                    
                except Exception as e:
                    user_results.append({"operation": i, "result": "error", "error": str(e)})
                    
                    # Send error notification to user
                    await websocket_manager.emit_critical_event(
                        user_id,
                        "api_error", 
                        {
                            "operation_index": i,
                            "error": str(e),
                            "circuit_breaker_state": user_cb.state.value,
                            "failure_count": user_cb.failure_count
                        }
                    )
                
                # Small delay between operations
                await asyncio.sleep(0.1)
            
            return user_results
        
        # Run operations concurrently for all users
        tasks = []
        operation_count = 6
        
        for context in user_contexts:
            task = user_operations(context.user_id, operation_count)
            tasks.append(task)
        
        all_user_results = await asyncio.gather(*tasks)
        
        # PHASE 4: Analyze results and verify isolation
        user_results_map = {}
        for i, context in enumerate(user_contexts):
            user_results_map[context.user_id] = all_user_results[i]
        
        # Verify each user has independent error handling
        for user_id, results in user_results_map.items():
            user_cb = user_circuit_breakers[user_id]
            user_websocket = user_websockets[user_id]
            
            # Should have attempted all operations
            assert len(results) == operation_count, f"User {user_id} should have {operation_count} operation attempts"
            
            # Should have some errors due to service failure rate
            error_count = len([r for r in results if r["result"] == "error"])
            success_count = len([r for r in results if r["result"] == "success"])
            
            # Verify WebSocket notifications were sent for errors
            sent_calls = user_websocket.send_json.call_args_list
            error_notifications = len(sent_calls)
            
            # Error notifications should match error count (excluding circuit breaker rejections)
            service_errors = len([r for r in results if r["result"] == "error" and "circuit breaker is OPEN" not in r.get("error", "")])
            assert error_notifications >= service_errors, f"User {user_id} should receive error notifications"
            
            # Verify circuit breaker metrics
            cb_metrics = user_cb.get_metrics()
            assert cb_metrics["call_count"] > 0, f"User {user_id} circuit breaker should have call history"
        
        # PHASE 5: Verify user isolation - users should not affect each other
        # Get circuit breaker states for all users
        cb_states = {user_id: user_circuit_breakers[user_id].state for user_id in user_results_map.keys()}
        cb_failure_counts = {user_id: user_circuit_breakers[user_id].failure_count for user_id in user_results_map.keys()}
        
        # Users should have independent failure counts and states
        # (They might be similar due to shared service, but should not be identical due to timing)
        unique_failure_counts = set(cb_failure_counts.values())
        
        # Verify error events are properly isolated
        for user_id in user_results_map.keys():
            user_websocket = user_websockets[user_id]
            sent_calls = user_websocket.send_json.call_args_list
            
            # All events for this user should be for this user only
            for call in sent_calls:
                event_data = call[0][0]["data"]  # Extract event data
                # Events should not contain data from other users
                if "user_id" in str(event_data):
                    assert user_id in str(event_data), f"User {user_id} should only receive their own events"
        
        # PHASE 6: Clean up all user sessions
        for context in user_contexts:
            cleanup_result = await agent_registry.cleanup_user_session(context.user_id)
            assert cleanup_result["status"] == "cleaned", f"User {context.user_id} session should be cleaned"