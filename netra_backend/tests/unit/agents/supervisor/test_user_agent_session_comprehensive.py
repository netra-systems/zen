"""
Comprehensive Unit Tests for UserAgentSession

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise) 
- Business Goal: Prevent agent execution contamination between users - MISSION CRITICAL
- Value Impact: Ensures complete user isolation preventing security vulnerabilities
- Strategic Impact: Foundation for multi-user AI chat sessions - prevents data leakage

This test suite validates the UserAgentSession class, which provides complete user isolation
for agent execution. It ensures:
- User-scoped agent instances with proper isolation
- WebSocket bridge per user with factory pattern integration
- Memory leak prevention and resource cleanup
- Thread-safe concurrent execution for 10+ users
- Agent registry isolation patterns

CRITICAL SECURITY REQUIREMENTS:
UserAgentSession is the foundation that prevents user contamination in agent execution.
Any bugs here could cause catastrophic user data leakage between users.

Testing Philosophy:
- Real UserExecutionContext instances (not mocks for core business logic)
- Strongly typed IDs following SSOT patterns
- Comprehensive security isolation tests
- Memory management validation
- WebSocket integration without mocking core functionality
"""

import asyncio
import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import Mock, AsyncMock, MagicMock, patch
from typing import Dict, Any, Optional, List
import weakref
import gc
from collections import defaultdict

# Import SSOT test framework
from test_framework.ssot.base import BaseTestCase

# Import the class under test
from netra_backend.app.agents.supervisor.agent_registry import UserAgentSession

# Import related components for real testing
from netra_backend.app.services.user_execution_context import UserExecutionContext


