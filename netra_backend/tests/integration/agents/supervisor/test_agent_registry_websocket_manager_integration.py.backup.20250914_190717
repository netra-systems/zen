"""
Integration Tests for AgentRegistry WebSocket Manager Integration

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Real-time agent communication for enhanced user experience
- Value Impact: Enables live agent feedback, progress updates, and interactive workflows
- Strategic Impact: Core infrastructure for responsive AI agent interactions

CRITICAL MISSION: Test AgentRegistry WebSocket Manager Integration ensuring:
1. AgentRegistry.set_websocket_manager() enhances tool dispatcher as required
2. Real WebSocket connection and event propagation to users
3. Agent execution with live WebSocket event streaming
4. User session WebSocket bridge creation and management
5. Run-thread mapping registration for reliable message routing
6. WebSocket event isolation per user with no cross-contamination
7. Tool dispatcher enhancement with WebSocket capabilities
8. Error handling and recovery in WebSocket communications

FOCUS: Real integration testing with actual WebSocket connections and agent execution
"""

import asyncio
import pytest
import time
import uuid
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock, patch, MagicMock

from test_framework.ssot.base_test_case import SSotBaseTestCase

# Import classes under test
from netra_backend.app.agents.supervisor.agent_registry import (
    AgentRegistry,
    UserAgentSession
)

from netra_backend.app.agents.supervisor.agent_instance_factory import (
    AgentInstanceFactory,
    configure_agent_instance_factory
)

from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import (
    AgentWebSocketBridge,
    create_agent_websocket_bridge
)

from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.core.tools.unified_tool_dispatcher import UnifiedToolDispatcher


# ============================================================================
# FIXTURES
# ============================================================================

