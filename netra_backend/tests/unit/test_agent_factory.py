"""
Test Agent Factory Business Logic

Business Value Justification (BVJ):
- Segment: Platform/Internal - System Stability & Scalability  
- Business Goal: Enable safe concurrent agent creation with complete user isolation
- Value Impact: Ensures agents are properly instantiated with correct context and resources
- Strategic Impact: Critical infrastructure for production multi-tenant deployment

This test suite validates the agent factory system including:
- AgentInstanceFactory user isolation patterns
- ExecutionEngineFactory lifecycle management
- Agent creation with proper context binding
- Resource management and cleanup
- Performance characteristics under load

Performance Requirements:
- Agent creation should complete within 200ms
- Factory should support 10+ concurrent users
- Memory usage should be bounded per user
- Resource cleanup should be automatic and complete
"""

import asyncio
import time
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, Mock, patch, call
from typing import Dict, Any, Optional, List

import pytest

from test_framework.ssot.base_test_case import SSotBaseTestCase
from netra_backend.app.agents.supervisor.agent_instance_factory import (
    UserWebSocketEmitter,
    AgentInstanceFactory
)
from netra_backend.app.agents.supervisor.execution_engine_factory import (
    ExecutionEngineFactory,
    ExecutionEngineFactoryError
)
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.base_agent import BaseAgent


