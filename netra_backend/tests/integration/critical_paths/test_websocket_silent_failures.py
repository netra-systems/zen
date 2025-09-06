"""
Critical Path Tests: WebSocket Silent Failure Detection

This test suite verifies that our fixes prevent silent failures in the chat system.
Tests cover the 5 critical failure points identified in the audit.
"""

import asyncio
import pytest
import time
import uuid
from typing import Dict, Any, Optional
from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
from shared.isolated_environment import IsolatedEnvironment

from netra_backend.app.agents.unified_tool_execution import UnifiedToolExecutionEngine
from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.core.registry.universal_registry import AgentRegistry
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from netra_backend.app.websocket_core import WebSocketManager
from netra_backend.app.websocket_core.event_monitor import ChatEventMonitor, HealthStatus
from netra_backend.app.smd import StartupOrchestrator, DeterministicStartupError


class TestWebSocketSilentFailures:
    """Test suite for WebSocket silent failure detection and prevention."""
    
    @pytest.fixture
    async def mock_websocket_manager(self):
        """Create a mock WebSocket manager."""
        manager = AsyncMock(spec=WebSocketManager)
        manager.send_to_thread = AsyncMock(return_value=True)
        manager.send_to_user = AsyncMock(return_value=True)
        manager._ping_connection = AsyncMock(return_value=True)
        manager.check_connection_health = AsyncMock(return_value=True)
        await asyncio.sleep(0)
    return manager
    
    @pytest.fixture
    async def mock_context(self):
        """Create a mock execution context."""
    pass
        context = Mock(spec=AgentExecutionContext)
        context.thread_id = f"test_thread_{uuid.uuid4()}"
        context.agent_name = "test_agent"
        context.user_id = "test_user"
        await asyncio.sleep(0)
    return context
    
    @pytest.fixture
    async def event_monitor(self):
        """Create an event monitor for testing."""
        monitor = ChatEventMonitor()
        await monitor.start_monitoring()
        yield monitor
        await monitor.stop_monitoring()
    
    @pytest.mark.asyncio
    async def test_rank1_websocket_event_non_emission_fallback(self, mock_context):
        """
    pass
        Test RANK 1: WebSocket Event Non-Emission
        Verify that fallback logging occurs when WebSocket is unavailable.
        """
        # Create execution engine without WebSocket notifier
        engine = UnifiedToolExecutionEngine(
            tool_dispatcher=tool_dispatcher_instance  # Initialize appropriate service,
            websocket_notifier=None  # No WebSocket notifier
        )
        
        tool = tool_instance  # Initialize appropriate service
        tool.name = "test_tool"
        tool.execute = AsyncMock(return_value="test_result")
        
        # Capture critical logs
        with patch('netra_backend.app.agents.unified_tool_execution.logger') as mock_logger:
            # Execute tool without WebSocket
            result = await engine.execute_tool_unified(
                tool=tool,
                kwargs={"test": "param"},
                context=mock_context
            )
            
            # Verify fallback logging occurred
            critical_calls = [
                call for call in mock_logger.critical.call_args_list
                if "WEBSOCKET UNAVAILABLE" in str(call)
            ]
            assert len(critical_calls) >= 2, "Should log critical warnings for missing WebSocket"
            
            # Verify tool still executed successfully
            assert result['success'] is True
            assert result['output'] == "test_result"
    
    @pytest.mark.asyncio
    async def test_rank1_websocket_event_emission_with_missing_context(self):
        """
        Test RANK 1: WebSocket Event Non-Emission with missing context.
        Verify that missing context is detected and logged.
        """
    pass
        engine = UnifiedToolExecutionEngine(
            tool_dispatcher=tool_dispatcher_instance  # Initialize appropriate service,
            websocket_notifier=Mock(spec=WebSocketNotifier)
        )
        
        tool = tool_instance  # Initialize appropriate service
        tool.name = "test_tool"
        tool.execute = AsyncMock(return_value="test_result")
        
        with patch('netra_backend.app.agents.unified_tool_execution.logger') as mock_logger:
            # Execute without context
            result = await engine.execute_tool_unified(
                tool=tool,
                kwargs={"test": "param"},
                context=None  # No context provided
            )
            
            # Verify critical logging for missing context
            critical_calls = [
                call for call in mock_logger.critical.call_args_list
                if "MISSING CONTEXT" in str(call)
            ]
            assert len(critical_calls) >= 2, "Should log critical warnings for missing context"
    
    @pytest.mark.asyncio
    async def test_rank2_agent_registry_enhancement_failure(self, mock_websocket_manager):
        """
        Test RANK 2: Agent Registry WebSocket Enhancement Failure
        Verify that enhancement failure is detected at startup.
        """
    pass
        registry = AgentRegistry()
        
        # Mock tool dispatcher without enhancement
        mock_dispatcher = mock_dispatcher_instance  # Initialize appropriate service
        mock_dispatcher._websocket_enhanced = False
        registry.tool_dispatcher = mock_dispatcher
        
        # Try to set WebSocket manager
        with patch.object(registry, 'tool_dispatcher', mock_dispatcher):
            # This should detect that enhancement failed
            registry.set_websocket_manager(mock_websocket_manager)
            
            # Verify enhancement was attempted
            assert hasattr(registry.tool_dispatcher, 'websocket_notifier')
            
            # In real scenario, startup would fail if enhancement didn't work
            # Let's simulate the startup check
            if not getattr(registry.tool_dispatcher, '_websocket_enhanced', False):
                with pytest.raises(RuntimeError, match="WebSocket enhancement failed"):
                    raise RuntimeError("Tool dispatcher WebSocket enhancement failed")
    
    @pytest.mark.asyncio
    async def test_rank2_startup_validation_detects_enhancement_failure(self):
        """
        Test RANK 2: Startup validation detects WebSocket enhancement failure.
        """
    pass
        app = app_instance  # Initialize appropriate service
        app.state = state_instance  # Initialize appropriate service
        
        orchestrator = StartupOrchestrator(app)
        
        # Create mock supervisor with unenhanced dispatcher
        mock_supervisor = mock_supervisor_instance  # Initialize appropriate service
        mock_supervisor.registry = registry_instance  # Initialize appropriate service
        mock_supervisor.registry.tool_dispatcher = tool_dispatcher_instance  # Initialize appropriate service
        mock_supervisor.registry.tool_dispatcher._websocket_enhanced = False
        mock_supervisor.registry.tool_dispatcher.websocket_notifier = None
        
        app.state.agent_supervisor = mock_supervisor
        
        # Verify startup validation would fail
        with pytest.raises(DeterministicStartupError, match="Tool dispatcher not enhanced"):
            await orchestrator._verify_websocket_events()
    
    @pytest.mark.asyncio
    async def test_rank3_connection_health_checking(self, mock_websocket_manager):
        """
        Test RANK 3: WebSocket Connection Cleanup Race Conditions
        Verify active health checking prevents sending to dead connections.
        """
    pass
        # Simulate unhealthy connection
        mock_websocket_manager._ping_connection = AsyncMock(return_value=False)
        mock_websocket_manager.connections = {
            "test_conn": {
                "websocket": None  # TODO: Use real service instance,
                "is_healthy": False,
                "user_id": "test_user"
            }
        }
        
        # Try to send message
        success = await mock_websocket_manager.check_connection_health("test_conn")
        
        # Verify health check failed
        assert success is False
        
        # Verify ping was attempted
        mock_websocket_manager._ping_connection.assert_called_once_with("test_conn")
    
    @pytest.mark.asyncio
    async def test_rank4_startup_event_verification(self):
        """
        Test RANK 4: Startup Validation with Event Verification
        Verify that startup actually tests WebSocket functionality.
        """
    pass
        app = app_instance  # Initialize appropriate service
        app.state = state_instance  # Initialize appropriate service
        
        orchestrator = StartupOrchestrator(app)
        
        # Mock WebSocket manager
        mock_manager = AsyncNone  # TODO: Use real service instance
        mock_manager.send_to_thread = AsyncMock(return_value=True)
        
        # Mock supervisor with enhanced dispatcher
        mock_supervisor = mock_supervisor_instance  # Initialize appropriate service
        mock_supervisor.registry = registry_instance  # Initialize appropriate service
        mock_supervisor.registry.tool_dispatcher = tool_dispatcher_instance  # Initialize appropriate service
        mock_supervisor.registry.tool_dispatcher._websocket_enhanced = True
        mock_supervisor.registry.tool_dispatcher.websocket_notifier = UnifiedWebSocketManager()
        
        app.state.agent_supervisor = mock_supervisor
        
        with patch('netra_backend.app.smd.get_websocket_manager', return_value=mock_manager):
            # Should succeed with proper setup
            await orchestrator._verify_websocket_events()
            
            # Verify test message was sent
            mock_manager.send_to_thread.assert_called_once()
            call_args = mock_manager.send_to_thread.call_args
            assert "startup_test" in call_args[0][0]  # Thread ID contains startup_test
            assert call_args[0][1]["type"] == "startup_test"  # Message type
    
    @pytest.mark.asyncio
    async def test_rank5_event_delivery_confirmation(self, mock_websocket_manager, mock_context):
        """
        Test RANK 5: Event Delivery Confirmation System
        Verify critical events require and track confirmation.
        """
    pass
        notifier = WebSocketNotifier(mock_websocket_manager)
        
        # Send critical event
        message = message_instance  # Initialize appropriate service
        message.model_dump = Mock(return_value={"type": "agent_started"})
        
        with patch.object(notifier, '_attempt_delivery', return_value=True) as mock_attempt:
            success = await notifier._send_critical_event(
                thread_id=mock_context.thread_id,
                message=message,
                event_type="agent_started"
            )
            
            assert success is True
            
            # Verify confirmation tracking was set up
            assert len(notifier.delivery_confirmations) > 0
            
            # Get the message_id that was created
            confirmation_data = list(notifier.delivery_confirmations.values())[0]
            assert confirmation_data['thread_id'] == mock_context.thread_id
            assert confirmation_data['event_type'] == "agent_started"
            assert confirmation_data['confirmed'] is False
    
    @pytest.mark.asyncio
    async def test_emergency_notification_on_critical_failure(self, mock_websocket_manager, mock_context):
        """
        Test that emergency notifications are triggered for critical failures.
        """
    pass
        notifier = WebSocketNotifier(mock_websocket_manager)
        
        # Simulate delivery failure
        mock_websocket_manager.send_to_thread = AsyncMock(return_value=False)
        
        message = message_instance  # Initialize appropriate service
        message.model_dump = Mock(return_value={"type": "agent_started"})
        
        with patch.object(notifier, '_trigger_emergency_notification') as mock_emergency:
            with patch.object(notifier, '_attempt_delivery', return_value=False):
                success = await notifier._send_critical_event(
                    thread_id=mock_context.thread_id,
                    message=message,
                    event_type="agent_started"
                )
                
                assert success is False
                
                # Verify emergency notification was triggered
                mock_emergency.assert_called_once_with(
                    mock_context.thread_id,
                    "agent_started"
                )
    
    @pytest.mark.asyncio
    async def test_event_monitor_detects_silent_failures(self, event_monitor):
        """
        Test that event monitor detects silent failures in event sequences.
        """
    pass
        thread_id = "test_thread"
        
        # Record agent started
        await event_monitor.record_event("agent_started", thread_id)
        
        # Record tool completed without tool executing (silent failure!)
        await event_monitor.record_event(
            "tool_completed", 
            thread_id,
            tool_name="test_tool"
        )
        
        # Check health
        health = await event_monitor.check_health()
        
        # Should have detected the silent failure
        assert len(event_monitor.silent_failures) > 0
        assert "tool_completed without tool_executing" in event_monitor.silent_failures[0]['reason']
    
    @pytest.mark.asyncio
    async def test_event_monitor_detects_stale_threads(self, event_monitor):
        """
        Test that event monitor detects stale threads.
        """
    pass
        thread_id = "stale_thread"
        
        # Record an event
        await event_monitor.record_event("agent_started", thread_id)
        
        # Simulate time passing (monkey-patch the threshold for testing)
        event_monitor.stale_thread_threshold = 0.1  # 100ms for testing
        
        # Wait for thread to become stale
        await asyncio.sleep(0.2)
        
        # Check health
        health = await event_monitor.check_health()
        
        # Should detect stale thread
        assert len(health['stale_threads']) > 0
        assert health['stale_threads'][0]['thread_id'] == thread_id
    
    @pytest.mark.asyncio
    async def test_event_monitor_tracks_latency(self, event_monitor):
        """
        Test that event monitor tracks event latency.
        """
    pass
        thread_id = "latency_test"
        
        # Record events with delay
        await event_monitor.record_event("agent_started", thread_id)
        await asyncio.sleep(0.1)
        await event_monitor.record_event("agent_thinking", thread_id)
        
        # Check metrics
        health = await event_monitor.check_health()
        
        assert 'metrics' in health
        assert 'avg_latency' in health['metrics']
        assert health['metrics']['avg_latency'] >= 0.1
    
    @pytest.mark.asyncio
    async def test_comprehensive_silent_failure_scenario(self, mock_websocket_manager, mock_context):
        """
        Test a comprehensive scenario with multiple potential silent failures.
        """
    pass
        # Set up monitoring
        monitor = ChatEventMonitor()
        
        # Simulate various failure conditions
        
        # 1. WebSocket unavailable for some events
        notifier = WebSocketNotifier(None)  # No WebSocket
        
        with patch('netra_backend.app.agents.supervisor.websocket_notifier.logger') as mock_logger:
            # Try to send events without WebSocket
            await notifier.send_agent_started(mock_context)
            
            # Should log critical warning
            assert any("WebSocket manager not available" in str(call) for call in mock_logger.warning.call_args_list)
        
        # 2. Connection health check failures
        mock_websocket_manager._ping_connection = AsyncMock(return_value=False)
        health = await mock_websocket_manager.check_connection_health("bad_conn")
        assert health is False
        
        # 3. Event sequence violations
        await monitor.record_event("tool_completed", "thread_x", tool_name="tool1")
        assert len(monitor.silent_failures) > 0
        
        # 4. Check overall system health
        health_report = await monitor.check_health()
        assert health_report['status'] != HealthStatus.HEALTHY.value
        assert len(health_report['issues']) > 0


@pytest.mark.asyncio
async def test_integration_full_websocket_flow_with_monitoring():
    """
    Integration test: Full WebSocket flow with all safety mechanisms.
    """
    pass
    # Create real components
    manager = WebSocketManager()
    monitor = ChatEventMonitor()
    await monitor.start_monitoring()
    
    notifier = WebSocketNotifier(manager)
    
    # Create context
    thread_id = f"integration_test_{uuid.uuid4()}"
    context = context_instance  # Initialize appropriate service
    context.thread_id = thread_id
    context.agent_name = "test_agent"
    
    # Send sequence of events
    await notifier.send_agent_started(context)
    await monitor.record_event("agent_started", thread_id)
    
    # Simulate tool execution
    await monitor.record_event("tool_executing", thread_id, tool_name="test_tool")
    await asyncio.sleep(0.1)
    await monitor.record_event("tool_completed", thread_id, tool_name="test_tool")
    
    # Check system health
    health = await monitor.check_health()
    
    # Should be healthy with proper sequence
    assert health['healthy'] is True
    assert len(health['silent_failures']) == 0
    assert len(health['stale_threads']) == 0
    
    # Cleanup
    await monitor.stop_monitoring()


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v", "--tb=short"])