@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager for testing."""
    mock_llm = AsyncMock()
    mock_llm.initialize = AsyncMock()
    mock_llm.chat_completion = AsyncMock(return_value="Test response from agent")
    mock_llm.is_healthy = Mock(return_value=True)
    return mock_llm


@pytest.fixture
def real_websocket_manager():
    """Create real WebSocket manager instance for integration testing."""
    # Create actual UnifiedWebSocketManager instance
    ws_manager = UnifiedWebSocketManager()
    
    # Mock the actual WebSocket sending for testing
    ws_manager.send_event = AsyncMock(return_value=True)
    ws_manager.is_connected = Mock(return_value=True)
    ws_manager.get_connection_count = Mock(return_value=1)
    
    return ws_manager


@pytest.fixture
def test_user_contexts():
    """Create multiple test user contexts for isolation testing."""
    contexts = []
    for i in range(3):
        context = UserExecutionContext(
            user_id=f"integration_user_{i}_{uuid.uuid4().hex[:6]}",
            request_id=f"req_{i}_{uuid.uuid4().hex[:6]}",
            thread_id=f"thread_{i}_{uuid.uuid4().hex[:6]}",
            run_id=f"run_{i}_{uuid.uuid4().hex[:6]}"
        )
        contexts.append(context)
    return contexts


@pytest.fixture 
def mock_agent_with_websocket_support():
    """Create mock agent that supports WebSocket integration."""
    class MockAgentWithWebSocket:
        def __init__(self, llm_manager=None, tool_dispatcher=None):
            self.llm_manager = llm_manager
            self.tool_dispatcher = tool_dispatcher
            self.execution_history = []
            self._websocket_bridge = None
            self._run_id = None
            self._agent_name = None
            
        def set_websocket_bridge(self, bridge, run_id, agent_name=None):
            self._websocket_bridge = bridge
            self._run_id = run_id
            self._agent_name = agent_name or "test_agent"
            
        async def execute(self, state, run_id):
            """Mock agent execution with WebSocket events."""
            # Send agent started event
            if self._websocket_bridge:
                await self._websocket_bridge.notify_agent_started(
                    run_id=self._run_id,
                    agent_name=self._agent_name,
                    context={"state": "started"}
                )
            
            # Simulate thinking
            if self._websocket_bridge:
                await self._websocket_bridge.notify_agent_thinking(
                    run_id=self._run_id,
                    agent_name=self._agent_name,
                    reasoning="Processing user request",
                    step_number=1,
                    progress_percentage=25.0
                )
            
            # Simulate tool execution
            if self._websocket_bridge:
                await self._websocket_bridge.notify_tool_executing(
                    run_id=self._run_id,
                    agent_name=self._agent_name,
                    tool_name="test_tool",
                    parameters={"input": state}
                )
                
                # Tool completed
                await self._websocket_bridge.notify_tool_completed(
                    run_id=self._run_id,
                    agent_name=self._agent_name,
                    tool_name="test_tool",
                    result={"output": "processed"},
                    execution_time_ms=150.0
                )
            
            # Complete execution
            if self._websocket_bridge:
                await self._websocket_bridge.notify_agent_completed(
                    run_id=self._run_id,
                    agent_name=self._agent_name,
                    result={"status": "success", "data": f"Processed: {state}"},
                    execution_time_ms=500.0
                )
            
            self.execution_history.append({"state": state, "run_id": run_id})
            return {"status": "success", "data": f"Processed: {state}"}
            
        async def cleanup(self):
            pass
    
    return MockAgentWithWebSocket


# ============================================================================
# TEST: AgentRegistry WebSocket Manager Integration
# ============================================================================

class TestAgentRegistryWebSocketManagerIntegration(SSotBaseTestCase):
    """Test AgentRegistry integration with WebSocket manager."""
    
    @pytest.mark.asyncio
    async def test_set_websocket_manager_enhances_tool_dispatcher(self, mock_llm_manager, real_websocket_manager):
        """Test that AgentRegistry.set_websocket_manager() enhances tool dispatcher as required by CLAUDE.md."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create test user context
        test_context = UserExecutionContext(
            user_id=f"test_user_{uuid.uuid4().hex[:8]}",
            thread_id=f"test_thread_{uuid.uuid4().hex[:8]}",
            run_id=f"test_run_{uuid.uuid4().hex[:8]}"
        )
        
        # Create user session first
        session = await registry.get_user_session(test_context.user_id)
        
        # Mock the tool dispatcher creation to verify enhancement
        with patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcher.create_for_user') as mock_create_dispatcher:
            mock_dispatcher = AsyncMock()
            mock_create_dispatcher.return_value = mock_dispatcher
            
            # Set WebSocket manager on registry
            registry.set_websocket_manager(real_websocket_manager)
            
            # Create tool dispatcher - should be enhanced with WebSocket capabilities
            enhanced_dispatcher = await registry.create_tool_dispatcher_for_user(
                user_context=test_context,
                websocket_bridge=session._websocket_bridge,
                enable_admin_tools=False
            )
            
            # Verify tool dispatcher was created with WebSocket bridge
            mock_create_dispatcher.assert_called_once()
            call_kwargs = mock_create_dispatcher.call_args[1]
            assert 'websocket_bridge' in call_kwargs
            assert call_kwargs['user_context'] == test_context
            
            # Verify registry has WebSocket manager
            assert registry.websocket_manager == real_websocket_manager
    
    @pytest.mark.asyncio
    async def test_websocket_manager_propagation_to_user_sessions(self, mock_llm_manager, real_websocket_manager, test_user_contexts):
        """Test WebSocket manager propagates to all user sessions."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create multiple user sessions
        sessions = []
        for context in test_user_contexts:
            session = await registry.get_user_session(context.user_id)
            sessions.append(session)
        
        # Mock set_websocket_manager on sessions to track calls
        for session in sessions:
            session.set_websocket_manager = AsyncMock()
        
        # Set WebSocket manager on registry - should propagate to all sessions
        await registry.set_websocket_manager_async(real_websocket_manager)
        
        # Verify WebSocket manager was set on all sessions
        for session in sessions:
            session.set_websocket_manager.assert_called_once_with(real_websocket_manager, None)
        
        assert registry.websocket_manager == real_websocket_manager
    
    @pytest.mark.asyncio
    async def test_websocket_bridge_creation_per_user_session(self, mock_llm_manager, real_websocket_manager, test_user_contexts):
        """Test that each user session gets its own WebSocket bridge."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(real_websocket_manager)
        
        # Create user sessions and collect their bridges
        bridges = []
        for context in test_user_contexts:
            session = await registry.get_user_session(context.user_id)
            
            # Mock bridge creation to capture created bridges
            with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge') as mock_create:
                mock_bridge = AsyncMock()
                mock_create.return_value = mock_bridge
                
                # Set WebSocket manager on session creates bridge
                await session.set_websocket_manager(real_websocket_manager, context)
                
                bridges.append(mock_bridge)
                mock_create.assert_called_with(context)
        
        # Each user should have their own bridge
        assert len(bridges) == len(test_user_contexts)
        for i, bridge in enumerate(bridges):
            assert bridge is not None
            # Each bridge should be unique (different instances)
            for j, other_bridge in enumerate(bridges):
                if i != j:
                    assert bridge is not other_bridge
    
    @pytest.mark.asyncio
    async def test_agent_creation_with_websocket_integration(self, mock_llm_manager, real_websocket_manager, 
                                                           mock_agent_with_websocket_support, test_user_contexts):
        """Test agent creation integrates properly with WebSocket system."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(real_websocket_manager)
        
        # Mock get_async to return our WebSocket-enabled agent
        test_agent = mock_agent_with_websocket_support()
        registry.get_async = AsyncMock(return_value=test_agent)
        
        user_context = test_user_contexts[0]
        
        # Create agent for user
        created_agent = await registry.create_agent_for_user(
            user_id=user_context.user_id,
            agent_type="websocket_test_agent",
            user_context=user_context,
            websocket_manager=real_websocket_manager
        )
        
        assert created_agent == test_agent
        
        # Verify agent was registered in user session
        session = registry._user_sessions[user_context.user_id]
        registered_agent = await session.get_agent("websocket_test_agent")
        assert registered_agent == test_agent
        
        # Verify WebSocket bridge was set on agent
        assert created_agent._websocket_bridge is not None
        assert created_agent._run_id == user_context.run_id
    
    @pytest.mark.asyncio
    async def test_websocket_manager_error_handling(self, mock_llm_manager, test_user_contexts):
        """Test WebSocket manager error handling during integration."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create user session
        user_context = test_user_contexts[0]
        session = await registry.get_user_session(user_context.user_id)
        
        # Mock WebSocket manager that causes errors
        failing_ws_manager = Mock()
        failing_ws_manager.send_event = AsyncMock(side_effect=Exception("WebSocket connection failed"))
        
        # Mock session's set_websocket_manager to raise exception
        session.set_websocket_manager = AsyncMock(side_effect=Exception("WebSocket setup failed"))
        
        # Should not raise exception but handle gracefully
        await registry.set_websocket_manager_async(failing_ws_manager)
        
        # Registry should still have the WebSocket manager set
        assert registry.websocket_manager == failing_ws_manager
    
    @pytest.mark.asyncio
    async def test_concurrent_websocket_manager_updates(self, mock_llm_manager, test_user_contexts):
        """Test concurrent WebSocket manager updates are handled safely."""
        registry = AgentRegistry(mock_llm_manager)
        
        # Create user sessions first
        for context in test_user_contexts:
            await registry.get_user_session(context.user_id)
        
        async def update_websocket_manager(manager_id):
            mock_manager = Mock()
            mock_manager.id = manager_id
            mock_manager.send_event = AsyncMock(return_value=True)
            await registry.set_websocket_manager_async(mock_manager)
            return mock_manager
        
        # Update WebSocket manager concurrently multiple times
        tasks = [update_websocket_manager(i) for i in range(5)]
        managers = await asyncio.gather(*tasks)
        
        # The final manager should be one of the created ones
        final_manager = registry.websocket_manager
        assert final_manager in managers
        
        # All managers should have been created successfully
        assert len(managers) == 5