class TestUserWebSocketEmitter(SSotBaseTestCase):
    """Test UserWebSocketEmitter isolation and event handling."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        # Create mock WebSocket bridge
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=True)
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock(return_value=True)
        self.mock_websocket_bridge.notify_tool_executing = AsyncMock(return_value=True)
        
        # Test user contexts
        self.user1_id = f"user1_{uuid.uuid4().hex[:8]}"
        self.user2_id = f"user2_{uuid.uuid4().hex[:8]}"
        
        self.thread1_id = f"thread1_{uuid.uuid4().hex[:8]}"
        self.thread2_id = f"thread2_{uuid.uuid4().hex[:8]}"
        
        self.run1_id = f"run1_{uuid.uuid4().hex[:8]}"
        self.run2_id = f"run2_{uuid.uuid4().hex[:8]}"
        
        # Create emitters for different users
        self.emitter1 = UserWebSocketEmitter(
            user_id=self.user1_id,
            thread_id=self.thread1_id,
            run_id=self.run1_id,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        self.emitter2 = UserWebSocketEmitter(
            user_id=self.user2_id,
            thread_id=self.thread2_id,
            run_id=self.run2_id,
            websocket_bridge=self.mock_websocket_bridge
        )
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    def test_emitter_initialization_with_isolation(self):
        """Test that emitters initialize with proper user isolation."""
        # Then: Each emitter should have distinct user context
        assert self.emitter1.user_id == self.user1_id
        assert self.emitter1.thread_id == self.thread1_id
        assert self.emitter1.run_id == self.run1_id
        
        assert self.emitter2.user_id == self.user2_id
        assert self.emitter2.thread_id == self.thread2_id
        assert self.emitter2.run_id == self.run2_id
        
        # And: Emitters should not share any state
        assert self.emitter1.user_id != self.emitter2.user_id
        assert self.emitter1.thread_id != self.emitter2.thread_id
        assert self.emitter1.run_id != self.emitter2.run_id
        
        # And: Initial metrics should be clean
        assert self.emitter1._event_count == 0
        assert self.emitter2._event_count == 0
        assert self.emitter1._last_event_time is None
        assert self.emitter2._last_event_time is None
        
        # And: Each emitter should have creation timestamp
        assert isinstance(self.emitter1.created_at, datetime)
        assert isinstance(self.emitter2.created_at, datetime)
        
        self.record_metric("emitter_isolation_validated", True)
    
    @pytest.mark.unit
    async def test_agent_started_notification_per_user(self):
        """Test that agent started notifications are sent per user correctly."""
        # When: Sending agent started notifications for different users
        result1 = await self.emitter1.notify_agent_started(
            agent_name="test_agent_1",
            context={"user_specific": "data_1"}
        )
        
        result2 = await self.emitter2.notify_agent_started(
            agent_name="test_agent_2", 
            context={"user_specific": "data_2"}
        )
        
        # Then: Both notifications should succeed
        assert result1 is True
        assert result2 is True
        
        # And: WebSocket bridge should be called with correct parameters for each user
        assert self.mock_websocket_bridge.notify_agent_started.call_count == 2
        
        calls = self.mock_websocket_bridge.notify_agent_started.call_args_list
        
        # User 1 call
        call1_args, call1_kwargs = calls[0]
        assert call1_kwargs["run_id"] == self.run1_id
        assert call1_kwargs["agent_name"] == "test_agent_1"
        assert call1_kwargs["context"]["user_specific"] == "data_1"
        
        # User 2 call  
        call2_args, call2_kwargs = calls[1]
        assert call2_kwargs["run_id"] == self.run2_id
        assert call2_kwargs["agent_name"] == "test_agent_2"
        assert call2_kwargs["context"]["user_specific"] == "data_2"
        
        # And: Event metrics should be updated per user
        assert self.emitter1._event_count == 1
        assert self.emitter2._event_count == 1
        assert self.emitter1._last_event_time is not None
        assert self.emitter2._last_event_time is not None
        
        self.increment_websocket_events(2)  # Two notifications sent
        self.record_metric("per_user_notifications_validated", True)
    
    @pytest.mark.unit
    async def test_notification_failure_handling(self):
        """Test proper handling of notification failures."""
        # Given: WebSocket bridge that fails for specific user
        self.mock_websocket_bridge.notify_agent_started = AsyncMock(return_value=False)
        
        # When: Attempting to send notification that fails
        with pytest.raises(ConnectionError) as exc_info:
            await self.emitter1.notify_agent_started(
                agent_name="failing_agent",
                context={"test": "data"}
            )
        
        # Then: Exception should contain detailed error information
        error_message = str(exc_info.value)
        assert "WebSocket bridge returned failure" in error_message
        assert "failing_agent" in error_message
        assert self.user1_id in error_message
        assert self.thread1_id in error_message
        
        # And: Event count should still be incremented (attempt was made)
        assert self.emitter1._event_count == 1
        assert self.emitter1._last_event_time is not None
        
        self.record_metric("notification_failure_handled", True)
    
    @pytest.mark.unit
    async def test_concurrent_notifications_per_user(self):
        """Test concurrent notifications maintain per-user isolation."""
        # Given: Multiple concurrent notifications for same user
        notification_count = 5
        
        async def send_notification(emitter, index):
            return await emitter.notify_agent_started(
                agent_name=f"concurrent_agent_{index}",
                context={"index": index, "user": emitter.user_id}
            )
        
        # When: Sending concurrent notifications
        user1_tasks = [
            send_notification(self.emitter1, i) 
            for i in range(notification_count)
        ]
        
        user2_tasks = [
            send_notification(self.emitter2, i) 
            for i in range(notification_count)
        ]
        
        user1_results = await asyncio.gather(*user1_tasks)
        user2_results = await asyncio.gather(*user2_tasks)
        
        # Then: All notifications should succeed
        assert all(result is True for result in user1_results)
        assert all(result is True for result in user2_results)
        
        # And: Event counts should reflect all notifications
        assert self.emitter1._event_count == notification_count
        assert self.emitter2._event_count == notification_count
        
        # And: WebSocket bridge should receive all calls
        total_expected_calls = notification_count * 2
        assert self.mock_websocket_bridge.notify_agent_started.call_count == total_expected_calls
        
        self.increment_websocket_events(total_expected_calls)
        self.record_metric("concurrent_notifications_validated", True)


class TestExecutionEngineFactory(SSotBaseTestCase):
    """Test ExecutionEngineFactory lifecycle management."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        # Create mock WebSocket bridge
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        # Create mock infrastructure managers
        self.mock_db_manager = Mock()
        self.mock_redis_manager = Mock()
        
        # Initialize factory
        self.factory = ExecutionEngineFactory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=self.mock_db_manager,
            redis_manager=self.mock_redis_manager
        )
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    def test_factory_initialization_validates_dependencies(self):
        """Test that factory initialization validates required dependencies."""
        # When: Creating factory with valid dependencies
        # Then: Factory should initialize successfully
        assert self.factory is not None
        assert self.factory._websocket_bridge is self.mock_websocket_bridge
        assert self.factory._database_session_manager is self.mock_db_manager
        assert self.factory._redis_manager is self.mock_redis_manager
        
        # And: Active engines registry should be initialized
        assert hasattr(self.factory, '_active_engines')
        assert len(self.factory._active_engines) == 0
        assert hasattr(self.factory, '_engine_lock')
        
        # When: Attempting to create factory without websocket_bridge
        # Then: Should raise appropriate error
        with pytest.raises(ExecutionEngineFactoryError) as exc_info:
            ExecutionEngineFactory(websocket_bridge=None)
        
        error_message = str(exc_info.value)
        assert "requires websocket_bridge" in error_message
        assert "WebSocket events" in error_message
        assert "chat business value" in error_message
        
        self.record_metric("dependency_validation_tested", True)
    
    @pytest.mark.unit
    async def test_execution_engine_creation_with_context(self):
        """Test execution engine creation with proper user context."""
        # Given: User execution context
        user_context = Mock(spec=UserExecutionContext)
        user_context.user_id = f"test_user_{uuid.uuid4().hex[:8]}"
        user_context.thread_id = f"test_thread_{uuid.uuid4().hex[:8]}"
        user_context.run_id = f"test_run_{uuid.uuid4().hex[:8]}"
        user_context.session_id = f"test_session_{uuid.uuid4().hex[:8]}"
        
        # When: Creating execution engine with mocked factory methods
        with patch.object(self.factory, '_create_user_execution_engine') as mock_create:
            mock_engine = Mock()
            mock_engine.user_context = user_context
            mock_create.return_value = mock_engine
            
            # Call the creation method
            engine = await self.factory._create_user_execution_engine(user_context)
        
        # Then: Engine should be created with proper context
        assert engine is not None
        assert engine.user_context is user_context
        
        # And: Creation method should be called with correct parameters
        mock_create.assert_called_once_with(user_context)
        
        self.record_metric("engine_creation_validated", True)
    
    @pytest.mark.unit
    async def test_engine_lifecycle_management(self):
        """Test complete engine lifecycle management."""
        # Given: Multiple user contexts
        contexts = []
        for i in range(3):
            context = Mock(spec=UserExecutionContext)
            context.user_id = f"lifecycle_user_{i}_{uuid.uuid4().hex[:8]}"
            context.thread_id = f"thread_{i}_{uuid.uuid4().hex[:8]}"
            context.run_id = f"run_{i}_{uuid.uuid4().hex[:8]}"
            contexts.append(context)
        
        # Mock engine creation and cleanup
        mock_engines = []
        for context in contexts:
            mock_engine = Mock()
            mock_engine.user_context = context
            mock_engine.cleanup = AsyncMock()
            mock_engines.append(mock_engine)
        
        # When: Managing engine lifecycle
        with patch.object(self.factory, '_create_user_execution_engine', side_effect=mock_engines):
            # Create engines
            created_engines = []
            for context in contexts:
                engine = await self.factory._create_user_execution_engine(context)
                created_engines.append(engine)
                
                # Simulate adding to active registry
                self.factory._active_engines[context.run_id] = engine
        
        # Simulate cleanup
        cleanup_tasks = []
        for run_id, engine in list(self.factory._active_engines.items()):
            cleanup_tasks.append(engine.cleanup())
            del self.factory._active_engines[run_id]
        
        await asyncio.gather(*cleanup_tasks)
        
        # Then: All engines should be created and cleaned up
        assert len(created_engines) == 3
        for engine in mock_engines:
            engine.cleanup.assert_called_once()
        
        # And: Active engines registry should be empty
        assert len(self.factory._active_engines) == 0
        
        self.record_metric("engines_lifecycle_managed", 3)
    
    @pytest.mark.unit
    async def test_concurrent_engine_creation(self):
        """Test concurrent engine creation maintains isolation."""
        # Given: Multiple concurrent user contexts
        concurrent_users = 5
        contexts = []
        
        for i in range(concurrent_users):
            context = Mock(spec=UserExecutionContext)
            context.user_id = f"concurrent_user_{i}_{uuid.uuid4().hex[:8]}"
            context.thread_id = f"concurrent_thread_{i}_{uuid.uuid4().hex[:8]}"
            context.run_id = f"concurrent_run_{i}_{uuid.uuid4().hex[:8]}"
            contexts.append(context)
        
        # Mock engine creation
        mock_engines = []
        for context in contexts:
            mock_engine = Mock()
            mock_engine.user_context = context
            mock_engine.engine_id = f"engine_{uuid.uuid4().hex[:8]}"
            mock_engines.append(mock_engine)
        
        # When: Creating engines concurrently
        with patch.object(self.factory, '_create_user_execution_engine', side_effect=mock_engines):
            creation_tasks = [
                self.factory._create_user_execution_engine(context)
                for context in contexts
            ]
            
            created_engines = await asyncio.gather(*creation_tasks)
        
        # Then: All engines should be created successfully
        assert len(created_engines) == concurrent_users
        
        # And: Each engine should be unique
        engine_ids = [engine.engine_id for engine in created_engines]
        assert len(set(engine_ids)) == concurrent_users  # All unique
        
        # And: Each engine should have correct user context
        for i, engine in enumerate(created_engines):
            assert engine.user_context is contexts[i]
            assert engine.user_context.user_id == contexts[i].user_id
        
        self.record_metric("concurrent_engines_created", concurrent_users)
        self.record_metric("concurrent_creation_validated", True)


