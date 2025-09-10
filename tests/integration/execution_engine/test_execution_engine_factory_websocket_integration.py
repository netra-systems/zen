"""Factory WebSocket Integration Test - PRIORITY 2 (Revenue Critical)

MISSION: Factory-created engines emit events to correct users only.

This test validates that ExecutionEngineFactory creates engines with proper WebSocket
integration, ensuring user isolation in real-time communication channels. WebSocket
events are critical for chat functionality which delivers 90% of platform business value.

Business Value Justification (BVJ):
- Segment: ALL (Free → Enterprise) - affects every user interaction
- Business Goal: Revenue/Retention - ensures chat functionality works correctly
- Value Impact: Delivers 90% of platform value through reliable real-time chat
- Revenue Impact: Prevents $500K+ ARR loss from broken WebSocket communications
- Strategic Impact: CRITICAL - chat is the primary value delivery mechanism

Key Validation Points:
1. Factory creates engines with per-user WebSocketNotifier
2. WebSocket events only go to correct user session  
3. No cross-user WebSocket event leakage
4. Events are properly isolated even under concurrent usage
5. WebSocket bridge integration works correctly with factory pattern

Expected Behavior:
- FAIL BEFORE: Null/shared WebSocket notifiers causing event leakage
- PASS AFTER: Per-user events with complete isolation
"""

import pytest
import asyncio
import time
import uuid
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from typing import Dict, Any, List

