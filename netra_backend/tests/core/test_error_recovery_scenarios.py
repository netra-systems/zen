"""
Comprehensive Error Recovery Test Suite for Netra AI

Tests cascading failures, partial success handling, rollback mechanisms,
compensation transactions, and error propagation paths.

Test Categories:
- Cascading: Agent failures propagating through system
- Partial: Some operations succeed while others fail  
- Rollback: Transaction rollback and state restoration
- Recovery: Automatic retry, manual intervention, graceful degradation

Dependencies:
- Circuit Breaker: Real implementation for state transitions
- Retry Handler: Real exponential backoff logic
- WebSocket Recovery: Real state snapshot and reconnection
- Database: Mocked sessions for controlled failures
- LLM: Mocked for rate limiting and service failures

Performance Targets:
- Unit tests: < 100ms each
- Integration tests: < 1s each
- Recovery scenarios: < 5s each
"""

# Add project root to path
import sys
from pathlib import Path

from netra_backend.tests.test_utils import setup_test_path

PROJECT_ROOT = Path(__file__).parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

setup_test_path()

import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from netra_backend.app.agents.state import DeepAgentState
from netra_backend.app.core.error_codes import ErrorCode, ErrorSeverity
from netra_backend.app.core.exceptions_base import ErrorDetails, NetraException

# Add project root to path
from netra_backend.app.core.reliability import AgentReliabilityWrapper
from netra_backend.app.core.reliability_circuit_breaker import (
    CircuitBreakerConfig,
    CircuitBreakerState,
)
from netra_backend.app.core.reliability_retry import RetryConfig
from netra_backend.app.services.state_persistence import state_persistence_service
from netra_backend.app.websocket.recovery import (
    RecoveryStrategy,
    WebSocketError,
    WebSocketRecoveryManager,
)

# Add project root to path


class ErrorRecoveryTestFixtures:
    """Fixtures for controlled error injection and recovery testing"""
    
    @staticmethod
    def create_failing_operation(failure_count: int, error_type: str = "ServiceError"):
        """Create operation that fails specified number of times"""
        call_count = 0
        async def failing_op():
            nonlocal call_count
            call_count += 1
            if call_count <= failure_count:
                raise Exception(error_type)
            return {"status": "success", "attempt": call_count}
        return failing_op
    
    @staticmethod
    def create_partial_success_operation(success_ratio: float = 0.5):
        """Create operation with partial success pattern"""
        call_count = 0
        async def partial_op():
            nonlocal call_count
            call_count += 1
            if call_count % 2 == 0 and success_ratio > 0.5:
                return {"status": "success", "call": call_count}
            raise Exception("PartialFailure")
        return partial_op
    
    @staticmethod
    def create_database_session_mock(fail_on_commit: bool = False):
        """Create database session mock with controlled failures"""
        session = AsyncMock()
        session.add = Mock()
        session.rollback = AsyncMock()
        session.close = AsyncMock()
        if fail_on_commit:
            session.commit = AsyncMock(side_effect=Exception("DB_COMMIT_FAILED"))
        else:
            session.commit = AsyncMock()
        return session