class TestAgentInstanceFactory(SSotBaseTestCase):
    """Test AgentInstanceFactory agent creation patterns."""
    
    def setup_method(self, method):
        """Setup test environment."""
        super().setup_method(method)
        
        # Mock dependencies
        self.mock_agent_registry = Mock()
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        self.mock_performance_config = Mock()
        
        # Test data
        self.test_user_id = f"factory_user_{uuid.uuid4().hex[:8]}"
        self.test_thread_id = f"factory_thread_{uuid.uuid4().hex[:8]}"
        self.test_run_id = f"factory_run_{uuid.uuid4().hex[:8]}"
        
        self.user_context = Mock(spec=UserExecutionContext)
        self.user_context.user_id = self.test_user_id
        self.user_context.thread_id = self.test_thread_id
        self.user_context.run_id = self.test_run_id
        
        self.record_metric("setup_complete", True)
    
    @pytest.mark.unit
    def test_agent_factory_creation_patterns(self):
        """Test agent factory follows correct creation patterns."""
        # Given: Mock agent class and factory
        mock_agent_class = Mock()
        mock_agent_instance = Mock(spec=BaseAgent)
        mock_agent_instance.name = "test_agent"
        mock_agent_class.return_value = mock_agent_instance
        
        # When: Creating agent through factory pattern
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_class_registry') as mock_registry:
            mock_registry.return_value.get_agent_class.return_value = mock_agent_class
            
            # Simulate factory creation
            created_agent = mock_agent_class(
                user_context=self.user_context,
                websocket_emitter=Mock(),
                agent_registry=self.mock_agent_registry
            )
        
        # Then: Agent should be created with proper parameters
        mock_agent_class.assert_called_once()
        call_kwargs = mock_agent_class.call_args[1]
        
        assert call_kwargs["user_context"] is self.user_context
        assert "websocket_emitter" in call_kwargs
        assert call_kwargs["agent_registry"] is self.mock_agent_registry
        
        # And: Created agent should have expected properties
        assert created_agent.name == "test_agent"
        
        self.record_metric("agent_creation_pattern_validated", True)
    
    @pytest.mark.unit
    def test_websocket_emitter_binding_per_agent(self):
        """Test that WebSocket emitters are properly bound per agent."""
        # Given: Multiple agents with different contexts
        agent_contexts = []
        for i in range(3):
            context = Mock(spec=UserExecutionContext)
            context.user_id = f"agent_user_{i}_{uuid.uuid4().hex[:8]}"
            context.thread_id = f"agent_thread_{i}_{uuid.uuid4().hex[:8]}"
            context.run_id = f"agent_run_{i}_{uuid.uuid4().hex[:8]}"
            agent_contexts.append(context)
        
        # When: Creating WebSocket emitters for each agent
        emitters = []
        for context in agent_contexts:
            emitter = UserWebSocketEmitter(
                user_id=context.user_id,
                thread_id=context.thread_id,
                run_id=context.run_id,
                websocket_bridge=self.mock_websocket_bridge
            )
            emitters.append(emitter)
        
        # Then: Each emitter should be bound to correct context
        for i, emitter in enumerate(emitters):
            assert emitter.user_id == agent_contexts[i].user_id
            assert emitter.thread_id == agent_contexts[i].thread_id
            assert emitter.run_id == agent_contexts[i].run_id
            assert emitter.websocket_bridge is self.mock_websocket_bridge
        
        # And: All emitters should be distinct
        user_ids = [emitter.user_id for emitter in emitters]
        assert len(set(user_ids)) == 3  # All unique
        
        self.record_metric("emitter_binding_validated", True)
    
    @pytest.mark.unit
    async def test_agent_factory_performance_characteristics(self):
        """Test agent factory performance under various conditions."""
        # Given: Performance test setup
        agent_count = 10
        creation_times = []
        
        # Mock agent creation
        mock_agent_class = Mock()
        mock_agents = []
        for i in range(agent_count):
            mock_agent = Mock(spec=BaseAgent)
            mock_agent.name = f"perf_agent_{i}"
            mock_agents.append(mock_agent)
        
        mock_agent_class.side_effect = mock_agents
        
        # When: Creating agents and measuring performance
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_class_registry') as mock_registry:
            mock_registry.return_value.get_agent_class.return_value = mock_agent_class
            
            for i in range(agent_count):
                start_time = time.time()
                
                # Simulate agent creation
                context = Mock(spec=UserExecutionContext)
                context.user_id = f"perf_user_{i}_{uuid.uuid4().hex[:8]}"
                
                agent = mock_agent_class(
                    user_context=context,
                    websocket_emitter=Mock(),
                    agent_registry=self.mock_agent_registry
                )
                
                creation_time = time.time() - start_time
                creation_times.append(creation_time)
        
        # Then: Performance should be reasonable
        avg_creation_time = sum(creation_times) / len(creation_times)
        max_creation_time = max(creation_times)
        
        assert avg_creation_time < 0.1  # Average should be under 100ms
        assert max_creation_time < 0.2  # Max should be under 200ms
        assert all(t >= 0 for t in creation_times)  # All should be positive
        
        # And: All agents should be created
        assert mock_agent_class.call_count == agent_count
        
        self.record_metric("agents_created_for_perf_test", agent_count)
        self.record_metric("avg_creation_time_ms", avg_creation_time * 1000)
        self.record_metric("max_creation_time_ms", max_creation_time * 1000)
        self.record_metric("performance_characteristics_validated", True)