class TestUserAgentSessionComprehensive(BaseTestCase):
    """Comprehensive test suite for UserAgentSession - MISSION CRITICAL for user isolation."""
    
    def setUp(self):
        """Set up test environment with clean state."""
        super().setUp()
        
        # Standard test data with proper user isolation
        self.test_user_id = "user_test_session_12345"
        self.test_user_id_2 = "user_test_session_67890" # For isolation tests
        self.test_agent_type = "triage_agent"
        self.test_agent_type_2 = "data_agent"
        
        # Mock agents for testing
        self.mock_agent_1 = Mock()
        self.mock_agent_1.cleanup = AsyncMock()
        self.mock_agent_1.close = AsyncMock()
        
        self.mock_agent_2 = Mock()  
        self.mock_agent_2.cleanup = AsyncMock()
        self.mock_agent_2.close = AsyncMock()
        
        # Mock WebSocket manager with bridge factory
        self.mock_websocket_manager = Mock()
        self.mock_websocket_bridge = Mock()
        self.mock_websocket_manager.create_bridge = AsyncMock(return_value=self.mock_websocket_bridge)
        
    def tearDown(self):
        """Clean up test environment."""
        # Force garbage collection to test memory leaks
        gc.collect()
        super().tearDown()

    # =========================================================================
    # INITIALIZATION AND BASIC FUNCTIONALITY TESTS
    # =========================================================================
    
    def test_basic_initialization_with_valid_user_id(self):
        """Test 1: Basic initialization with valid user ID."""
        session = UserAgentSession(self.test_user_id)
        
        # Verify required fields
        assert session.user_id == self.test_user_id
        assert isinstance(session._agents, dict)
        assert len(session._agents) == 0
        assert isinstance(session._execution_contexts, dict)
        assert len(session._execution_contexts) == 0
        assert session._websocket_bridge is None
        assert session._websocket_manager is None
        
        # Verify timestamp and lock
        assert isinstance(session._created_at, datetime)
        assert session._created_at.tzinfo is not None
        assert isinstance(session._access_lock, asyncio.Lock)
        
    def test_initialization_with_empty_user_id_raises_error(self):
        """Test 2: Initialization with empty user ID raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            UserAgentSession("")
            
    def test_initialization_with_none_user_id_raises_error(self):
        """Test 3: Initialization with None user ID raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            UserAgentSession(None)
            
    def test_initialization_with_non_string_user_id_raises_error(self):
        """Test 4: Initialization with non-string user ID raises ValueError."""
        with pytest.raises(ValueError, match="user_id must be a non-empty string"):
            UserAgentSession(12345)

    # =========================================================================
    # WEBSOCKET MANAGER INTEGRATION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_set_websocket_manager_with_default_context(self):
        """Test 5: Set WebSocket manager with auto-created user context."""
        session = UserAgentSession(self.test_user_id)
        
        await session.set_websocket_manager(self.mock_websocket_manager)
        
        # Verify WebSocket manager is set
        assert session._websocket_manager == self.mock_websocket_manager
        assert session._websocket_bridge == self.mock_websocket_bridge
        
        # Verify bridge was created with proper context
        self.mock_websocket_manager.create_bridge.assert_called_once()
        call_args = self.mock_websocket_manager.create_bridge.call_args[0]
        user_context = call_args[0]
        
        assert isinstance(user_context, UserExecutionContext)
        assert user_context.user_id == self.test_user_id
        assert f"session_{self.test_user_id}" in user_context.request_id
        assert f"thread_{self.test_user_id}" in user_context.thread_id
        
    @pytest.mark.asyncio 
    async def test_set_websocket_manager_with_provided_context(self):
        """Test 6: Set WebSocket manager with provided user context."""
        session = UserAgentSession(self.test_user_id)
        
        # Create explicit user context
        user_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id="custom_request_123",
            thread_id="custom_thread_456"
        )
        
        await session.set_websocket_manager(self.mock_websocket_manager, user_context)
        
        # Verify WebSocket manager integration
        assert session._websocket_manager == self.mock_websocket_manager
        assert session._websocket_bridge == self.mock_websocket_bridge
        
        # Verify bridge was created with the provided context
        self.mock_websocket_manager.create_bridge.assert_called_once_with(user_context)
        
    @pytest.mark.asyncio
    async def test_set_websocket_manager_with_sync_bridge_factory(self):
        """Test 7: Set WebSocket manager with synchronous bridge factory."""
        session = UserAgentSession(self.test_user_id)
        
        # Create sync bridge factory
        sync_manager = Mock()
        sync_manager.create_bridge = Mock(return_value=self.mock_websocket_bridge)
        
        await session.set_websocket_manager(sync_manager)
        
        # Verify sync bridge factory was called
        assert session._websocket_manager == sync_manager
        assert session._websocket_bridge == self.mock_websocket_bridge
        sync_manager.create_bridge.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_set_websocket_manager_falls_back_to_standard_factory(self):
        """Test 8: WebSocket manager without custom factory uses standard factory."""
        session = UserAgentSession(self.test_user_id)
        
        # Create manager without create_bridge method
        standard_manager = Mock(spec=[])  # No create_bridge method
        
        # Mock the standard factory
        with patch('netra_backend.app.agents.supervisor.agent_registry.create_agent_websocket_bridge') as mock_factory:
            mock_bridge = Mock()
            mock_factory.return_value = mock_bridge
            
            await session.set_websocket_manager(standard_manager)
            
            # Verify standard factory was used
            assert session._websocket_manager == standard_manager
            assert session._websocket_bridge == mock_bridge
            mock_factory.assert_called_once()

    # =========================================================================
    # AGENT EXECUTION CONTEXT CREATION TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_create_agent_execution_context_creates_child_context(self):
        """Test 9: Create agent execution context creates proper child context."""
        session = UserAgentSession(self.test_user_id)
        
        # Create parent context
        parent_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id="parent_request_123",
            thread_id="parent_thread_456"
        )
        
        # Create child context for agent
        child_context = await session.create_agent_execution_context(
            self.test_agent_type, parent_context
        )
        
        # Verify child context is created and stored
        assert child_context.user_id == self.test_user_id
        assert f"agent_{self.test_agent_type}" in child_context.request_id
        assert session._execution_contexts[self.test_agent_type] == child_context
        
    @pytest.mark.asyncio
    async def test_create_agent_execution_context_thread_safety(self):
        """Test 10: Create agent execution context is thread-safe."""
        session = UserAgentSession(self.test_user_id)
        
        parent_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id="concurrent_test",
            thread_id="concurrent_thread"
        )
        
        # Create multiple contexts concurrently
        tasks = [
            session.create_agent_execution_context(f"agent_{i}", parent_context)
            for i in range(5)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Verify all contexts were created
        assert len(results) == 5
        assert len(session._execution_contexts) == 5
        
        # Verify each context is unique and properly isolated
        for i, context in enumerate(results):
            assert context.user_id == self.test_user_id
            assert f"agent_{i}" in context.request_id

    # =========================================================================
    # AGENT MANAGEMENT TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_register_and_get_agent_basic_functionality(self):
        """Test 11: Register and retrieve agent basic functionality."""
        session = UserAgentSession(self.test_user_id)
        
        # Register agent
        await session.register_agent(self.test_agent_type, self.mock_agent_1)
        
        # Verify agent is registered
        retrieved_agent = await session.get_agent(self.test_agent_type)
        assert retrieved_agent == self.mock_agent_1
        
    @pytest.mark.asyncio
    async def test_get_nonexistent_agent_returns_none(self):
        """Test 12: Get non-existent agent returns None."""
        session = UserAgentSession(self.test_user_id)
        
        result = await session.get_agent("nonexistent_agent")
        assert result is None
        
    @pytest.mark.asyncio
    async def test_register_multiple_agents_isolation(self):
        """Test 13: Register multiple agents with proper isolation."""
        session = UserAgentSession(self.test_user_id)
        
        # Register multiple agents
        await session.register_agent(self.test_agent_type, self.mock_agent_1)
        await session.register_agent(self.test_agent_type_2, self.mock_agent_2)
        
        # Verify both agents are isolated
        agent_1 = await session.get_agent(self.test_agent_type)
        agent_2 = await session.get_agent(self.test_agent_type_2)
        
        assert agent_1 == self.mock_agent_1
        assert agent_2 == self.mock_agent_2
        assert agent_1 != agent_2
        
    @pytest.mark.asyncio
    async def test_agent_operations_thread_safety(self):
        """Test 14: Agent operations are thread-safe under concurrency."""
        session = UserAgentSession(self.test_user_id)
        
        # Simulate concurrent registration
        agents = [Mock() for _ in range(10)]
        
        async def register_agent_concurrent(i):
            await session.register_agent(f"agent_{i}", agents[i])
            return await session.get_agent(f"agent_{i}")
            
        tasks = [register_agent_concurrent(i) for i in range(10)]
        results = await asyncio.gather(*tasks)
        
        # Verify all agents were registered correctly
        assert len(results) == 10
        for i, result in enumerate(results):
            assert result == agents[i]

    # =========================================================================
    # MEMORY MANAGEMENT AND CLEANUP TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_cleanup_all_agents_calls_agent_cleanup_methods(self):
        """Test 15: Cleanup calls proper cleanup methods on agents."""
        session = UserAgentSession(self.test_user_id)
        
        # Register agents with cleanup methods
        await session.register_agent(self.test_agent_type, self.mock_agent_1)
        await session.register_agent(self.test_agent_type_2, self.mock_agent_2)
        
        # Perform cleanup
        await session.cleanup_all_agents()
        
        # Verify cleanup methods were called
        self.mock_agent_1.cleanup.assert_called_once()
        self.mock_agent_1.close.assert_called_once()
        self.mock_agent_2.cleanup.assert_called_once()
        self.mock_agent_2.close.assert_called_once()
        
        # Verify collections are cleared
        assert len(session._agents) == 0
        assert len(session._execution_contexts) == 0
        assert session._websocket_bridge is None
        
    @pytest.mark.asyncio
    async def test_cleanup_handles_agent_cleanup_errors_gracefully(self):
        """Test 16: Cleanup handles agent cleanup errors gracefully."""
        session = UserAgentSession(self.test_user_id)
        
        # Create agent with failing cleanup
        failing_agent = Mock()
        failing_agent.cleanup = AsyncMock(side_effect=Exception("Cleanup failed"))
        failing_agent.close = AsyncMock(side_effect=Exception("Close failed"))
        
        await session.register_agent("failing_agent", failing_agent)
        await session.register_agent(self.test_agent_type, self.mock_agent_1)
        
        # Cleanup should not fail despite agent errors
        await session.cleanup_all_agents()
        
        # Verify failing agent methods were called
        failing_agent.cleanup.assert_called_once()
        failing_agent.close.assert_called_once()
        
        # Verify successful agent was also cleaned up
        self.mock_agent_1.cleanup.assert_called_once()
        self.mock_agent_1.close.assert_called_once()
        
        # Verify collections are still cleared
        assert len(session._agents) == 0
        
    @pytest.mark.asyncio
    async def test_cleanup_handles_agents_without_cleanup_methods(self):
        """Test 17: Cleanup handles agents without cleanup methods."""
        session = UserAgentSession(self.test_user_id)
        
        # Create agent without cleanup methods
        simple_agent = Mock(spec=[])  # No cleanup/close methods
        
        await session.register_agent("simple_agent", simple_agent)
        await session.register_agent(self.test_agent_type, self.mock_agent_1)
        
        # Cleanup should handle agents without cleanup methods
        await session.cleanup_all_agents()
        
        # Verify agent with cleanup was handled
        self.mock_agent_1.cleanup.assert_called_once()
        self.mock_agent_1.close.assert_called_once()
        
        # Verify collections are cleared
        assert len(session._agents) == 0

    @pytest.mark.asyncio 
    async def test_memory_leak_prevention_with_weak_references(self):
        """Test 18: Memory leak prevention through proper cleanup."""
        session = UserAgentSession(self.test_user_id)
        
        # Create object that can be weakly referenced
        class TestAgent:
            async def cleanup(self):
                pass
            async def close(self):
                pass
        
        test_agent = TestAgent()
        weak_ref = weakref.ref(test_agent)
        
        await session.register_agent("test_agent", test_agent)
        
        # Verify agent is registered and weakref is alive
        assert await session.get_agent("test_agent") is not None
        assert weak_ref() is not None
        
        # Cleanup session
        await session.cleanup_all_agents()
        
        # Clear local reference and force garbage collection
        del test_agent
        gc.collect()
        
        # Verify object was properly cleaned up (weakref should be dead)
        assert weak_ref() is None

    # =========================================================================
    # USER ISOLATION SECURITY TESTS (MISSION CRITICAL)
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_user_isolation_prevents_cross_contamination(self):
        """Test 19: CRITICAL - User isolation prevents agent cross-contamination."""
        # Create separate sessions for different users
        session_user_1 = UserAgentSession(self.test_user_id)
        session_user_2 = UserAgentSession(self.test_user_id_2)
        
        # Register different agents for each user
        await session_user_1.register_agent(self.test_agent_type, self.mock_agent_1)
        await session_user_2.register_agent(self.test_agent_type, self.mock_agent_2)
        
        # Verify complete isolation
        user_1_agent = await session_user_1.get_agent(self.test_agent_type)
        user_2_agent = await session_user_2.get_agent(self.test_agent_type)
        
        # CRITICAL: Agents must be completely isolated
        assert user_1_agent == self.mock_agent_1
        assert user_2_agent == self.mock_agent_2
        assert user_1_agent != user_2_agent
        
        # Verify user 1 cannot access user 2's agents
        user_1_agent_2 = await session_user_1.get_agent("user_2_exclusive")
        assert user_1_agent_2 is None
        
    @pytest.mark.asyncio
    async def test_websocket_isolation_per_user(self):
        """Test 20: CRITICAL - WebSocket bridges are isolated per user."""
        session_user_1 = UserAgentSession(self.test_user_id)
        session_user_2 = UserAgentSession(self.test_user_id_2)
        
        # Create separate WebSocket managers for each user
        manager_1 = Mock()
        bridge_1 = Mock()
        manager_1.create_bridge = AsyncMock(return_value=bridge_1)
        
        manager_2 = Mock()
        bridge_2 = Mock() 
        manager_2.create_bridge = AsyncMock(return_value=bridge_2)
        
        await session_user_1.set_websocket_manager(manager_1)
        await session_user_2.set_websocket_manager(manager_2)
        
        # Verify complete WebSocket isolation
        assert session_user_1._websocket_bridge == bridge_1
        assert session_user_2._websocket_bridge == bridge_2
        assert session_user_1._websocket_bridge != session_user_2._websocket_bridge
        
    @pytest.mark.asyncio
    async def test_execution_context_isolation_per_user(self):
        """Test 21: CRITICAL - Execution contexts are isolated per user."""
        session_user_1 = UserAgentSession(self.test_user_id)
        session_user_2 = UserAgentSession(self.test_user_id_2)
        
        # Create contexts for same agent type but different users
        parent_context_1 = UserExecutionContext(
            user_id=self.test_user_id,
            request_id="user1_request",
            thread_id="user1_thread"
        )
        
        parent_context_2 = UserExecutionContext(
            user_id=self.test_user_id_2,
            request_id="user2_request", 
            thread_id="user2_thread"
        )
        
        context_1 = await session_user_1.create_agent_execution_context(
            self.test_agent_type, parent_context_1
        )
        context_2 = await session_user_2.create_agent_execution_context(
            self.test_agent_type, parent_context_2
        )
        
        # Verify complete context isolation
        assert context_1.user_id == self.test_user_id
        assert context_2.user_id == self.test_user_id_2
        assert context_1.user_id != context_2.user_id
        assert context_1.request_id != context_2.request_id
        assert context_1.thread_id != context_2.thread_id
        
    @pytest.mark.asyncio
    async def test_concurrent_user_sessions_no_interference(self):
        """Test 22: CRITICAL - Concurrent user sessions don't interfere."""
        # Create multiple user sessions
        sessions = [
            UserAgentSession(f"user_concurrent_{i}")
            for i in range(5)
        ]
        
        # Register agents concurrently for all users
        async def setup_user_session(session, user_index):
            agent = Mock()
            agent.cleanup = AsyncMock()
            agent.close = AsyncMock()
            
            await session.register_agent(f"agent_{user_index}", agent)
            return agent
            
        tasks = [
            setup_user_session(sessions[i], i)
            for i in range(5)
        ]
        
        registered_agents = await asyncio.gather(*tasks)
        
        # Verify each user has their own isolated agent
        for i, session in enumerate(sessions):
            user_agent = await session.get_agent(f"agent_{i}")
            assert user_agent == registered_agents[i]
            
            # Verify user cannot access other users' agents
            for j in range(5):
                if i != j:
                    other_agent = await session.get_agent(f"agent_{j}")
                    assert other_agent is None

    # =========================================================================
    # METRICS AND MONITORING TESTS
    # =========================================================================
    
    def test_get_metrics_returns_proper_session_information(self):
        """Test 23: Get metrics returns comprehensive session information."""
        session = UserAgentSession(self.test_user_id)
        
        metrics = session.get_metrics()
        
        # Verify basic metrics structure
        assert isinstance(metrics, dict)
        assert metrics['user_id'] == self.test_user_id
        assert metrics['agent_count'] == 0
        assert metrics['context_count'] == 0
        assert metrics['has_websocket_bridge'] == False
        assert 'uptime_seconds' in metrics
        assert isinstance(metrics['uptime_seconds'], float)
        assert metrics['uptime_seconds'] >= 0
        
    @pytest.mark.asyncio
    async def test_get_metrics_reflects_session_state_changes(self):
        """Test 24: Get metrics reflects real session state changes."""
        session = UserAgentSession(self.test_user_id)
        
        # Initial state
        initial_metrics = session.get_metrics()
        assert initial_metrics['agent_count'] == 0
        assert initial_metrics['context_count'] == 0
        assert initial_metrics['has_websocket_bridge'] == False
        
        # Add agent and context
        await session.register_agent(self.test_agent_type, self.mock_agent_1)
        
        parent_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id="metrics_test",
            thread_id="metrics_thread"
        )
        await session.create_agent_execution_context(self.test_agent_type, parent_context)
        await session.set_websocket_manager(self.mock_websocket_manager)
        
        # Updated state
        updated_metrics = session.get_metrics()
        assert updated_metrics['agent_count'] == 1
        assert updated_metrics['context_count'] == 1
        assert updated_metrics['has_websocket_bridge'] == True
        assert updated_metrics['uptime_seconds'] >= initial_metrics['uptime_seconds']

    # =========================================================================
    # ERROR HANDLING AND EDGE CASES
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_websocket_manager_integration_error_handling(self):
        """Test 25: WebSocket manager integration handles errors gracefully."""
        session = UserAgentSession(self.test_user_id)
        
        # Create manager with failing bridge creation
        failing_manager = Mock()
        failing_manager.create_bridge = AsyncMock(
            side_effect=Exception("Bridge creation failed")
        )
        
        # Should propagate the error (not swallow it)
        with pytest.raises(Exception, match="Bridge creation failed"):
            await session.set_websocket_manager(failing_manager)
            
    @pytest.mark.asyncio
    async def test_agent_context_creation_with_invalid_agent_type(self):
        """Test 26: Agent context creation with edge case agent types."""
        session = UserAgentSession(self.test_user_id)
        
        parent_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id="edge_case_test",
            thread_id="edge_case_thread"
        )
        
        # Test with empty agent type
        context = await session.create_agent_execution_context("", parent_context)
        assert context.user_id == self.test_user_id
        assert "agent_" in context.request_id
        
        # Test with special characters
        special_type = "agent-with-special_chars.test"
        context_special = await session.create_agent_execution_context(
            special_type, parent_context
        )
        assert context_special.user_id == self.test_user_id
        assert f"agent_{special_type}" in context_special.request_id
        
    @pytest.mark.asyncio
    async def test_cleanup_with_no_agents_registered(self):
        """Test 27: Cleanup with no agents registered should not error."""
        session = UserAgentSession(self.test_user_id)
        
        # Cleanup empty session should work without error
        await session.cleanup_all_agents()
        
        # Verify state remains clean
        assert len(session._agents) == 0
        assert len(session._execution_contexts) == 0
        assert session._websocket_bridge is None

    # =========================================================================
    # PERFORMANCE AND STRESS TESTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_high_volume_agent_registration_performance(self):
        """Test 28: High-volume agent registration maintains performance."""
        session = UserAgentSession(self.test_user_id)
        
        # Register many agents
        num_agents = 100
        agents = [Mock() for _ in range(num_agents)]
        
        start_time = datetime.now(timezone.utc)
        
        # Register all agents
        for i in range(num_agents):
            await session.register_agent(f"perf_agent_{i}", agents[i])
            
        end_time = datetime.now(timezone.utc)
        duration = (end_time - start_time).total_seconds()
        
        # Verify all agents registered successfully
        assert len(session._agents) == num_agents
        
        # Performance should be reasonable (less than 1 second for 100 agents)
        assert duration < 1.0
        
        # Verify random access still works
        random_agent = await session.get_agent("perf_agent_50")
        assert random_agent == agents[50]
        
    @pytest.mark.asyncio
    async def test_memory_usage_stability_under_load(self):
        """Test 29: Memory usage remains stable under repeated operations."""
        session = UserAgentSession(self.test_user_id)
        
        # Perform many register/cleanup cycles
        for cycle in range(10):
            # Register agents
            agents = [Mock() for _ in range(10)]
            for i, agent in enumerate(agents):
                agent.cleanup = AsyncMock()
                agent.close = AsyncMock()
                await session.register_agent(f"cycle_{cycle}_agent_{i}", agent)
                
            # Verify agents registered
            assert len(session._agents) == 10
            
            # Cleanup all agents
            await session.cleanup_all_agents()
            
            # Verify cleanup
            assert len(session._agents) == 0
            
        # Force garbage collection
        gc.collect()
        
        # Session should still be functional
        test_agent = Mock()
        test_agent.cleanup = AsyncMock()
        test_agent.close = AsyncMock()
        await session.register_agent("final_test", test_agent)
        
        retrieved = await session.get_agent("final_test")
        assert retrieved == test_agent

    # =========================================================================
    # INTEGRATION TESTS WITH REAL COMPONENTS
    # =========================================================================
    
    @pytest.mark.asyncio
    async def test_real_user_execution_context_integration(self):
        """Test 30: Integration with real UserExecutionContext instances."""
        session = UserAgentSession(self.test_user_id)
        
        # Create real UserExecutionContext
        real_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id="real_integration_test",
            thread_id="real_integration_thread"
        )
        
        # Test WebSocket manager with real context
        await session.set_websocket_manager(self.mock_websocket_manager, real_context)
        
        # Verify integration
        assert session._websocket_manager == self.mock_websocket_manager
        self.mock_websocket_manager.create_bridge.assert_called_once_with(real_context)
        
        # Test agent context creation with real context
        child_context = await session.create_agent_execution_context(
            self.test_agent_type, real_context
        )
        
        # Verify child context is properly created from real parent
        assert isinstance(child_context, UserExecutionContext)
        assert child_context.user_id == real_context.user_id
        assert child_context != real_context  # Should be different instance
        
    @pytest.mark.asyncio
    async def test_factory_pattern_compliance_with_websocket_bridge(self):
        """Test 31: Factory pattern compliance for WebSocket bridge creation."""
        session = UserAgentSession(self.test_user_id)
        
        # Test with async factory
        async_manager = Mock()
        async_manager.create_bridge = AsyncMock(return_value=self.mock_websocket_bridge)
        
        await session.set_websocket_manager(async_manager)
        assert session._websocket_bridge == self.mock_websocket_bridge
        
        # Test with sync factory
        sync_manager = Mock()
        sync_bridge = Mock()
        sync_manager.create_bridge = Mock(return_value=sync_bridge)
        
        # Create new session for sync test
        sync_session = UserAgentSession(self.test_user_id_2)
        await sync_session.set_websocket_manager(sync_manager)
        assert sync_session._websocket_bridge == sync_bridge
        
        # Verify both sessions maintain isolation
        assert session._websocket_bridge != sync_session._websocket_bridge
        
    @pytest.mark.asyncio
    async def test_session_lifecycle_end_to_end(self):
        """Test 32: Complete session lifecycle from creation to cleanup."""
        # Create session
        session = UserAgentSession(self.test_user_id)
        initial_metrics = session.get_metrics()
        
        # Set up WebSocket
        await session.set_websocket_manager(self.mock_websocket_manager)
        
        # Create execution contexts
        parent_context = UserExecutionContext(
            user_id=self.test_user_id,
            request_id="lifecycle_test",
            thread_id="lifecycle_thread"
        )
        context_1 = await session.create_agent_execution_context("agent_1", parent_context)
        context_2 = await session.create_agent_execution_context("agent_2", parent_context)
        
        # Register agents
        agent_1 = Mock()
        agent_1.cleanup = AsyncMock()
        agent_1.close = AsyncMock()
        
        agent_2 = Mock()
        agent_2.cleanup = AsyncMock() 
        agent_2.close = AsyncMock()
        
        await session.register_agent("agent_1", agent_1)
        await session.register_agent("agent_2", agent_2)
        
        # Verify session state
        mid_metrics = session.get_metrics()
        assert mid_metrics['agent_count'] == 2
        assert mid_metrics['context_count'] == 2
        assert mid_metrics['has_websocket_bridge'] == True
        
        # Complete cleanup
        await session.cleanup_all_agents()
        
        # Verify final state
        final_metrics = session.get_metrics()
        assert final_metrics['agent_count'] == 0
        assert final_metrics['context_count'] == 0
        assert final_metrics['has_websocket_bridge'] == False
        
        # Verify cleanup methods were called
        agent_1.cleanup.assert_called_once()
        agent_1.close.assert_called_once()
        agent_2.cleanup.assert_called_once()
        agent_2.close.assert_called_once()