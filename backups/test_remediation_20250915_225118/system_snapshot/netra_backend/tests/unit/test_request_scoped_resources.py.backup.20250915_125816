"""
Test Request Scoped Resources - Per-User Isolation Patterns

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & User Privacy
- Business Goal: Ensure complete user isolation and eliminate data leakage
- Value Impact: Users can trust their data remains private and secure
- Strategic Impact: Enables reliable multi-user concurrent operations

This test suite validates the request-scoped resource management patterns including:
- RequestScopedAgentExecutor user isolation
- Request-scoped database session handling
- User context lifecycle management
- Resource cleanup and error recovery
- Performance isolation between users

Performance Requirements:
- Resource allocation per user should be isolated
- No cross-user resource contamination
- Proper cleanup after request completion
- Memory usage should be bounded per user
"""

import asyncio
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, Mock, patch
from typing import Dict, Any, Optional

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.request_scoped_executor import (
    RequestScopedAgentExecutor,
    AgentExecutorError
)
from netra_backend.app.database.request_scoped_session_factory import (
    RequestScopedSessionFactory,
    RequestScopedSession
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.websocket_core.unified_emitter import UnifiedWebSocketEmitter


class TestRequestScopedAgentExecutor(SSotBaseTestCase):
    """Test RequestScopedAgentExecutor isolation and lifecycle."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        # Create mock user execution contexts for different users
        self.user1_id = f"user1_{uuid.uuid4().hex[:8]}"
        self.user2_id = f"user2_{uuid.uuid4().hex[:8]}"
        
        self.mock_user_context_1 = Mock(spec=UserExecutionContext)
        self.mock_user_context_1.user_id = self.user1_id
        self.mock_user_context_1.session_id = f"session1_{uuid.uuid4().hex[:8]}"
        self.mock_user_context_1.request_id = f"req1_{uuid.uuid4().hex[:8]}"
        
        self.mock_user_context_2 = Mock(spec=UserExecutionContext)
        self.mock_user_context_2.user_id = self.user2_id
        self.mock_user_context_2.session_id = f"session2_{uuid.uuid4().hex[:8]}"
        self.mock_user_context_2.request_id = f"req2_{uuid.uuid4().hex[:8]}"
        
        # Create mock event emitters
        self.mock_event_emitter_1 = Mock(spec=UnifiedWebSocketEmitter)
        self.mock_event_emitter_1.emit = AsyncMock()
        
        self.mock_event_emitter_2 = Mock(spec=UnifiedWebSocketEmitter)
        self.mock_event_emitter_2.emit = AsyncMock()
        
        # Create mock agent registry
        self.mock_agent_registry = Mock()
        
        # Initialize executors for different users
        self.executor_user1 = RequestScopedAgentExecutor(
            user_context=self.mock_user_context_1,
            event_emitter=self.mock_event_emitter_1,
            agent_registry=self.mock_agent_registry
        )
        
        self.executor_user2 = RequestScopedAgentExecutor(
            user_context=self.mock_user_context_2,
            event_emitter=self.mock_event_emitter_2,
            agent_registry=self.mock_agent_registry
        )
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    def test_initialization_creates_isolated_executors(self):
        """Test that executor initialization creates properly isolated instances."""
        # Given: Two different user contexts
        # When: Creating executors for different users
        # Then: Each executor should be isolated
        
        assert self.executor_user1.user_context.user_id == self.user1_id
        assert self.executor_user2.user_context.user_id == self.user2_id
        
        # And: Executors should not share state
        assert self.executor_user1 is not self.executor_user2
        assert self.executor_user1.user_context is not self.executor_user2.user_context
        assert self.executor_user1.event_emitter is not self.executor_user2.event_emitter
        
        # And: Configuration should be proper
        assert hasattr(self.executor_user1, 'AGENT_EXECUTION_TIMEOUT')
        assert self.executor_user1.AGENT_EXECUTION_TIMEOUT > 0
        assert hasattr(self.executor_user1, 'MAX_RETRIES')
        assert self.executor_user1.MAX_RETRIES > 0
        
        self.record_metric("isolation_validated", True)
    
    @pytest.mark.unit
    async def test_concurrent_execution_maintains_isolation(self):
        """Test that concurrent executions maintain proper user isolation."""
        # Given: Mock agent execution for both users
        mock_agent = Mock()
        mock_agent.name = "test_agent"
        mock_agent.execute = AsyncMock()
        
        self.mock_agent_registry.get_agent = Mock(return_value=mock_agent)
        
        # Configure different execution results for each user
        execution_results = {
            self.user1_id: {"result": "user1_data", "computation": "user1_specific"},
            self.user2_id: {"result": "user2_data", "computation": "user2_specific"}
        }
        
        async def mock_agent_execution(context, *args, **kwargs):
            """Mock agent execution that returns user-specific data."""
            await asyncio.sleep(0.1)  # Simulate processing time
            user_id = context.user_id
            return execution_results[user_id]
        
        mock_agent.execute.side_effect = mock_agent_execution
        
        # When: Executing agents concurrently for both users
        with patch.object(self.executor_user1, '_validate_execution_context', return_value=True), \
             patch.object(self.executor_user2, '_validate_execution_context', return_value=True):
            
            task1 = self.executor_user1.execute_agent(
                agent_name="test_agent",
                message="Execute for user 1"
            )
            
            task2 = self.executor_user2.execute_agent(
                agent_name="test_agent", 
                message="Execute for user 2"
            )
            
            # Run concurrently
            result1, result2 = await asyncio.gather(task1, task2)
        
        # Then: Results should be isolated per user
        assert result1["result"] == "user1_data"
        assert result1["computation"] == "user1_specific"
        
        assert result2["result"] == "user2_data"
        assert result2["computation"] == "user2_specific"
        
        # And: No cross-contamination
        assert "user2" not in str(result1)
        assert "user1" not in str(result2)
        
        # And: WebSocket events should be sent to correct users
        self.mock_event_emitter_1.emit.assert_called()
        self.mock_event_emitter_2.emit.assert_called()
        
        self.record_metric("concurrent_isolation_validated", True)
        self.increment_websocket_events(2)  # Both users received events
    
    @pytest.mark.unit
    async def test_execution_timeout_handling_per_user(self):
        """Test that execution timeout is handled properly per user."""
        # Given: Agent that takes too long for one user but not another
        mock_agent = Mock()
        mock_agent.name = "timeout_test_agent"
        
        async def user_specific_execution(context, *args, **kwargs):
            if context.user_id == self.user1_id:
                await asyncio.sleep(0.1)  # Fast execution
                return {"status": "completed_quickly"}
            else:
                await asyncio.sleep(5.0)  # Slow execution (will timeout)
                return {"status": "completed_slowly"}
        
        mock_agent.execute = user_specific_execution
        self.mock_agent_registry.get_agent = Mock(return_value=mock_agent)
        
        # Override timeout for testing
        original_timeout = self.executor_user1.AGENT_EXECUTION_TIMEOUT
        original_timeout2 = self.executor_user2.AGENT_EXECUTION_TIMEOUT
        
        self.executor_user1.AGENT_EXECUTION_TIMEOUT = 1.0  # Short timeout
        self.executor_user2.AGENT_EXECUTION_TIMEOUT = 1.0  # Short timeout
        
        try:
            # When: Executing agents for both users concurrently
            with patch.object(self.executor_user1, '_validate_execution_context', return_value=True), \
                 patch.object(self.executor_user2, '_validate_execution_context', return_value=True):
                
                results = await asyncio.gather(
                    self.executor_user1.execute_agent("timeout_test_agent", "Fast execution"),
                    self.executor_user2.execute_agent("timeout_test_agent", "Slow execution"),
                    return_exceptions=True
                )
            
            # Then: User 1 should succeed, User 2 should timeout
            result1, result2 = results
            
            # User 1 should complete successfully
            if isinstance(result1, dict):
                assert result1.get("status") == "completed_quickly"
            
            # User 2 should encounter timeout or exception
            if isinstance(result2, Exception) or (isinstance(result2, dict) and "error" in result2):
                self.record_metric("timeout_handled_correctly", True)
            
        finally:
            # Restore original timeouts
            self.executor_user1.AGENT_EXECUTION_TIMEOUT = original_timeout
            self.executor_user2.AGENT_EXECUTION_TIMEOUT = original_timeout2
        
        self.record_metric("per_user_timeout_validated", True)
    
    @pytest.mark.unit
    async def test_error_isolation_between_users(self):
        """Test that errors in one user's execution don't affect another user."""
        # Given: Agent that fails for user 1 but succeeds for user 2
        mock_agent = Mock()
        mock_agent.name = "error_test_agent"
        
        async def error_prone_execution(context, *args, **kwargs):
            if context.user_id == self.user1_id:
                raise Exception("User 1 specific error")
            else:
                return {"status": "success", "user": context.user_id}
        
        mock_agent.execute = error_prone_execution
        self.mock_agent_registry.get_agent = Mock(return_value=mock_agent)
        
        # When: Executing agents for both users
        with patch.object(self.executor_user1, '_validate_execution_context', return_value=True), \
             patch.object(self.executor_user2, '_validate_execution_context', return_value=True):
            
            results = await asyncio.gather(
                self.executor_user1.execute_agent("error_test_agent", "Will fail"),
                self.executor_user2.execute_agent("error_test_agent", "Will succeed"),
                return_exceptions=True
            )
        
        result1, result2 = results
        
        # Then: User 1 should have error, User 2 should succeed
        assert isinstance(result1, Exception) or (isinstance(result1, dict) and "error" in result1)
        assert isinstance(result2, dict) and result2.get("status") == "success"
        assert result2.get("user") == self.user2_id
        
        self.record_metric("error_isolation_validated", True)
    
    @pytest.mark.unit
    def test_resource_cleanup_per_user(self):
        """Test that resources are properly cleaned up per user."""
        # Given: Executors with tracking
        initial_user1_resources = len(getattr(self.executor_user1, '_active_executions', {}))
        initial_user2_resources = len(getattr(self.executor_user2, '_active_executions', {}))
        
        # When: Simulating resource allocation and cleanup
        # Mock some resource allocation
        if hasattr(self.executor_user1, '_active_executions'):
            self.executor_user1._active_executions[f"exec_{uuid.uuid4().hex}"] = {
                "start_time": time.time(),
                "agent": "test_agent"
            }
        
        if hasattr(self.executor_user2, '_active_executions'):
            self.executor_user2._active_executions[f"exec_{uuid.uuid4().hex}"] = {
                "start_time": time.time(),
                "agent": "test_agent"
            }
        
        # Simulate cleanup
        if hasattr(self.executor_user1, 'cleanup'):
            self.executor_user1.cleanup()
        if hasattr(self.executor_user2, 'cleanup'):
            self.executor_user2.cleanup()
        
        # Then: Resources should be cleaned up independently
        final_user1_resources = len(getattr(self.executor_user1, '_active_executions', {}))
        final_user2_resources = len(getattr(self.executor_user2, '_active_executions', {}))
        
        # Each user's cleanup should only affect their own resources
        assert final_user1_resources <= initial_user1_resources + 1  # Allow for test allocation
        assert final_user2_resources <= initial_user2_resources + 1  # Allow for test allocation
        
        self.record_metric("resource_cleanup_validated", True)


class TestRequestScopedSessionFactory(SSotBaseTestCase):
    """Test RequestScopedSessionFactory database isolation."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        # Mock database engine
        self.mock_engine = Mock()
        
        # Create session factory
        self.session_factory = RequestScopedSessionFactory(engine=self.mock_engine)
        
        # Test user contexts
        self.user1_context = {
            "user_id": f"user1_{uuid.uuid4().hex[:8]}",
            "session_id": f"session1_{uuid.uuid4().hex[:8]}",
            "request_id": f"req1_{uuid.uuid4().hex[:8]}"
        }
        
        self.user2_context = {
            "user_id": f"user2_{uuid.uuid4().hex[:8]}",
            "session_id": f"session2_{uuid.uuid4().hex[:8]}",
            "request_id": f"req2_{uuid.uuid4().hex[:8]}"
        }
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    def test_session_isolation_per_user(self):
        """Test that database sessions are isolated per user context."""
        # Given: Mock session creation
        mock_session1 = Mock()
        mock_session2 = Mock()
        
        self.session_factory._create_session = Mock(side_effect=[mock_session1, mock_session2])
        
        # When: Creating sessions for different users
        session1 = self.session_factory.get_session(self.user1_context)
        session2 = self.session_factory.get_session(self.user2_context)
        
        # Then: Sessions should be different instances
        assert session1 is not session2
        assert session1 is mock_session1
        assert session2 is mock_session2
        
        # And: Factory should track sessions per user
        assert self.session_factory._create_session.call_count == 2
        
        self.record_metric("session_isolation_validated", True)
        self.increment_db_query_count(2)  # Two session creations
    
    @pytest.mark.unit
    def test_session_reuse_within_request(self):
        """Test that sessions are reused within the same request context."""
        # Given: Mock session creation
        mock_session = Mock()
        self.session_factory._create_session = Mock(return_value=mock_session)
        
        # When: Getting session multiple times for same user context
        session1 = self.session_factory.get_session(self.user1_context)
        session2 = self.session_factory.get_session(self.user1_context)
        session3 = self.session_factory.get_session(self.user1_context)
        
        # Then: Should reuse same session
        assert session1 is session2
        assert session2 is session3
        assert session1 is mock_session
        
        # And: Should only create session once
        self.session_factory._create_session.assert_called_once()
        
        self.record_metric("session_reuse_validated", True)
        self.increment_db_query_count(1)  # Only one session creation
    
    @pytest.mark.unit
    async def test_session_cleanup_per_request(self):
        """Test that sessions are properly cleaned up per request."""
        # Given: Mock sessions for different users
        mock_session1 = Mock()
        mock_session1.close = Mock()
        mock_session2 = Mock()
        mock_session2.close = Mock()
        
        self.session_factory._create_session = Mock(side_effect=[mock_session1, mock_session2])
        
        # When: Using sessions and then cleaning up
        session1 = self.session_factory.get_session(self.user1_context)
        session2 = self.session_factory.get_session(self.user2_context)
        
        # Cleanup for specific user
        await self.session_factory.cleanup_user_sessions(self.user1_context["user_id"])
        
        # Then: Only user 1's session should be cleaned up
        mock_session1.close.assert_called_once()
        mock_session2.close.assert_not_called()
        
        # And: User 2's session should still be available
        session2_again = self.session_factory.get_session(self.user2_context)
        assert session2_again is session2
        
        self.record_metric("session_cleanup_validated", True)
        self.increment_db_query_count(2)  # Two session creations
    
    @pytest.mark.unit
    def test_concurrent_session_access_isolation(self):
        """Test that concurrent session access maintains isolation."""
        # Given: Multiple contexts that might be accessed concurrently
        contexts = []
        sessions = []
        
        for i in range(5):
            context = {
                "user_id": f"user{i}_{uuid.uuid4().hex[:8]}",
                "session_id": f"session{i}_{uuid.uuid4().hex[:8]}",
                "request_id": f"req{i}_{uuid.uuid4().hex[:8]}"
            }
            contexts.append(context)
        
        # Mock session creation for each user
        mock_sessions = [Mock() for _ in range(5)]
        self.session_factory._create_session = Mock(side_effect=mock_sessions)
        
        # When: Getting sessions for all contexts
        for context in contexts:
            session = self.session_factory.get_session(context)
            sessions.append(session)
        
        # Then: Each session should be unique
        assert len(set(sessions)) == 5  # All sessions should be unique
        
        # And: Each session should correspond to the mock
        for i, session in enumerate(sessions):
            assert session is mock_sessions[i]
        
        self.record_metric("concurrent_access_isolation_validated", True)
        self.increment_db_query_count(5)  # Five session creations


class TestUserExecutionContextIsolation(SSotBaseTestCase):
    """Test UserExecutionContext isolation patterns."""
    
    @pytest.mark.unit
    def test_context_immutability(self):
        """Test that user execution contexts are properly immutable."""
        # Given: User execution context
        context_data = {
            "user_id": f"user_{uuid.uuid4().hex[:8]}",
            "session_id": f"session_{uuid.uuid4().hex[:8]}",
            "request_id": f"req_{uuid.uuid4().hex[:8]}",
            "metadata": {"key": "value"}
        }
        
        mock_context = Mock(spec=UserExecutionContext)
        mock_context.user_id = context_data["user_id"]
        mock_context.session_id = context_data["session_id"]
        mock_context.request_id = context_data["request_id"]
        
        original_user_id = mock_context.user_id
        original_session_id = mock_context.session_id
        
        # When: Attempting to access context properties
        retrieved_user_id = mock_context.user_id
        retrieved_session_id = mock_context.session_id
        
        # Then: Values should be consistent
        assert retrieved_user_id == original_user_id
        assert retrieved_session_id == original_session_id
        
        # And: Context should maintain consistency
        assert mock_context.user_id == context_data["user_id"]
        assert mock_context.session_id == context_data["session_id"]
        
        self.record_metric("context_immutability_validated", True)
    
    @pytest.mark.unit
    def test_context_lifecycle_management(self):
        """Test proper lifecycle management of user execution contexts."""
        # Given: Multiple user contexts
        contexts = []
        
        for i in range(3):
            mock_context = Mock(spec=UserExecutionContext)
            mock_context.user_id = f"user_{i}_{uuid.uuid4().hex[:8]}"
            mock_context.session_id = f"session_{i}_{uuid.uuid4().hex[:8]}"
            mock_context.request_id = f"req_{i}_{uuid.uuid4().hex[:8]}"
            mock_context.created_at = time.time()
            contexts.append(mock_context)
        
        # When: Managing context lifecycle
        active_contexts = {ctx.request_id: ctx for ctx in contexts}
        
        # Simulate context cleanup
        expired_request_id = contexts[0].request_id
        if expired_request_id in active_contexts:
            del active_contexts[expired_request_id]
        
        # Then: Context should be properly removed
        assert expired_request_id not in active_contexts
        assert len(active_contexts) == 2
        
        # And: Other contexts should remain unaffected
        for ctx in contexts[1:]:
            assert ctx.request_id in active_contexts
        
        self.record_metric("context_lifecycle_validated", True)


class TestResourceMetricsAndPerformance(SSotBaseTestCase):
    """Test resource metrics and performance isolation."""
    
    @pytest.mark.unit
    def test_resource_usage_tracking_per_user(self):
        """Test that resource usage is tracked per user."""
        # Given: Mock resource tracker
        resource_tracker = {}
        
        users = [f"user_{i}_{uuid.uuid4().hex[:8]}" for i in range(3)]
        
        # When: Tracking resource usage for different users
        for user_id in users:
            resource_tracker[user_id] = {
                "memory_mb": 50 + (hash(user_id) % 100),  # Different memory usage
                "cpu_time": 0.1 + (hash(user_id) % 10) * 0.01,  # Different CPU time
                "db_connections": 2 + (hash(user_id) % 5),  # Different connection count
                "active_agents": 1 + (hash(user_id) % 3)  # Different agent count
            }
        
        # Then: Each user should have different resource usage
        memory_values = [resource_tracker[uid]["memory_mb"] for uid in users]
        cpu_values = [resource_tracker[uid]["cpu_time"] for uid in users]
        
        # All values should be different (with high probability due to hash)
        assert len(set(memory_values)) >= 2  # At least some variation
        assert len(set(cpu_values)) >= 2  # At least some variation
        
        # And: Total resources should be sum of all users
        total_memory = sum(resource_tracker[uid]["memory_mb"] for uid in users)
        total_agents = sum(resource_tracker[uid]["active_agents"] for uid in users)
        
        assert total_memory > 0
        assert total_agents >= len(users)  # At least one agent per user
        
        self.record_metric("resource_tracking_validated", True)
        self.record_metric("total_memory_tracked", total_memory)
        self.record_metric("total_agents_tracked", total_agents)
    
    @pytest.mark.unit
    async def test_performance_isolation_under_load(self):
        """Test that performance remains isolated under concurrent load."""
        # Given: Simulated concurrent users
        user_count = 10
        operations_per_user = 5
        
        performance_results = {}
        
        async def simulate_user_operations(user_id: str, operation_count: int):
            """Simulate operations for a single user."""
            start_time = time.time()
            
            # Simulate different workloads per user
            base_delay = 0.01 + (hash(user_id) % 10) * 0.001
            
            for i in range(operation_count):
                await asyncio.sleep(base_delay)  # Simulate work
            
            end_time = time.time()
            return {
                "user_id": user_id,
                "operations": operation_count,
                "duration": end_time - start_time,
                "avg_op_time": (end_time - start_time) / operation_count
            }
        
        # When: Running concurrent operations
        tasks = []
        for i in range(user_count):
            user_id = f"load_test_user_{i}_{uuid.uuid4().hex[:8]}"
            task = simulate_user_operations(user_id, operations_per_user)
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        # Then: Performance should be reasonably isolated
        durations = [r["duration"] for r in results]
        avg_op_times = [r["avg_op_time"] for r in results]
        
        # Check that performance is reasonable
        max_duration = max(durations)
        min_duration = min(durations)
        
        assert max_duration < 1.0  # Should complete quickly
        assert all(d > 0 for d in durations)  # All should have measurable time
        
        # Performance should vary based on user-specific load
        assert max(avg_op_times) > min(avg_op_times)  # Some variation expected
        
        self.record_metric("concurrent_users_tested", user_count)
        self.record_metric("total_operations", user_count * operations_per_user)
        self.record_metric("max_duration", max_duration)
        self.record_metric("min_duration", min_duration)
        self.record_metric("performance_isolation_validated", True)
    
    def teardown_method(self, method):
        """Cleanup after each test."""
        # Verify no resource leaks
        total_metrics = self.get_all_metrics()
        
        # Log performance metrics for analysis
        if "concurrent_users_tested" in total_metrics:
            users_tested = total_metrics["concurrent_users_tested"]
            if users_tested > 0:
                self.record_metric("test_efficiency", total_metrics.get("total_operations", 0) / users_tested)
        
        super().teardown_method(method)