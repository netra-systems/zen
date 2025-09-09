"""
WebSocket Timeout Optimization Validation Tests

CRITICAL: Validates the secondary timeout fixes that resolve 60s/120s WebSocket latency patterns.
After fixing the primary 179s auth timeout, this test ensures all remaining timeout sources
are optimized for <5s WebSocket responsiveness.

Business Value: $30K+ MRR chat functionality requires <5s response times for user experience.
"""

import pytest
import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from netra_backend.app.agents.base_agent import BaseAgent
from netra_backend.app.core.agent_execution_tracker import AgentExecutionTracker
from netra_backend.app.database.request_scoped_session_factory import RequestScopedSessionFactory
from netra_backend.app.database import get_engine
from test_framework.ssot.e2e_auth_helper import E2EWebSocketAuthHelper
from test_framework.websocket_helpers import WebSocketTestClient


class TestWebSocketTimeoutOptimization:
    """Test suite for WebSocket timeout optimization validation."""
    
    @pytest.mark.asyncio
    async def test_agent_circuit_breaker_timeout_optimized(self):
        """Verify agent circuit breaker timeout reduced from 60s to 10s."""
        # Create base agent and verify circuit breaker timeout
        agent = BaseAgent(name="TestAgent")
        
        # CRITICAL: Circuit breaker timeout must be 10s, not 60s
        assert agent.circuit_breaker.recovery_timeout_seconds == 10, (
            f"Circuit breaker timeout should be 10s for WebSocket optimization, "
            f"got {agent.circuit_breaker.recovery_timeout_seconds}s"
        )
        
        # Verify reliability manager timeout also optimized
        if agent._reliability_manager_instance:
            assert agent._reliability_manager_instance.recovery_timeout == 10, (
                f"Reliability manager timeout should be 10s, "
                f"got {agent._reliability_manager_instance.recovery_timeout}s"
            )
    
    @pytest.mark.asyncio
    async def test_agent_execution_timeout_optimized(self):
        """Verify agent execution timeout reduced from 30s to 15s."""
        tracker = AgentExecutionTracker()
        
        # CRITICAL: Execution timeout must be 15s, not 30s
        assert tracker.execution_timeout == 15, (
            f"Agent execution timeout should be 15s for WebSocket optimization, "
            f"got {tracker.execution_timeout}s"
        )
        
        # Test execution record also uses optimized timeout
        execution_id = tracker.create_execution(
            agent_name="TestAgent",
            thread_id="test_thread_123",
            user_id="test_user_456"
        )
        
        execution = tracker._executions[execution_id]
        assert execution.timeout_seconds == 15, (
            f"Execution record timeout should be 15s, got {execution.timeout_seconds}s"
        )
    
    @pytest.mark.asyncio
    async def test_database_session_lifetime_optimized(self):
        """Verify database session lifetime reduced from 5min to 30s."""
        factory = RequestScopedSessionFactory()
        
        # CRITICAL: Session lifetime must be 30s, not 5 minutes
        assert factory._max_session_lifetime_ms == 30000, (
            f"Database session lifetime should be 30s (30000ms) for WebSocket optimization, "
            f"got {factory._max_session_lifetime_ms}ms"
        )
    
    @pytest.mark.asyncio
    async def test_database_connection_pool_optimization(self):
        """Verify database engine uses QueuePool with optimized settings."""
        engine = get_engine()
        
        # CRITICAL: Must use QueuePool, not NullPool
        from sqlalchemy.pool import QueuePool
        assert isinstance(engine.pool, QueuePool), (
            f"Database engine should use QueuePool for connection reuse, "
            f"got {type(engine.pool).__name__}"
        )
        
        # Verify pool configuration
        pool = engine.pool
        assert pool.size() == 5, f"Pool size should be 5, got {pool.size()}"
        assert pool.timeout() == 5, f"Pool timeout should be 5s, got {pool.timeout()}s"
    
    @pytest.mark.asyncio
    async def test_websocket_timeout_cascade_prevention(self):
        """Test that WebSocket operations complete within 5s timeout."""
        auth_helper = E2EWebSocketAuthHelper(environment="test")
        user_id = "timeout_test_user"
        token = auth_helper.create_test_jwt_token(user_id=user_id)
        
        websocket_url = "ws://localhost:8000/ws"
        
        # CRITICAL: WebSocket operations must complete within 5s
        start_time = time.time()
        
        try:
            async with WebSocketTestClient(websocket_url, user_id) as ws_client:
                # Send a simple message and get response
                test_message = {
                    "type": "agent_execution",
                    "data": {
                        "message": "Quick test for timeout optimization",
                        "agent_type": "simple_response"
                    }
                }
                
                await ws_client.send_json(test_message)
                
                # Wait for response with 5s timeout
                response = await asyncio.wait_for(
                    ws_client.receive_json(),
                    timeout=5.0
                )
                
                elapsed = time.time() - start_time
                
                # CRITICAL: Must complete within 5s for user experience
                assert elapsed < 5.0, (
                    f"WebSocket operation took {elapsed:.2f}s, must be <5s for optimization"
                )
                
                # Verify we got a valid response
                assert response is not None, "Should receive response within timeout"
                
        except asyncio.TimeoutError:
            elapsed = time.time() - start_time
            pytest.fail(f"WebSocket operation timed out after {elapsed:.2f}s, violates <5s requirement")
    
    @pytest.mark.asyncio
    async def test_circuit_breaker_fast_recovery(self):
        """Test circuit breaker recovers quickly without blocking WebSocket."""
        agent = BaseAgent(name="CircuitBreakerTest")
        
        # Force circuit breaker to open
        for _ in range(5):  # failure_threshold is 5
            try:
                await agent.circuit_breaker._circuit_breaker.call(self._failing_operation)
            except Exception:
                pass  # Expected failures
        
        # Verify circuit breaker is open
        assert agent.circuit_breaker._circuit_breaker.current_state == "open"
        
        # CRITICAL: Circuit breaker should transition to half-open in 10s, not 60s
        start_time = time.time()
        
        # Wait for circuit breaker to transition to half-open
        while (agent.circuit_breaker._circuit_breaker.current_state == "open" and 
               time.time() - start_time < 15):  # Max 15s wait
            await asyncio.sleep(0.1)
        
        elapsed = time.time() - start_time
        
        # CRITICAL: Should transition within 10s timeout + small buffer
        assert elapsed < 12, (
            f"Circuit breaker took {elapsed:.2f}s to recover, "
            f"should be ~10s for WebSocket optimization"
        )
        
        assert agent.circuit_breaker._circuit_breaker.current_state == "half_open", (
            f"Circuit breaker should be half-open after recovery timeout, "
            f"got {agent.circuit_breaker._circuit_breaker.current_state}"
        )
    
    async def _failing_operation(self):
        """Helper method that always fails."""
        raise RuntimeError("Simulated failure for circuit breaker test")
    
    @pytest.mark.asyncio
    async def test_database_session_cleanup_speed(self):
        """Test database session cleanup happens quickly to prevent pool exhaustion."""
        factory = RequestScopedSessionFactory()
        user_id = "session_cleanup_test"
        
        start_time = time.time()
        
        # Create and immediately close session
        async with factory.get_request_scoped_session(user_id) as session:
            # Perform minimal database operation
            from sqlalchemy import text
            await session.execute(text("SELECT 1"))
        
        # Session should be cleaned up quickly
        cleanup_time = time.time() - start_time
        
        # CRITICAL: Session cleanup should be fast to prevent WebSocket blocking
        assert cleanup_time < 2.0, (
            f"Database session cleanup took {cleanup_time:.2f}s, should be <2s "
            f"to prevent WebSocket blocking"
        )
        
        # Verify session was cleaned up
        assert len(factory._active_sessions) == 0, (
            f"Should have 0 active sessions after cleanup, got {len(factory._active_sessions)}"
        )
    
    @pytest.mark.asyncio
    async def test_agent_execution_timeout_fast_failure(self):
        """Test agent execution fails fast at 15s instead of 30s."""
        tracker = AgentExecutionTracker()
        
        # Create execution that will timeout
        execution_id = tracker.create_execution(
            agent_name="TimeoutAgent",
            thread_id="timeout_thread_123", 
            user_id="timeout_user_456",
            timeout_seconds=15  # Use optimized timeout
        )
        
        # Start tracking execution
        await tracker.start_monitoring()
        
        execution = tracker._executions[execution_id]
        
        # Simulate execution running for 16 seconds (past timeout)
        execution.started_at = datetime.now(timezone.utc) - asyncio.create_task(asyncio.sleep(0))
        await asyncio.sleep(0.1)  # Let monitoring cycle run
        
        # Manually check timeout since we can't wait 15 seconds in test
        from datetime import timedelta
        execution.started_at = datetime.now(timezone.utc) - timedelta(seconds=16)
        
        # CRITICAL: Should be detected as timed out
        assert execution.is_timed_out(), (
            f"Execution should be timed out after 16s with 15s timeout"
        )
        
        await tracker.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_connection_pool_prevents_timeout_cascade(self):
        """Test connection pool prevents timeout cascading to WebSocket operations."""
        # Get multiple database connections quickly
        engine = get_engine()
        connections_acquired = []
        
        start_time = time.time()
        
        try:
            # Rapidly acquire multiple connections (should use pool)
            for i in range(3):
                conn = await engine.connect()
                connections_acquired.append(conn)
                
                # Each connection should be fast due to pooling
                elapsed = time.time() - start_time
                assert elapsed < 2.0, (
                    f"Connection {i+1} took {elapsed:.2f}s total, "
                    f"pooling should keep this fast"
                )
            
            # Total time for all connections should be fast
            total_time = time.time() - start_time
            assert total_time < 3.0, (
                f"Acquiring 3 connections took {total_time:.2f}s, "
                f"should be <3s with connection pooling"
            )
            
        finally:
            # Clean up connections
            for conn in connections_acquired:
                await conn.close()
    
    @pytest.mark.asyncio
    async def test_timeout_configuration_constants(self):
        """Verify all timeout constants are set to optimized values."""
        # Agent circuit breaker timeout
        agent = BaseAgent(name="ConstantsTest")
        assert agent.circuit_breaker.recovery_timeout_seconds == 10
        
        # Agent execution timeout  
        tracker = AgentExecutionTracker()
        assert tracker.execution_timeout == 15
        
        # Database session lifetime
        factory = RequestScopedSessionFactory()
        assert factory._max_session_lifetime_ms == 30000
        
        # These values ensure WebSocket operations complete within 5s:
        # - Circuit breaker recovery: 10s (reduced from 60s)
        # - Agent execution timeout: 15s (reduced from 30s) 
        # - Database session lifetime: 30s (reduced from 5min)
        # - Connection pool timeout: 5s (new optimization)


if __name__ == "__main__":
    pytest.main([__file__])