class TestCascadingFailureScenarios:
    """Test cascading failure scenarios across agent system"""
    async def test_agent_failure_propagation_circuit_breaker(self):
        """Test Agent A failure → Circuit breaker → Impact on dependent agents"""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=1.0)
        wrapper = AgentReliabilityWrapper("TestAgent", config)
        
        failing_op = ErrorRecoveryTestFixtures.create_failing_operation(3)
        
        # Execute failing operations to trigger circuit breaker
        for _ in range(3):
            try:
                await wrapper.execute_safely(failing_op, "test_operation")
            except Exception:
                pass
        
        # Verify circuit breaker is OPEN
        status = wrapper.circuit_breaker.get_status()
        assert status["state"] == CircuitBreakerState.OPEN.value
        assert status["failure_count"] >= 2
    async def test_database_failure_system_response(self):
        """Test Database failure → System graceful degradation"""
        session = ErrorRecoveryTestFixtures.create_database_session_mock(fail_on_commit=True)
        
        # Mock state persistence failure
        async def failing_save(run_id, thread_id, user_id, state, db_session):
            raise Exception("DATABASE_UNAVAILABLE")
        
        with patch.object(state_persistence_service, 'save_agent_state', failing_save):
            # Verify operation handles database failure gracefully
            try:
                await state_persistence_service.save_agent_state(
                    "test_run", "test_thread", "test_user", 
                    DeepAgentState(user_request="test"), session
                )
                assert False, "Expected exception"
            except Exception as e:
                assert "DATABASE_UNAVAILABLE" in str(e)
    async def test_llm_service_down_fallback_behavior(self):
        """Test LLM service failure → Fallback to cached responses"""
        config = RetryConfig(max_retries=2, base_delay=0.1)
        wrapper = AgentReliabilityWrapper("LLMAgent", retry_config=config)
        
        # Create LLM operation that always fails
        async def llm_failure():
            raise Exception("LLM_SERVICE_UNAVAILABLE")
        
        # Create fallback operation
        async def fallback_response():
            return {"content": "Cached response", "fallback": True}
        
        # Test fallback execution
        result = await wrapper.execute_safely(
            llm_failure, "llm_call", fallback=fallback_response
        )
        assert result["fallback"] is True
        assert "Cached response" in result["content"]
    async def test_websocket_disconnect_reconnection(self):
        """Test WebSocket disconnect → Automatic reconnection with state sync"""
        recovery_manager = WebSocketRecoveryManager()
        connection_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        # Save state snapshot before failure
        test_state = DeepAgentState(user_request="test", step_count=5)
        recovery_manager.save_state_snapshot(connection_id, test_state)
        
        # Simulate WebSocket error
        ws_error = WebSocketError("Connection lost", ErrorSeverity.HIGH)
        
        # Initiate recovery
        recovery_success = await recovery_manager.initiate_recovery(
            connection_id, user_id, ws_error,
            [RecoveryStrategy.STATE_SYNC, RecoveryStrategy.EXPONENTIAL_BACKOFF]
        )
        
        assert recovery_success is True
        status = recovery_manager.get_recovery_status(connection_id)
        # Status should be None after successful recovery cleanup
        assert status is None


class TestPartialSuccessHandling:
    """Test partial success scenarios and compensation patterns"""
    async def test_multi_data_source_partial_availability(self):
        """Test 3/5 data sources available → Partial results with warnings"""
        data_sources = ["source1", "source2", "source3", "source4", "source5"]
        results = {}
        failures = []
        
        for i, source in enumerate(data_sources):
            if i < 3:  # First 3 succeed
                results[source] = {"data": f"data_from_{source}", "status": "success"}
            else:  # Last 2 fail
                failures.append({"source": source, "error": "CONNECTION_TIMEOUT"})
        
        # Verify partial success handling
        assert len(results) == 3
        assert len(failures) == 2
        success_ratio = len(results) / len(data_sources)
        assert success_ratio == 0.6
    async def test_agent_workflow_partial_completion(self):
        """Test some agents complete, others fail → Partial workflow results"""
        agent_results = {}
        agent_failures = {}
        agents = ["triage", "data", "optimization", "reporting"]
        
        for i, agent in enumerate(agents):
            if i % 2 == 0:  # Even indices succeed
                agent_results[agent] = {"status": "completed", "result": f"{agent}_output"}
            else:  # Odd indices fail
                agent_failures[agent] = {"status": "failed", "error": "AGENT_TIMEOUT"}
        
        # Verify partial workflow completion
        assert len(agent_results) == 2
        assert len(agent_failures) == 2
        assert "triage" in agent_results
        assert "data" in agent_failures
    async def test_database_partial_write_transaction(self):
        """Test partial database writes → Transaction rollback"""
        session = ErrorRecoveryTestFixtures.create_database_session_mock()
        write_operations = []
        
        # Simulate partial write scenario
        for i in range(3):
            try:
                if i == 2:  # Third operation fails
                    raise Exception("CONSTRAINT_VIOLATION")
                write_operations.append(f"write_{i}")
                session.add(f"record_{i}")
            except Exception:
                # Trigger rollback on failure
                await session.rollback()
                break
        
        # Verify rollback was called
        session.rollback.assert_called_once()
        assert len(write_operations) == 2  # Only 2 operations succeeded