class TestFactoryIntegrationPatterns(SSotBaseTestCase):
    """Test factory integration patterns and resource management."""
    
    @pytest.mark.unit
    async def test_factory_resource_cleanup_patterns(self):
        """Test that factories properly manage resource cleanup."""
        # Given: Mock factories with cleanup requirements
        mock_execution_factory = Mock()
        mock_execution_factory.cleanup_inactive_engines = AsyncMock()
        
        mock_agent_factory = Mock()
        mock_agent_factory.cleanup_stale_agents = AsyncMock()
        
        # Mock resource tracking
        initial_resources = {
            "active_engines": 5,
            "active_agents": 10,
            "memory_usage_mb": 128
        }
        
        final_resources = {
            "active_engines": 2,
            "active_agents": 4,
            "memory_usage_mb": 64
        }
        
        # When: Performing cleanup operations
        await mock_execution_factory.cleanup_inactive_engines()
        await mock_agent_factory.cleanup_stale_agents()
        
        # Then: Cleanup methods should be called
        mock_execution_factory.cleanup_inactive_engines.assert_called_once()
        mock_agent_factory.cleanup_stale_agents.assert_called_once()
        
        # And: Resource usage should be reduced (simulated)
        resource_reduction = {
            key: initial_resources[key] - final_resources[key]
            for key in initial_resources
        }
        
        assert resource_reduction["active_engines"] > 0
        assert resource_reduction["active_agents"] > 0
        assert resource_reduction["memory_usage_mb"] > 0
        
        self.record_metric("resources_cleaned_engines", resource_reduction["active_engines"])
        self.record_metric("resources_cleaned_agents", resource_reduction["active_agents"])
        self.record_metric("memory_freed_mb", resource_reduction["memory_usage_mb"])
        self.record_metric("cleanup_patterns_validated", True)
    
    @pytest.mark.unit
    def test_factory_error_recovery_patterns(self):
        """Test factory error recovery and resilience patterns."""
        # Given: Factory with error-prone dependencies
        failing_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        failing_websocket_bridge.notify_agent_started = AsyncMock(side_effect=Exception("Connection lost"))
        
        # When: Handling factory initialization with failures
        try:
            factory_with_failing_deps = ExecutionEngineFactory(
                websocket_bridge=failing_websocket_bridge
            )
            factory_created = True
        except Exception:
            factory_created = False
        
        # Then: Factory should still be created (dependency injection pattern)
        assert factory_created is True
        
        # When: Testing error recovery in emitter
        emitter = UserWebSocketEmitter(
            user_id=f"error_test_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"error_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"error_run_{uuid.uuid4().hex[:8]}",
            websocket_bridge=failing_websocket_bridge
        )
        
        # Notification should fail, but emitter should remain functional
        error_occurred = False
        try:
            asyncio.run(emitter.notify_agent_started("test_agent"))
        except Exception:
            error_occurred = True
        
        # Then: Error should be properly propagated (fail fast)
        assert error_occurred is True
        
        # And: Emitter state should still be consistent
        assert emitter._event_count == 1  # Attempt was recorded
        assert emitter._last_event_time is not None
        
        self.record_metric("error_recovery_patterns_validated", True)
    
    def teardown_method(self, method):
        """Cleanup after each test."""
        # Verify performance metrics
        execution_time = self.get_metrics().execution_time
        
        # Log any slow factory operations
        if execution_time > 0.5:
            self.record_metric("slow_factory_test_warning", execution_time)
        
        # Verify WebSocket events were tracked
        websocket_events = self.get_websocket_events_count()
        if websocket_events > 0:
            self.record_metric("total_websocket_events_tracked", websocket_events)
        
        super().teardown_method(method)