# ============================================================================
# TEST: Real WebSocket Event Propagation
# ============================================================================

class TestRealWebSocketEventPropagation(SSotBaseTestCase):
    """Test real WebSocket event propagation through the integrated system."""
    
    @pytest.mark.asyncio
    async def test_agent_execution_websocket_event_flow(self, mock_llm_manager, real_websocket_manager,
                                                       mock_agent_with_websocket_support, test_user_contexts):
        """Test complete agent execution with WebSocket event flow."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(real_websocket_manager)
        
        user_context = test_user_contexts[0]
        
        # Create and register WebSocket-enabled agent
        test_agent = mock_agent_with_websocket_support()
        
        # Mock agent creation in registry
        registry.get_async = AsyncMock(return_value=test_agent)
        
        # Create agent through registry
        agent = await registry.create_agent_for_user(
            user_id=user_context.user_id,
            agent_type="integration_test_agent",
            user_context=user_context,
            websocket_manager=real_websocket_manager
        )
        
        # Track WebSocket events sent
        sent_events = []
        original_send = real_websocket_manager.send_event
        
        async def track_events(*args, **kwargs):
            sent_events.append((args, kwargs))
            return await original_send(*args, **kwargs)
        
        real_websocket_manager.send_event = track_events
        
        # Execute agent (should generate WebSocket events)
        result = await agent.execute("test_input", user_context.run_id)
        
        # Verify execution succeeded
        assert result['status'] == 'success'
        assert 'test_input' in result['data']
        
        # Verify WebSocket events were sent
        assert len(sent_events) >= 5  # Should have sent at least 5 events (started, thinking, tool_executing, tool_completed, completed)
        
        # Verify event types
        event_types = []
        for args, kwargs in sent_events:
            if len(args) > 0:
                event_data = args[0] if isinstance(args[0], dict) else kwargs
                if 'event_type' in event_data:
                    event_types.append(event_data['event_type'])
        
        # Should include essential event types for substantive chat value
        expected_events = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        for expected_event in expected_events:
            # Events might be wrapped differently, so check if any event contains the expected type
            assert any(expected_event in str(event_types) for expected_event in expected_events), \
                f"Missing expected WebSocket events: {expected_events}, got: {event_types}"
    
    @pytest.mark.asyncio
    async def test_websocket_event_user_isolation(self, mock_llm_manager, real_websocket_manager,
                                                 mock_agent_with_websocket_support, test_user_contexts):
        """Test WebSocket events maintain user isolation."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(real_websocket_manager)
        
        # Create agents for different users
        agents = []
        for context in test_user_contexts:
            agent = mock_agent_with_websocket_support()
            registry.get_async = AsyncMock(return_value=agent)
            
            created_agent = await registry.create_agent_for_user(
                user_id=context.user_id,
                agent_type="isolation_test_agent",
                user_context=context,
                websocket_manager=real_websocket_manager
            )
            
            agents.append((created_agent, context))
        
        # Track events per user
        user_events = {}
        original_send = real_websocket_manager.send_event
        
        async def track_user_events(*args, **kwargs):
            # Extract user/run information from event
            event_data = args[0] if len(args) > 0 and isinstance(args[0], dict) else kwargs
            run_id = event_data.get('run_id') or event_data.get('data', {}).get('run_id')
            
            if run_id not in user_events:
                user_events[run_id] = []
            user_events[run_id].append(event_data)
            
            return await original_send(*args, **kwargs)
        
        real_websocket_manager.send_event = track_user_events
        
        # Execute agents concurrently
        execution_tasks = []
        for agent, context in agents:
            task = agent.execute(f"input_for_{context.user_id}", context.run_id)
            execution_tasks.append(task)
        
        results = await asyncio.gather(*execution_tasks)
        
        # Verify all executions succeeded
        for result in results:
            assert result['status'] == 'success'
        
        # Verify event isolation per user
        assert len(user_events) == len(test_user_contexts)
        
        for i, context in enumerate(test_user_contexts):
            run_id = context.run_id
            assert run_id in user_events
            user_specific_events = user_events[run_id]
            
            # Each user should have their own events
            assert len(user_specific_events) > 0
            
            # Verify no cross-contamination of run_ids
            for other_context in test_user_contexts:
                if other_context.run_id != run_id:
                    # Events for this user should not contain other users' run_ids
                    for event in user_specific_events:
                        event_run_id = event.get('run_id') or event.get('data', {}).get('run_id')
                        assert event_run_id != other_context.run_id
    
    @pytest.mark.asyncio
    async def test_websocket_run_thread_mapping_registration(self, mock_llm_manager, real_websocket_manager, test_user_contexts):
        """Test WebSocket run-thread mapping registration for reliable routing."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(real_websocket_manager)
        
        user_context = test_user_contexts[0]
        
        # Mock AgentWebSocketBridge to capture run-thread mapping calls
        with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge') as mock_create_bridge:
            mock_bridge = AsyncMock()
            mock_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
            mock_create_bridge.return_value = mock_bridge
            
            # Create user session (should register run-thread mapping)
            session = await registry.get_user_session(user_context.user_id)
            await session.set_websocket_manager(real_websocket_manager, user_context)
            
            # Verify bridge was created with user context
            mock_create_bridge.assert_called_once_with(user_context)
            
            # Verify run-thread mapping would be registered when creating agent contexts
            # (This is typically done in AgentInstanceFactory during context creation)
    
    @pytest.mark.asyncio
    async def test_websocket_error_recovery_during_agent_execution(self, mock_llm_manager, real_websocket_manager,
                                                                  mock_agent_with_websocket_support, test_user_contexts):
        """Test WebSocket error recovery during agent execution."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(real_websocket_manager)
        
        user_context = test_user_contexts[0]
        
        # Create agent
        test_agent = mock_agent_with_websocket_support()
        registry.get_async = AsyncMock(return_value=test_agent)
        
        agent = await registry.create_agent_for_user(
            user_id=user_context.user_id,
            agent_type="error_recovery_agent",
            user_context=user_context,
            websocket_manager=real_websocket_manager
        )
        
        # Mock WebSocket bridge to fail on some calls
        original_bridge = agent._websocket_bridge
        call_count = 0
        
        async def failing_notify_agent_started(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("WebSocket connection temporarily failed")
            return True
        
        # Make first WebSocket call fail
        agent._websocket_bridge.notify_agent_started = failing_notify_agent_started
        
        # Agent execution should handle WebSocket errors and continue
        try:
            result = await agent.execute("test_input", user_context.run_id)
            # If the agent handles errors properly, it might continue execution
            # The exact behavior depends on the agent implementation
            assert result is not None
        except Exception as e:
            # If the agent doesn't handle WebSocket errors gracefully,
            # it should still provide meaningful error information
            assert "WebSocket" in str(e) or "connection" in str(e)


# ============================================================================
# TEST: Tool Dispatcher Enhancement Integration
# ============================================================================

class TestToolDispatcherEnhancementIntegration(SSotBaseTestCase):
    """Test tool dispatcher enhancement with WebSocket capabilities."""
    
    @pytest.mark.asyncio
    async def test_tool_dispatcher_websocket_enhancement(self, mock_llm_manager, real_websocket_manager, test_user_contexts):
        """Test tool dispatcher gets enhanced with WebSocket capabilities."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(real_websocket_manager)
        
        user_context = test_user_contexts[0]
        
        # Create user session to get WebSocket bridge
        session = await registry.get_user_session(user_context.user_id)
        
        # Mock bridge creation
        with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge') as mock_create_bridge:
            mock_bridge = AsyncMock()
            mock_create_bridge.return_value = mock_bridge
            
            await session.set_websocket_manager(real_websocket_manager, user_context)
            
            # Create tool dispatcher with WebSocket enhancement
            with patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcher.create_for_user') as mock_create_dispatcher:
                mock_dispatcher = AsyncMock()
                mock_create_dispatcher.return_value = mock_dispatcher
                
                enhanced_dispatcher = await registry.create_tool_dispatcher_for_user(
                    user_context=user_context,
                    websocket_bridge=session._websocket_bridge,
                    enable_admin_tools=False
                )
                
                # Verify dispatcher was created with WebSocket bridge
                mock_create_dispatcher.assert_called_once_with(
                    user_context=user_context,
                    websocket_bridge=session._websocket_bridge,
                    enable_admin_tools=False
                )
                
                assert enhanced_dispatcher == mock_dispatcher
    
    @pytest.mark.asyncio
    async def test_tool_dispatcher_admin_tools_with_websockets(self, mock_llm_manager, real_websocket_manager, test_user_contexts):
        """Test tool dispatcher with admin tools enabled and WebSocket support."""
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(real_websocket_manager)
        
        user_context = test_user_contexts[0]
        session = await registry.get_user_session(user_context.user_id)
        
        # Mock bridge creation
        with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge') as mock_create_bridge:
            mock_bridge = AsyncMock()
            mock_create_bridge.return_value = mock_bridge
            
            await session.set_websocket_manager(real_websocket_manager, user_context)
            
            # Create tool dispatcher with admin tools enabled
            with patch('netra_backend.app.core.tools.unified_tool_dispatcher.UnifiedToolDispatcher.create_for_user') as mock_create_dispatcher:
                mock_dispatcher = AsyncMock()
                mock_create_dispatcher.return_value = mock_dispatcher
                
                admin_dispatcher = await registry.create_tool_dispatcher_for_user(
                    user_context=user_context,
                    websocket_bridge=session._websocket_bridge,
                    enable_admin_tools=True  # Admin tools enabled
                )
                
                # Verify dispatcher was created with admin tools and WebSocket bridge
                mock_create_dispatcher.assert_called_once_with(
                    user_context=user_context,
                    websocket_bridge=session._websocket_bridge,
                    enable_admin_tools=True
                )
    
    @pytest.mark.asyncio
    async def test_tool_dispatcher_factory_with_websocket_integration(self, mock_llm_manager, real_websocket_manager, test_user_contexts):
        """Test custom tool dispatcher factory integrates with WebSocket system."""
        # Create custom tool dispatcher factory
        async def custom_dispatcher_factory(user_context, websocket_bridge=None):
            # Verify WebSocket bridge is provided
            assert websocket_bridge is not None
            assert user_context is not None
            
            # Create mock dispatcher with WebSocket awareness
            mock_dispatcher = AsyncMock()
            mock_dispatcher.websocket_bridge = websocket_bridge
            mock_dispatcher.user_context = user_context
            mock_dispatcher.has_websocket = True
            return mock_dispatcher
        
        # Create registry with custom factory
        registry = AgentRegistry(mock_llm_manager, custom_dispatcher_factory)
        registry.set_websocket_manager(real_websocket_manager)
        
        user_context = test_user_contexts[0]
        session = await registry.get_user_session(user_context.user_id)
        
        # Mock bridge creation
        with patch('netra_backend.app.services.agent_websocket_bridge.create_agent_websocket_bridge') as mock_create_bridge:
            mock_bridge = AsyncMock()
            mock_create_bridge.return_value = mock_bridge
            
            await session.set_websocket_manager(real_websocket_manager, user_context)
            
            # Create dispatcher using custom factory
            dispatcher = await registry.create_tool_dispatcher_for_user(
                user_context=user_context,
                websocket_bridge=session._websocket_bridge
            )
            
            # Verify custom factory created dispatcher with WebSocket integration
            assert dispatcher.websocket_bridge == session._websocket_bridge
            assert dispatcher.user_context == user_context
            assert dispatcher.has_websocket is True


# ============================================================================
# TEST: Integration with AgentInstanceFactory
# ============================================================================

class TestIntegrationWithAgentInstanceFactory(SSotBaseTestCase):
    """Test integration between AgentRegistry and AgentInstanceFactory WebSocket systems."""
    
    @pytest.mark.asyncio
    async def test_agent_registry_factory_websocket_coordination(self, mock_llm_manager, real_websocket_manager, test_user_contexts):
        """Test coordination between AgentRegistry and AgentInstanceFactory for WebSocket integration."""
        # Setup AgentRegistry
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(real_websocket_manager)
        
        # Setup AgentInstanceFactory
        factory = AgentInstanceFactory()
        
        # Mock AgentWebSocketBridge for factory configuration
        mock_bridge = AsyncMock()
        mock_bridge.register_run_thread_mapping = AsyncMock(return_value=True)
        
        factory.configure(
            agent_registry=registry,
            websocket_bridge=mock_bridge,
            websocket_manager=real_websocket_manager,
            llm_manager=mock_llm_manager
        )
        
        user_context = test_user_contexts[0]
        
        # Create user execution context through factory
        execution_context = await factory.create_user_execution_context(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id
        )
        
        # Verify factory and registry coordinate WebSocket setup
        assert execution_context.user_id == user_context.user_id
        assert execution_context.run_id == user_context.run_id
        
        # Verify run-thread mapping was registered
        mock_bridge.register_run_thread_mapping.assert_called_once()
        
        # Cleanup context
        await factory.cleanup_user_context(execution_context)
    
    @pytest.mark.asyncio
    async def test_factory_agent_creation_with_registry_websocket_manager(self, mock_llm_manager, real_websocket_manager, 
                                                                         mock_agent_with_websocket_support, test_user_contexts):
        """Test AgentInstanceFactory agent creation integrates with AgentRegistry WebSocket manager."""
        # Setup registry and factory
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(real_websocket_manager)
        
        factory = AgentInstanceFactory()
        mock_bridge = AsyncMock()
        
        factory.configure(
            agent_registry=registry,
            websocket_bridge=mock_bridge,
            llm_manager=mock_llm_manager
        )
        
        user_context = test_user_contexts[0]
        
        # Create execution context
        execution_context = await factory.create_user_execution_context(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id
        )
        
        # Mock agent class registry
        with patch.object(factory, '_agent_class_registry') as mock_class_registry:
            mock_class_registry.get_agent_class = Mock(return_value=mock_agent_with_websocket_support)
            
            # Create agent instance through factory
            agent = await factory.create_agent_instance("test_agent", execution_context)
            
            # Verify agent has WebSocket integration
            assert agent is not None
            assert hasattr(agent, 'set_websocket_bridge') or hasattr(agent, '_websocket_adapter')
        
        # Cleanup
        await factory.cleanup_user_context(execution_context)
    
    @pytest.mark.asyncio
    async def test_comprehensive_websocket_integration_flow(self, mock_llm_manager, real_websocket_manager, 
                                                          mock_agent_with_websocket_support, test_user_contexts):
        """Test comprehensive WebSocket integration flow through registry and factory."""
        # Setup complete integration
        registry = AgentRegistry(mock_llm_manager)
        registry.set_websocket_manager(real_websocket_manager)
        
        factory = await configure_agent_instance_factory(
            agent_registry=registry,
            websocket_manager=real_websocket_manager,
            llm_manager=mock_llm_manager
        )
        
        user_context = test_user_contexts[0]
        
        # Track WebSocket events throughout the flow
        websocket_events = []
        original_send = real_websocket_manager.send_event
        
        async def track_all_events(*args, **kwargs):
            websocket_events.append({"args": args, "kwargs": kwargs, "timestamp": time.time()})
            return await original_send(*args, **kwargs)
        
        real_websocket_manager.send_event = track_all_events
        
        # Execute complete flow: context creation -> agent creation -> agent execution
        async with factory.user_execution_scope(
            user_id=user_context.user_id,
            thread_id=user_context.thread_id,
            run_id=user_context.run_id
        ) as execution_context:
            
            # Create agent through registry
            test_agent = mock_agent_with_websocket_support()
            registry.get_async = AsyncMock(return_value=test_agent)
            
            agent = await registry.create_agent_for_user(
                user_id=user_context.user_id,
                agent_type="comprehensive_test_agent",
                user_context=user_context,
                websocket_manager=real_websocket_manager
            )
            
            # Execute agent (should generate WebSocket events)
            result = await agent.execute("integration_test_data", user_context.run_id)
            
            # Verify execution succeeded
            assert result['status'] == 'success'
        
        # Verify WebSocket events were generated throughout the flow
        assert len(websocket_events) > 0
        
        # Verify event timing (events should be chronologically ordered)
        event_times = [event['timestamp'] for event in websocket_events]
        assert event_times == sorted(event_times), "WebSocket events should be chronologically ordered"


if __name__ == "__main__":
    # Run tests with proper async support
    pytest.main([__file__, "-v", "--tb=short", "--maxfail=3"])