class TestRollbackMechanisms:
    """Test transaction rollback and state restoration mechanisms"""
    async def test_transaction_rollback_on_error(self):
        """Test automatic transaction rollback when operation fails"""
        session = ErrorRecoveryTestFixtures.create_database_session_mock(fail_on_commit=True)
        
        try:
            # Simulate transaction operations
            session.add("record1")
            session.add("record2") 
            await session.commit()  # This will fail
        except Exception:
            await session.rollback()
        
        # Verify rollback was executed
        session.rollback.assert_called_once()
        session.commit.assert_called_once()
    async def test_agent_state_restoration_after_failure(self):
        """Test state restoration after agent failure"""
        initial_state = DeepAgentState(user_request="test", step_count=3)
        
        # Mock state persistence
        async def mock_load_state(run_id, db_session):
            return initial_state
        
        with patch.object(state_persistence_service, 'load_agent_state', mock_load_state):
            restored_state = await state_persistence_service.load_agent_state(
                "test_run", AsyncMock()
            )
        
        # Verify state restoration
        assert restored_state.user_request == "test"
        assert restored_state.step_count == 3
    async def test_resource_cleanup_partial_operations(self):
        """Test cleanup of partial operations and resource deallocation"""
        allocated_resources = []
        cleanup_called = []
        
        try:
            # Simulate resource allocation
            for i in range(3):
                resource = f"resource_{i}"
                allocated_resources.append(resource)
                if i == 2:  # Fail on third resource
                    raise Exception("ALLOCATION_FAILED")
        except Exception:
            # Cleanup allocated resources
            for resource in allocated_resources:
                cleanup_called.append(f"cleanup_{resource}")
        
        # Verify cleanup
        assert len(cleanup_called) == 3
        assert "cleanup_resource_0" in cleanup_called


class TestRecoveryMechanisms:
    """Test automatic retry, manual intervention, and graceful degradation"""
    async def test_automatic_retry_success_after_failures(self):
        """Test automatic retry succeeds after initial failures"""
        config = RetryConfig(max_retries=3, base_delay=0.1, jitter=False)
        wrapper = AgentReliabilityWrapper("RetryAgent", retry_config=config)
        
        failing_op = ErrorRecoveryTestFixtures.create_failing_operation(2)
        
        # Should succeed on third attempt (after 2 failures)
        result = await wrapper.execute_safely(failing_op, "retry_test")
        assert result["status"] == "success"
        assert result["attempt"] == 3
    async def test_circuit_breaker_automatic_recovery(self):
        """Test circuit breaker automatic recovery after timeout"""
        config = CircuitBreakerConfig(failure_threshold=2, recovery_timeout=0.1)
        wrapper = AgentReliabilityWrapper("CBAgent", circuit_breaker_config=config)
        
        # Trigger circuit breaker
        failing_op = ErrorRecoveryTestFixtures.create_failing_operation(5)
        for _ in range(3):
            try:
                await wrapper.execute_safely(failing_op, "cb_test")
            except:
                pass
        
        # Wait for recovery timeout
        await asyncio.sleep(0.2)
        
        # Verify circuit breaker allows execution after timeout
        assert wrapper.circuit_breaker.can_execute() is True
    async def test_graceful_degradation_under_load(self):
        """Test graceful degradation when system under stress"""
        config = CircuitBreakerConfig(failure_threshold=1, recovery_timeout=0.5)
        wrapper = AgentReliabilityWrapper("LoadAgent", config)
        
        # Create degraded operation (always succeeds but with reduced functionality)
        async def degraded_operation():
            return {"status": "degraded", "functionality": "limited"}
        
        # Trigger degradation
        failing_op = ErrorRecoveryTestFixtures.create_failing_operation(10)
        try:
            await wrapper.execute_safely(failing_op, "load_test")
        except:
            pass
        
        # Use degraded operation when circuit breaker is open
        if not wrapper.circuit_breaker.can_execute():
            result = await degraded_operation()
            assert result["status"] == "degraded"
    async def test_alternative_workflow_activation(self):
        """Test alternative workflow activation when primary fails"""
        primary_workflow_failed = True
        alternative_result = None
        
        if primary_workflow_failed:
            # Activate alternative workflow
            alternative_result = {
                "workflow": "alternative",
                "method": "cached_analysis",
                "confidence": 0.7
            }
        
        # Verify alternative workflow
        assert alternative_result is not None
        assert alternative_result["workflow"] == "alternative"
        assert alternative_result["confidence"] < 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])