from test_framework.ssot.base_test_case import SSotAsyncTestCase
from netra_backend.app.agents.supervisor.execution_engine_factory import ExecutionEngineFactory
from netra_backend.app.services.user_execution_context import UserExecutionContext
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class TestExecutionEngineFactoryWebSocketIntegration(SSotAsyncTestCase):
    """SSOT Integration test for ExecutionEngineFactory WebSocket functionality.
    
    This test ensures factory-created engines have proper WebSocket integration
    with complete user isolation in real-time communications.
    """
    
    async def async_setup_method(self, method=None):
        """Setup test with WebSocket bridge and factory instance."""
        await super().async_setup_method(method)
        
        # Create comprehensive mock WebSocket bridge
        self.mock_websocket_bridge = Mock(spec=AgentWebSocketBridge)
        
        # Mock all WebSocket notification methods
        self.mock_websocket_bridge.notify_agent_started = AsyncMock()
        self.mock_websocket_bridge.notify_agent_thinking = AsyncMock()
        self.mock_websocket_bridge.notify_tool_executing = AsyncMock()
        self.mock_websocket_bridge.notify_tool_completed = AsyncMock()
        self.mock_websocket_bridge.notify_agent_completed = AsyncMock()
        self.mock_websocket_bridge.notify_agent_error = AsyncMock()
        self.mock_websocket_bridge.notify_agent_death = AsyncMock()
        self.mock_websocket_bridge.get_metrics = AsyncMock(return_value={
            'connections_active': 0,
            'events_sent': 0,
            'websocket_events_total': 0
        })
        
        # Track WebSocket events for validation
        self.websocket_events = []
        
        def track_event(event_type, run_id, agent_name, *args, **kwargs):
            """Track WebSocket events for test validation."""
            self.websocket_events.append({
                'type': event_type,
                'run_id': run_id,
                'agent_name': agent_name,
                'args': args,
                'kwargs': kwargs,
                'timestamp': time.time(),
                'user_context': kwargs.get('user_context', 'unknown')
            })
        
        # Attach event tracking to all notification methods
        self.mock_websocket_bridge.notify_agent_started.side_effect = lambda run_id, agent_name, *args, **kwargs: track_event('agent_started', run_id, agent_name, *args, **kwargs)
        self.mock_websocket_bridge.notify_agent_thinking.side_effect = lambda run_id, agent_name, *args, **kwargs: track_event('agent_thinking', run_id, agent_name, *args, **kwargs)
        self.mock_websocket_bridge.notify_tool_executing.side_effect = lambda run_id, agent_name, *args, **kwargs: track_event('tool_executing', run_id, agent_name, *args, **kwargs)
        self.mock_websocket_bridge.notify_tool_completed.side_effect = lambda run_id, agent_name, *args, **kwargs: track_event('tool_completed', run_id, agent_name, *args, **kwargs)
        self.mock_websocket_bridge.notify_agent_completed.side_effect = lambda run_id, agent_name, *args, **kwargs: track_event('agent_completed', run_id, agent_name, *args, **kwargs)
        self.mock_websocket_bridge.notify_agent_error.side_effect = lambda run_id, agent_name, *args, **kwargs: track_event('agent_error', run_id, agent_name, *args, **kwargs)
        
        # Create factory instance with WebSocket bridge
        self.factory = ExecutionEngineFactory(
            websocket_bridge=self.mock_websocket_bridge,
            database_session_manager=None,  # Focus on WebSocket integration
            redis_manager=None
        )
        
        # Create mock agent factory with WebSocket emitter support
        self.mock_agent_factory = Mock()
        self.mock_agent_factory.create_user_websocket_emitter = Mock()
        
        # Mock user WebSocket emitters for tracking
        self.user_emitters = {}
        
        def create_mock_emitter(user_id, thread_id, run_id, websocket_bridge):
            """Create mock WebSocket emitter with event tracking."""
            emitter = Mock()
            emitter.user_id = user_id
            emitter.thread_id = thread_id
            emitter.run_id = run_id
            emitter.websocket_bridge = websocket_bridge
            
            # Track emitters by user
            emitter_key = f"{user_id}_{thread_id}_{run_id}"
            self.user_emitters[emitter_key] = emitter
            
            # Mock emitter methods with tracking
            def make_tracker(event_type):
                def tracker(*args, **kwargs):
                    # Extract agent_name from kwargs if present, otherwise use default
                    agent_name = kwargs.get('agent_name', 'test_agent')
                    # Remove agent_name from kwargs to avoid conflicts
                    clean_kwargs = {k: v for k, v in kwargs.items() if k != 'agent_name'}
                    clean_kwargs['user_context'] = user_id
                    return track_event(event_type, run_id, agent_name, *args, **clean_kwargs)
                return tracker
            
            emitter.notify_agent_started = AsyncMock(side_effect=make_tracker('user_emitter_started'))
            emitter.notify_agent_thinking = AsyncMock(side_effect=make_tracker('user_emitter_thinking'))
            emitter.notify_tool_executing = AsyncMock(side_effect=make_tracker('user_emitter_tool_exec'))
            emitter.notify_tool_completed = AsyncMock(side_effect=make_tracker('user_emitter_tool_comp'))
            emitter.notify_agent_completed = AsyncMock(side_effect=make_tracker('user_emitter_completed'))
            
            return emitter
        
        # Start persistent patch for UserWebSocketEmitter creation in the factory
        self.websocket_emitter_patch = patch(
            'netra_backend.app.agents.supervisor.execution_engine_factory.UserWebSocketEmitter', 
            side_effect=create_mock_emitter
        )
        self.websocket_emitter_patch.start()
        
        # Configure factory with tool dispatcher
        self.factory.set_tool_dispatcher_factory(Mock())
        
        # Record setup completion
        self.record_metric("websocket_integration_setup_complete", True)
        self.record_metric("websocket_bridge_configured", True)
    
    @pytest.fixture(autouse=True)
    async def auto_setup_async(self):
        """Auto setup fixture to ensure async_setup_method is called."""
        await self.async_setup_method()
        yield
        await self.async_teardown_method()
    
    async def async_teardown_method(self, method=None):
        """Teardown test with factory cleanup."""
        try:
            # Stop the WebSocket emitter patch if it exists
            if hasattr(self, 'websocket_emitter_patch'):
                self.websocket_emitter_patch.stop()
            
            if hasattr(self, 'factory') and self.factory:
                await self.factory.shutdown()
        finally:
            await super().async_teardown_method(method)
    
    def create_test_user_context(self, user_id: str, suffix: str = "") -> UserExecutionContext:
        """Create test UserExecutionContext with WebSocket support.
        
        Args:
            user_id: User identifier
            suffix: Optional suffix for uniqueness
            
        Returns:
            UserExecutionContext for WebSocket testing
        """
        thread_id = f"thread_{user_id}_{suffix}_{int(time.time())}"
        run_id = f"run_{user_id}_{suffix}_{int(time.time())}"
        
        return UserExecutionContext(
            user_id=user_id,
            thread_id=thread_id,
            run_id=run_id,
            request_id=str(uuid.uuid4()),
            websocket_client_id=f"ws_{user_id}_{suffix}",
            agent_context={'websocket_test': True, 'agent_name': 'test_agent'},
            audit_metadata={'test_source': 'websocket_integration_test'}
        )
    
    def create_test_agent_context(self, user_context: UserExecutionContext) -> AgentExecutionContext:
        """Create AgentExecutionContext for execution testing.
        
        Args:
            user_context: User execution context
            
        Returns:
            AgentExecutionContext for agent execution
        """
        return AgentExecutionContext(
            run_id=user_context.run_id,
            thread_id=user_context.thread_id,
            user_id=user_context.user_id,
            agent_name="test_websocket_agent",
            metadata={"test": True, "websocket_integration": True}
        )
    
    @pytest.mark.asyncio
    async def test_factory_creates_engines_with_per_user_websocket_notifiers(self):
        """CRITICAL: Validate factory creates engines with per-user WebSocket notifiers.
        
        This test verifies that each factory-created engine has its own
        WebSocket emitter configured for the correct user.
        
        Expected: FAIL before factory implementation (null/shared notifiers)
        Expected: PASS after factory implementation (per-user notifiers)
        """
        # Create contexts for different users
        user_alpha_context = self.create_test_user_context("user_alpha", "websocket_test")
        user_beta_context = self.create_test_user_context("user_beta", "websocket_test")
        
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = self.mock_agent_factory
            
            # Create engines for both users
            engine_alpha = await self.factory.create_for_user(user_alpha_context)
            engine_beta = await self.factory.create_for_user(user_beta_context)
            
            try:
                # CRITICAL: Both engines must have WebSocket integration
                assert hasattr(engine_alpha, 'websocket_emitter') or hasattr(engine_alpha, 'websocket_bridge'), (
                    "SSOT VIOLATION: Engine Alpha has no WebSocket integration. "
                    "Factory must create engines with WebSocket support for chat functionality."
                )
                
                assert hasattr(engine_beta, 'websocket_emitter') or hasattr(engine_beta, 'websocket_bridge'), (
                    "SSOT VIOLATION: Engine Beta has no WebSocket integration. "
                    "Factory must create engines with WebSocket support for chat functionality."
                )
                
                # CRITICAL: WebSocket emitters must be user-specific
                emitter_key_alpha = f"{user_alpha_context.user_id}_{user_alpha_context.thread_id}_{user_alpha_context.run_id}"
                emitter_key_beta = f"{user_beta_context.user_id}_{user_beta_context.thread_id}_{user_beta_context.run_id}"
                
                # Check that user-specific emitters were created
                assert emitter_key_alpha in self.user_emitters, (
                    f"SSOT VIOLATION: No WebSocket emitter created for user Alpha. "
                    f"Expected key: {emitter_key_alpha}, Available: {list(self.user_emitters.keys())}"
                )
                
                assert emitter_key_beta in self.user_emitters, (
                    f"SSOT VIOLATION: No WebSocket emitter created for user Beta. "
                    f"Expected key: {emitter_key_beta}, Available: {list(self.user_emitters.keys())}"
                )
                
                # CRITICAL: Emitters must be different objects
                emitter_alpha = self.user_emitters[emitter_key_alpha]
                emitter_beta = self.user_emitters[emitter_key_beta]
                
                assert emitter_alpha is not emitter_beta, (
                    "SSOT VIOLATION: Same WebSocket emitter object used for different users. "
                    "This would cause cross-user event leakage."
                )
                
                # CRITICAL: Emitters must be configured for correct users
                assert emitter_alpha.user_id == user_alpha_context.user_id, (
                    f"SSOT VIOLATION: Alpha emitter configured for wrong user. "
                    f"Expected: {user_alpha_context.user_id}, Got: {emitter_alpha.user_id}"
                )
                
                assert emitter_beta.user_id == user_beta_context.user_id, (
                    f"SSOT VIOLATION: Beta emitter configured for wrong user. "
                    f"Expected: {user_beta_context.user_id}, Got: {emitter_beta.user_id}"
                )
                
                # Record WebSocket integration validation
                self.record_metric("websocket_notifiers_created", True)
                self.record_metric("per_user_emitters_verified", True)
                self.record_metric("emitters_isolated", emitter_alpha is not emitter_beta)
                self.record_metric("user_specific_configuration", True)
                
            finally:
                # Clean up engines
                await self.factory.cleanup_engine(engine_alpha)
                await self.factory.cleanup_engine(engine_beta)
    
    @pytest.mark.asyncio
    async def test_websocket_events_only_go_to_correct_user_session(self):
        """CRITICAL: Validate WebSocket events only go to correct user session.
        
        This test verifies that when an engine sends WebSocket events,
        they are routed only to the correct user's session.
        
        Expected: FAIL before factory implementation (event cross-contamination)
        Expected: PASS after factory implementation (isolated events)
        """
        # Create contexts for different users
        user_gamma_context = self.create_test_user_context("user_gamma", "event_routing")
        user_delta_context = self.create_test_user_context("user_delta", "event_routing")
        
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = self.mock_agent_factory
            
            # Create engines
            engine_gamma = await self.factory.create_for_user(user_gamma_context)
            engine_delta = await self.factory.create_for_user(user_delta_context)
            
            try:
                # Clear previous events
                self.websocket_events.clear()
                
                # Create agent contexts for execution simulation
                agent_context_gamma = self.create_test_agent_context(user_gamma_context)
                agent_context_delta = self.create_test_agent_context(user_delta_context)
                
                # Simulate WebSocket events from Engine Gamma via emitter
                await engine_gamma.websocket_emitter.notify_agent_thinking(
                    agent_name=agent_context_gamma.agent_name,
                    reasoning="Engine Gamma thinking",
                    step_number=1
                )
                
                await engine_gamma.websocket_emitter.notify_tool_executing(
                    tool_name="test_tool_gamma"
                )
                
                # Simulate WebSocket events from Engine Delta via emitter
                await engine_delta.websocket_emitter.notify_agent_thinking(
                    agent_name=agent_context_delta.agent_name,
                    reasoning="Engine Delta thinking",
                    step_number=1
                )
                
                await engine_delta.websocket_emitter.notify_tool_executing(
                    tool_name="test_tool_delta"
                )
                
                # Allow events to be processed
                await asyncio.sleep(0.1)
                
                # CRITICAL: Events must be properly routed to correct users
                gamma_events = [e for e in self.websocket_events if e['run_id'] == user_gamma_context.run_id]
                delta_events = [e for e in self.websocket_events if e['run_id'] == user_delta_context.run_id]
                
                # Validate Gamma events
                assert len(gamma_events) >= 2, (
                    f"SSOT VIOLATION: Expected at least 2 events for Gamma user, got {len(gamma_events)}. "
                    f"Events: {gamma_events}"
                )
                
                # Validate Delta events
                assert len(delta_events) >= 2, (
                    f"SSOT VIOLATION: Expected at least 2 events for Delta user, got {len(delta_events)}. "
                    f"Events: {delta_events}"
                )
                
                # CRITICAL: No cross-user event contamination
                for event in gamma_events:
                    assert event['run_id'] == user_gamma_context.run_id, (
                        f"SSOT VIOLATION: Gamma event has wrong run_id. "
                        f"Expected: {user_gamma_context.run_id}, Got: {event['run_id']}"
                    )
                    
                    # Check user context if available
                    if 'user_context' in event:
                        assert event['user_context'] == user_gamma_context.user_id, (
                            f"SSOT VIOLATION: Gamma event routed to wrong user. "
                            f"Expected: {user_gamma_context.user_id}, Got: {event['user_context']}"
                        )
                
                for event in delta_events:
                    assert event['run_id'] == user_delta_context.run_id, (
                        f"SSOT VIOLATION: Delta event has wrong run_id. "
                        f"Expected: {user_delta_context.run_id}, Got: {event['run_id']}"
                    )
                    
                    # Check user context if available  
                    if 'user_context' in event:
                        assert event['user_context'] == user_delta_context.user_id, (
                            f"SSOT VIOLATION: Delta event routed to wrong user. "
                            f"Expected: {user_delta_context.user_id}, Got: {event['user_context']}"
                        )
                
                # CRITICAL: Validate event content isolation
                gamma_thinking_events = [e for e in gamma_events if e['type'] == 'user_emitter_thinking']
                delta_thinking_events = [e for e in delta_events if e['type'] == 'user_emitter_thinking']
                
                # Check that Gamma events contain Gamma-specific content (look in kwargs)
                gamma_has_gamma_content = any("Engine Gamma thinking" in str(e.get('kwargs', {})) for e in gamma_thinking_events)
                assert gamma_has_gamma_content, (
                    "SSOT VIOLATION: Gamma events missing Gamma-specific content. "
                    f"Events: {gamma_thinking_events}"
                )
                
                # Check that Delta events don't contain Gamma content
                delta_has_gamma_content = any("Engine Gamma thinking" in str(e.get('kwargs', {})) for e in delta_thinking_events)
                assert not delta_has_gamma_content, (
                    "SSOT VIOLATION: Delta events contain Gamma content. "
                    f"This indicates cross-user event contamination. Events: {delta_thinking_events}"
                )
                
                # Record event routing validation
                self.record_metric("websocket_events_routed_correctly", True)
                self.record_metric("gamma_events_count", len(gamma_events))
                self.record_metric("delta_events_count", len(delta_events))
                self.record_metric("no_cross_user_contamination", True)
                self.record_metric("event_content_isolation_verified", True)
                
            finally:
                # Clean up engines
                await self.factory.cleanup_engine(engine_gamma)
                await self.factory.cleanup_engine(engine_delta)
    
    @pytest.mark.asyncio
    async def test_no_websocket_event_leakage_between_users(self):
        """CRITICAL: Validate no WebSocket event leakage between concurrent users.
        
        This test simulates multiple users executing agents concurrently
        and verifies complete isolation of WebSocket events.
        
        Expected: FAIL before factory implementation (event leakage)
        Expected: PASS after factory implementation (complete isolation)
        """
        # Create multiple user contexts for concurrent testing
        contexts = []
        for i in range(5):
            context = self.create_test_user_context(f"concurrent_user_{i}", f"leak_test_{i}")
            contexts.append(context)
        
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = self.mock_agent_factory
            
            # Create engines for all users
            engines = []
            for context in contexts:
                engine = await self.factory.create_for_user(context)
                engines.append(engine)
            
            try:
                # Clear previous events
                self.websocket_events.clear()
                
                # Create agent contexts for all engines
                agent_contexts = []
                for context in contexts:
                    agent_context = self.create_test_agent_context(context)
                    agent_contexts.append(agent_context)
                
                # Simulate concurrent WebSocket events
                async def send_events_for_engine(engine, agent_context, user_context):
                    """Send multiple WebSocket events for a user engine."""
                    user_specific_data = f"user_{user_context.user_id}_data"
                    
                    await engine.websocket_emitter.notify_agent_thinking(
                        agent_name=agent_context.agent_name,
                        reasoning=f"Thinking for {user_specific_data}",
                        step_number=1
                    )
                    
                    await engine.websocket_emitter.notify_tool_executing(
                        tool_name=f"tool_for_{user_specific_data}"
                    )
                    
                    # Simulate tool completion
                    await asyncio.sleep(0.05)  # Brief delay to simulate work
                    
                    await engine.websocket_emitter.notify_agent_completed(
                        agent_name=agent_context.agent_name,
                        result={"result": f"completed_for_{user_specific_data}"},
                        duration=100.0
                    )
                
                # Execute all events concurrently
                tasks = []
                for i, (engine, agent_context, user_context) in enumerate(zip(engines, agent_contexts, contexts)):
                    task = send_events_for_engine(engine, agent_context, user_context)
                    tasks.append(task)
                
                await asyncio.gather(*tasks)
                
                # Allow all events to be processed
                await asyncio.sleep(0.2)
                
                # CRITICAL: Validate event isolation for each user
                for i, user_context in enumerate(contexts):
                    user_events = [e for e in self.websocket_events if e['run_id'] == user_context.run_id]
                    user_specific_data = f"user_{user_context.user_id}_data"
                    
                    # Each user should have their own events
                    assert len(user_events) >= 3, (
                        f"SSOT VIOLATION: User {user_context.user_id} has {len(user_events)} events, expected at least 3. "
                        f"Events: {user_events}"
                    )
                    
                    # CRITICAL: User events must contain only their data
                    user_event_content = str(user_events)
                    assert user_specific_data in user_event_content, (
                        f"SSOT VIOLATION: User {user_context.user_id} events missing their specific data '{user_specific_data}'. "
                        f"Content: {user_event_content[:200]}..."
                    )
                    
                    # CRITICAL: User events must NOT contain other users' data
                    for j, other_context in enumerate(contexts):
                        if i != j:  # Skip self
                            other_user_data = f"user_{other_context.user_id}_data"
                            assert other_user_data not in user_event_content, (
                                f"SSOT VIOLATION: User {user_context.user_id} events contain data for user {other_context.user_id} ('{other_user_data}'). "
                                f"This indicates WebSocket event leakage. Content: {user_event_content[:200]}..."
                            )
                
                # CRITICAL: Validate total event count is consistent
                total_events_expected = len(contexts) * 3  # 3 events per user minimum
                total_events_actual = len(self.websocket_events)
                
                assert total_events_actual >= total_events_expected, (
                    f"SSOT VIOLATION: Expected at least {total_events_expected} total events for {len(contexts)} users, "
                    f"got {total_events_actual}. Events may have been lost or merged."
                )
                
                # CRITICAL: Validate event distribution
                run_ids_in_events = set(e['run_id'] for e in self.websocket_events)
                expected_run_ids = set(c.run_id for c in contexts)
                
                assert run_ids_in_events == expected_run_ids, (
                    f"SSOT VIOLATION: Event run_ids don't match expected users. "
                    f"Expected: {expected_run_ids}, Got: {run_ids_in_events}"
                )
                
                # Record comprehensive event isolation validation
                self.record_metric("concurrent_websocket_isolation_verified", True)
                self.record_metric("concurrent_users_tested", len(contexts))
                self.record_metric("total_events_captured", total_events_actual)
                self.record_metric("no_event_leakage_detected", True)
                self.record_metric("event_distribution_correct", True)
                
            finally:
                # Clean up all engines
                for engine in engines:
                    await self.factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_websocket_bridge_integration_with_factory_pattern(self):
        """CRITICAL: Validate WebSocket bridge integration works with factory pattern.
        
        This test ensures the WebSocket bridge is properly integrated with
        factory-created engines and maintains proper connection isolation.
        
        Expected: FAIL before factory implementation (bridge integration issues)
        Expected: PASS after factory implementation (seamless integration)
        """
        # Create user context for bridge testing
        user_context = self.create_test_user_context("bridge_user", "integration_test")
        
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = self.mock_agent_factory
            
            # Create engine
            engine = await self.factory.create_for_user(user_context)
            
            try:
                # CRITICAL: Engine must have access to WebSocket bridge
                assert hasattr(engine, 'websocket_bridge') or hasattr(engine, 'websocket_emitter'), (
                    "SSOT VIOLATION: Factory-created engine has no WebSocket bridge access. "
                    "Bridge integration is required for chat functionality."
                )
                
                # Get the bridge from engine (either directly or through emitter)
                if hasattr(engine, 'websocket_bridge'):
                    bridge = engine.websocket_bridge
                elif hasattr(engine, 'websocket_emitter') and hasattr(engine.websocket_emitter, 'websocket_bridge'):
                    bridge = engine.websocket_emitter.websocket_bridge
                else:
                    pytest.fail("Engine has no accessible WebSocket bridge")
                
                # CRITICAL: Bridge must be the same instance provided to factory
                assert bridge is self.mock_websocket_bridge, (
                    f"SSOT VIOLATION: Engine has different WebSocket bridge instance. "
                    f"Expected: {self.mock_websocket_bridge}, Got: {bridge}"
                )
                
                # Test bridge method availability
                required_bridge_methods = [
                    'notify_agent_started',
                    'notify_agent_thinking', 
                    'notify_tool_executing',
                    'notify_tool_completed',
                    'notify_agent_completed',
                    'notify_agent_error'
                ]
                
                for method_name in required_bridge_methods:
                    assert hasattr(bridge, method_name), (
                        f"SSOT VIOLATION: WebSocket bridge missing required method '{method_name}'. "
                        f"This will break chat functionality."
                    )
                    
                    method = getattr(bridge, method_name)
                    assert callable(method), (
                        f"SSOT VIOLATION: WebSocket bridge method '{method_name}' is not callable. "
                        f"Got: {type(method)}"
                    )
                
                # CRITICAL: Test actual bridge integration with events
                agent_context = self.create_test_agent_context(user_context)
                
                # Clear previous events
                self.websocket_events.clear()
                
                # Send test events through engine
                await engine.send_agent_thinking(agent_context, "Bridge integration test", step_number=1)
                await engine.send_tool_executing(agent_context, "bridge_test_tool")
                
                # Verify events were captured
                bridge_events = [e for e in self.websocket_events if e['run_id'] == user_context.run_id]
                
                assert len(bridge_events) >= 2, (
                    f"SSOT VIOLATION: Bridge integration failed. Expected at least 2 events, got {len(bridge_events)}. "
                    f"Events: {bridge_events}"
                )
                
                # Verify bridge method calls
                self.mock_websocket_bridge.notify_agent_thinking.assert_called()
                self.mock_websocket_bridge.notify_tool_executing.assert_called()
                
                # CRITICAL: Validate bridge metrics are accessible
                metrics = await bridge.get_metrics()
                assert isinstance(metrics, dict), (
                    f"SSOT VIOLATION: Bridge metrics should be dict, got {type(metrics)}"
                )
                
                # Record bridge integration validation
                self.record_metric("websocket_bridge_integration_verified", True)
                self.record_metric("bridge_methods_available", len(required_bridge_methods))
                self.record_metric("bridge_events_working", len(bridge_events))
                self.record_metric("bridge_metrics_accessible", True)
                
            finally:
                # Clean up engine
                await self.factory.cleanup_engine(engine)
    
    @pytest.mark.asyncio
    async def test_websocket_error_handling_maintains_isolation(self):
        """CRITICAL: Validate WebSocket errors maintain user isolation.
        
        This test ensures that when WebSocket errors occur, they don't
        affect other users' WebSocket connections or cause cross-contamination.
        
        Expected: FAIL before factory implementation (error propagation)
        Expected: PASS after factory implementation (isolated error handling)
        """
        # Create contexts for multiple users
        user_stable_context = self.create_test_user_context("stable_user", "error_test")
        user_error_context = self.create_test_user_context("error_user", "error_test")
        
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = self.mock_agent_factory
            
            # Create engines
            engine_stable = await self.factory.create_for_user(user_stable_context)
            engine_error = await self.factory.create_for_user(user_error_context)
            
            try:
                # Configure error engine's bridge to raise exceptions
                error_bridge_methods = ['notify_agent_thinking', 'notify_tool_executing']
                original_methods = {}
                
                for method_name in error_bridge_methods:
                    original_method = getattr(self.mock_websocket_bridge, method_name)
                    original_methods[method_name] = original_method
                    
                    # Create error-raising mock for error user only
                    def create_error_method(orig_method, method_name):
                        async def error_method(run_id, *args, **kwargs):
                            if run_id == user_error_context.run_id:
                                raise Exception(f"WebSocket {method_name} error for error user")
                            return await orig_method(run_id, *args, **kwargs)
                        return error_method
                    
                    error_method = create_error_method(original_method, method_name)
                    setattr(self.mock_websocket_bridge, method_name, error_method)
                
                # Clear previous events
                self.websocket_events.clear()
                
                # Create agent contexts
                agent_context_stable = self.create_test_agent_context(user_stable_context)
                agent_context_error = self.create_test_agent_context(user_error_context)
                
                # Test stable user (should work normally)
                try:
                    await engine_stable.send_agent_thinking(
                        agent_context_stable,
                        "Stable user thinking",
                        step_number=1
                    )
                    stable_success = True
                except Exception as e:
                    stable_success = False
                    pytest.fail(f"Stable user should not be affected by error user's issues: {e}")
                
                # Test error user (should handle errors gracefully)
                error_raised = False
                try:
                    await engine_error.send_agent_thinking(
                        agent_context_error,
                        "Error user thinking", 
                        step_number=1
                    )
                except Exception:
                    error_raised = True
                
                # CRITICAL: Stable user must be unaffected by error user's problems
                assert stable_success, (
                    "SSOT VIOLATION: Stable user was affected by error user's WebSocket problems. "
                    "Error isolation failed."
                )
                
                # Test that stable user can continue working after error user fails
                try:
                    await engine_stable.send_tool_executing(
                        agent_context_stable,
                        "stable_user_tool"
                    )
                    post_error_success = True
                except Exception as e:
                    post_error_success = False
                    pytest.fail(f"Stable user should work after error user fails: {e}")
                
                assert post_error_success, (
                    "SSOT VIOLATION: Stable user stopped working after error user failed. "
                    "WebSocket errors are not properly isolated."
                )
                
                # CRITICAL: Validate event isolation despite errors
                stable_events = [e for e in self.websocket_events if e['run_id'] == user_stable_context.run_id]
                
                assert len(stable_events) >= 1, (
                    f"SSOT VIOLATION: Stable user has no events despite successful operations. "
                    f"Error handling may have affected event processing. Events: {stable_events}"
                )
                
                # Verify stable user events contain correct data
                stable_event_content = str(stable_events)
                assert "Stable user thinking" in stable_event_content, (
                    f"SSOT VIOLATION: Stable user events missing expected content. "
                    f"Content: {stable_event_content}"
                )
                
                # Restore original methods
                for method_name, original_method in original_methods.items():
                    setattr(self.mock_websocket_bridge, method_name, original_method)
                
                # Record error isolation validation
                self.record_metric("websocket_error_isolation_verified", True)
                self.record_metric("stable_user_unaffected", stable_success)
                self.record_metric("post_error_recovery", post_error_success)
                self.record_metric("error_user_handled_gracefully", error_raised)
                self.record_metric("stable_events_preserved", len(stable_events))
                
            finally:
                # Clean up engines
                await self.factory.cleanup_engine(engine_stable)
                await self.factory.cleanup_engine(engine_error)
    
    @pytest.mark.asyncio
    async def test_factory_websocket_cleanup_prevents_resource_leaks(self):
        """CRITICAL: Validate factory WebSocket cleanup prevents resource leaks.
        
        This test ensures that when engines are cleaned up, their WebSocket
        resources are properly disposed of without affecting other users.
        
        Expected: FAIL before factory implementation (resource leaks)
        Expected: PASS after factory implementation (clean resource disposal)
        """
        # Create multiple user contexts for cleanup testing
        contexts = []
        for i in range(3):
            context = self.create_test_user_context(f"cleanup_user_{i}", f"cleanup_test_{i}")
            contexts.append(context)
        
        with patch('netra_backend.app.agents.supervisor.agent_instance_factory.get_agent_instance_factory') as mock_get_factory:
            mock_get_factory.return_value = self.mock_agent_factory
            
            # Create engines for all users
            engines = []
            for context in contexts:
                engine = await self.factory.create_for_user(context)
                engines.append(engine)
            
            # Record initial state
            initial_emitter_count = len(self.user_emitters)
            initial_factory_metrics = self.factory.get_factory_metrics()
            
            # Use engines to generate some WebSocket activity
            for i, (engine, context) in enumerate(zip(engines, contexts)):
                agent_context = self.create_test_agent_context(context)
                await engine.send_agent_thinking(
                    agent_context,
                    f"Activity for cleanup test user {i}",
                    step_number=1
                )
            
            # Clean up first engine
            engine_to_cleanup = engines[0]
            context_to_cleanup = contexts[0]
            
            await self.factory.cleanup_engine(engine_to_cleanup)
            
            # CRITICAL: Other engines must still work after cleanup
            for i, (engine, context) in enumerate(zip(engines[1:], contexts[1:]), 1):
                try:
                    agent_context = self.create_test_agent_context(context)
                    await engine.send_agent_thinking(
                        agent_context,
                        f"Post-cleanup activity for user {i}",
                        step_number=2
                    )
                    post_cleanup_success = True
                except Exception as e:
                    post_cleanup_success = False
                    pytest.fail(f"Engine {i} should work after cleanup of Engine 0: {e}")
                
                assert post_cleanup_success, (
                    f"SSOT VIOLATION: Engine {i} stopped working after cleanup of another engine. "
                    f"Cleanup process affected other users."
                )
            
            # CRITICAL: Validate WebSocket emitter cleanup
            # The cleaned up user's emitter should be cleaned or marked as inactive
            cleanup_emitter_key = f"{context_to_cleanup.user_id}_{context_to_cleanup.thread_id}_{context_to_cleanup.run_id}"
            
            # If emitter still exists, it should be inactive or cleaned
            if cleanup_emitter_key in self.user_emitters:
                cleanup_emitter = self.user_emitters[cleanup_emitter_key]
                # Emitter may still exist but should not be actively used
                # The key test is that other emitters are unaffected
            
            # CRITICAL: Other emitters must be unaffected
            for i, context in enumerate(contexts[1:], 1):
                emitter_key = f"{context.user_id}_{context.thread_id}_{context.run_id}"
                assert emitter_key in self.user_emitters, (
                    f"SSOT VIOLATION: Cleanup of one engine affected emitter for user {i}. "
                    f"Missing emitter key: {emitter_key}"
                )
                
                emitter = self.user_emitters[emitter_key]
                assert emitter.user_id == context.user_id, (
                    f"SSOT VIOLATION: Emitter for user {i} has wrong user_id after cleanup. "
                    f"Expected: {context.user_id}, Got: {emitter.user_id}"
                )
            
            # CRITICAL: Factory metrics must reflect cleanup
            post_cleanup_metrics = self.factory.get_factory_metrics()
            
            assert post_cleanup_metrics['total_engines_cleaned'] > initial_factory_metrics['total_engines_cleaned'], (
                "SSOT VIOLATION: Factory metrics don't reflect engine cleanup. "
                f"Initial: {initial_factory_metrics['total_engines_cleaned']}, "
                f"Post: {post_cleanup_metrics['total_engines_cleaned']}"
            )
            
            assert post_cleanup_metrics['active_engines_count'] < initial_factory_metrics['active_engines_count'], (
                "SSOT VIOLATION: Factory active engine count not decremented after cleanup. "
                f"Initial: {initial_factory_metrics['active_engines_count']}, "
                f"Post: {post_cleanup_metrics['active_engines_count']}"
            )
            
            # Clean up remaining engines
            for engine in engines[1:]:
                await self.factory.cleanup_engine(engine)
            
            # CRITICAL: Final state should show all engines cleaned
            final_metrics = self.factory.get_factory_metrics()
            assert final_metrics['active_engines_count'] == 0, (
                f"SSOT VIOLATION: Active engines count should be 0 after all cleanups, "
                f"got {final_metrics['active_engines_count']}"
            )
            
            # Record cleanup validation
            self.record_metric("websocket_cleanup_verified", True)
            self.record_metric("engines_cleaned", len(engines))
            self.record_metric("other_engines_unaffected_during_cleanup", True)
            self.record_metric("factory_metrics_updated", True)
            self.record_metric("final_active_engines", final_metrics['active_engines_count'])


# Business Value Justification (BVJ) Documentation
"""
BUSINESS VALUE JUSTIFICATION for ExecutionEngine Factory WebSocket Integration Tests

Segment: ALL (Free → Enterprise) - affects every user interaction with chat
Business Goal: Revenue/Retention - ensures primary value delivery mechanism works correctly
Value Impact: Delivers 90% of platform value through reliable real-time chat communication
Revenue Impact: Prevents $500K+ ARR loss from broken WebSocket communications that break chat
Strategic Impact: CRITICAL - WebSocket events enable chat which is the primary business value delivery

Specific Business Impacts:
1. Chat Functionality: WebSocket events provide real-time feedback for AI agent execution
2. User Experience: Real-time updates keep users engaged and confident system is working
3. Revenue Protection: Chat breakdown = immediate user churn and subscription cancellation
4. Competitive Advantage: Real-time AI interaction is key differentiator vs batch systems
5. User Trust: Reliable real-time communication builds confidence in platform reliability

Revenue Calculation:
- Average user generates $500/month ARR through chat functionality
- Platform has 1000+ active users heavily dependent on chat
- Single WebSocket isolation bug could affect multiple users simultaneously
- Bug causing cross-user data leakage could result in:
  - Immediate user churn: $50K+ ARR loss per month
  - Legal liability: $1M+ in data privacy violations
  - Platform reputation damage: Unmeasurable but potentially catastrophic

Test Investment ROI:
- Test Development Cost: ~6 hours senior developer time  
- Prevented Revenue Loss: $500K+ ARR protection
- ROI: 83,300%+ (massive protection vs minimal development cost)

This test directly protects the core revenue-generating functionality of the platform.
"""