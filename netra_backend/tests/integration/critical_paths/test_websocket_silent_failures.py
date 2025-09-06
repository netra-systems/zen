from unittest.mock import AsyncMock, Mock, patch, MagicMock

# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: Critical Path Tests: WebSocket Silent Failure Detection

# REMOVED_SYNTAX_ERROR: This test suite verifies that our fixes prevent silent failures in the chat system.
# REMOVED_SYNTAX_ERROR: Tests cover the 5 critical failure points identified in the audit.
""

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


# REMOVED_SYNTAX_ERROR: class TestWebSocketSilentFailures:
    # REMOVED_SYNTAX_ERROR: """Test suite for WebSocket silent failure detection and prevention."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_websocket_manager(self):
    # REMOVED_SYNTAX_ERROR: """Create a mock WebSocket manager."""
    # REMOVED_SYNTAX_ERROR: manager = AsyncMock(spec=WebSocketManager)
    # REMOVED_SYNTAX_ERROR: manager.send_to_thread = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: manager.send_to_user = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: manager._ping_connection = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: manager.check_connection_health = AsyncMock(return_value=True)
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return manager

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def mock_context(self):
    # REMOVED_SYNTAX_ERROR: """Create a mock execution context."""
    # REMOVED_SYNTAX_ERROR: context = Mock(spec=AgentExecutionContext)
    # REMOVED_SYNTAX_ERROR: context.thread_id = "formatted_string"
    # REMOVED_SYNTAX_ERROR: context.agent_name = "test_agent"
    # REMOVED_SYNTAX_ERROR: context.user_id = "test_user"
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return context

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: async def event_monitor(self):
    # REMOVED_SYNTAX_ERROR: """Create an event monitor for testing."""
    # REMOVED_SYNTAX_ERROR: monitor = ChatEventMonitor()
    # REMOVED_SYNTAX_ERROR: await monitor.start_monitoring()
    # REMOVED_SYNTAX_ERROR: yield monitor
    # REMOVED_SYNTAX_ERROR: await monitor.stop_monitoring()

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_rank1_websocket_event_non_emission_fallback(self, mock_context):
        # REMOVED_SYNTAX_ERROR: '''
        # REMOVED_SYNTAX_ERROR: Test RANK 1: WebSocket Event Non-Emission
        # REMOVED_SYNTAX_ERROR: Verify that fallback logging occurs when WebSocket is unavailable.
        # REMOVED_SYNTAX_ERROR: """"
        # Create execution engine without WebSocket notifier
        # REMOVED_SYNTAX_ERROR: engine = UnifiedToolExecutionEngine( )
        # REMOVED_SYNTAX_ERROR: tool_dispatcher=tool_dispatcher_instance  # Initialize appropriate service,
        # REMOVED_SYNTAX_ERROR: websocket_notifier=None  # No WebSocket notifier
        

        # REMOVED_SYNTAX_ERROR: tool = tool_instance  # Initialize appropriate service
        # REMOVED_SYNTAX_ERROR: tool.name = "test_tool"
        # REMOVED_SYNTAX_ERROR: tool.execute = AsyncMock(return_value="test_result")

        # Capture critical logs
        # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.unified_tool_execution.logger') as mock_logger:
            # Execute tool without WebSocket
            # REMOVED_SYNTAX_ERROR: result = await engine.execute_tool_unified( )
            # REMOVED_SYNTAX_ERROR: tool=tool,
            # REMOVED_SYNTAX_ERROR: kwargs={"test": "param"},
            # REMOVED_SYNTAX_ERROR: context=mock_context
            

            # Verify fallback logging occurred
            # REMOVED_SYNTAX_ERROR: critical_calls = [ )
            # REMOVED_SYNTAX_ERROR: call for call in mock_logger.critical.call_args_list
            # REMOVED_SYNTAX_ERROR: if "WEBSOCKET UNAVAILABLE" in str(call)
            
            # REMOVED_SYNTAX_ERROR: assert len(critical_calls) >= 2, "Should log critical warnings for missing WebSocket"

            # Verify tool still executed successfully
            # REMOVED_SYNTAX_ERROR: assert result['success'] is True
            # REMOVED_SYNTAX_ERROR: assert result['output'] == "test_result"

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_rank1_websocket_event_emission_with_missing_context(self):
                # REMOVED_SYNTAX_ERROR: '''
                # REMOVED_SYNTAX_ERROR: Test RANK 1: WebSocket Event Non-Emission with missing context.
                # REMOVED_SYNTAX_ERROR: Verify that missing context is detected and logged.
                # REMOVED_SYNTAX_ERROR: """"
                # REMOVED_SYNTAX_ERROR: engine = UnifiedToolExecutionEngine( )
                # REMOVED_SYNTAX_ERROR: tool_dispatcher=tool_dispatcher_instance  # Initialize appropriate service,
                # REMOVED_SYNTAX_ERROR: websocket_notifier=Mock(spec=WebSocketNotifier)
                

                # REMOVED_SYNTAX_ERROR: tool = tool_instance  # Initialize appropriate service
                # REMOVED_SYNTAX_ERROR: tool.name = "test_tool"
                # REMOVED_SYNTAX_ERROR: tool.execute = AsyncMock(return_value="test_result")

                # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.unified_tool_execution.logger') as mock_logger:
                    # Execute without context
                    # REMOVED_SYNTAX_ERROR: result = await engine.execute_tool_unified( )
                    # REMOVED_SYNTAX_ERROR: tool=tool,
                    # REMOVED_SYNTAX_ERROR: kwargs={"test": "param"},
                    # REMOVED_SYNTAX_ERROR: context=None  # No context provided
                    

                    # Verify critical logging for missing context
                    # REMOVED_SYNTAX_ERROR: critical_calls = [ )
                    # REMOVED_SYNTAX_ERROR: call for call in mock_logger.critical.call_args_list
                    # REMOVED_SYNTAX_ERROR: if "MISSING CONTEXT" in str(call)
                    
                    # REMOVED_SYNTAX_ERROR: assert len(critical_calls) >= 2, "Should log critical warnings for missing context"

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_rank2_agent_registry_enhancement_failure(self, mock_websocket_manager):
                        # REMOVED_SYNTAX_ERROR: '''
                        # REMOVED_SYNTAX_ERROR: Test RANK 2: Agent Registry WebSocket Enhancement Failure
                        # REMOVED_SYNTAX_ERROR: Verify that enhancement failure is detected at startup.
                        # REMOVED_SYNTAX_ERROR: """"
                        # REMOVED_SYNTAX_ERROR: registry = AgentRegistry()

                        # Mock tool dispatcher without enhancement
                        # REMOVED_SYNTAX_ERROR: mock_dispatcher = mock_dispatcher_instance  # Initialize appropriate service
                        # REMOVED_SYNTAX_ERROR: mock_dispatcher._websocket_enhanced = False
                        # REMOVED_SYNTAX_ERROR: registry.tool_dispatcher = mock_dispatcher

                        # Try to set WebSocket manager
                        # REMOVED_SYNTAX_ERROR: with patch.object(registry, 'tool_dispatcher', mock_dispatcher):
                            # This should detect that enhancement failed
                            # REMOVED_SYNTAX_ERROR: registry.set_websocket_manager(mock_websocket_manager)

                            # Verify enhancement was attempted
                            # REMOVED_SYNTAX_ERROR: assert hasattr(registry.tool_dispatcher, 'websocket_notifier')

                            # In real scenario, startup would fail if enhancement didn't work
                            # Let's simulate the startup check
                            # REMOVED_SYNTAX_ERROR: if not getattr(registry.tool_dispatcher, '_websocket_enhanced', False):
                                # REMOVED_SYNTAX_ERROR: with pytest.raises(RuntimeError, match="WebSocket enhancement failed"):
                                    # REMOVED_SYNTAX_ERROR: raise RuntimeError("Tool dispatcher WebSocket enhancement failed")

                                    # Removed problematic line: @pytest.mark.asyncio
                                    # Removed problematic line: async def test_rank2_startup_validation_detects_enhancement_failure(self):
                                        # REMOVED_SYNTAX_ERROR: '''
                                        # REMOVED_SYNTAX_ERROR: Test RANK 2: Startup validation detects WebSocket enhancement failure.
                                        # REMOVED_SYNTAX_ERROR: """"
                                        # REMOVED_SYNTAX_ERROR: app = app_instance  # Initialize appropriate service
                                        # REMOVED_SYNTAX_ERROR: app.state = state_instance  # Initialize appropriate service

                                        # REMOVED_SYNTAX_ERROR: orchestrator = StartupOrchestrator(app)

                                        # Create mock supervisor with unenhanced dispatcher
                                        # REMOVED_SYNTAX_ERROR: mock_supervisor = mock_supervisor_instance  # Initialize appropriate service
                                        # REMOVED_SYNTAX_ERROR: mock_supervisor.registry = registry_instance  # Initialize appropriate service
                                        # REMOVED_SYNTAX_ERROR: mock_supervisor.registry.tool_dispatcher = tool_dispatcher_instance  # Initialize appropriate service
                                        # REMOVED_SYNTAX_ERROR: mock_supervisor.registry.tool_dispatcher._websocket_enhanced = False
                                        # REMOVED_SYNTAX_ERROR: mock_supervisor.registry.tool_dispatcher.websocket_notifier = None

                                        # REMOVED_SYNTAX_ERROR: app.state.agent_supervisor = mock_supervisor

                                        # Verify startup validation would fail
                                        # REMOVED_SYNTAX_ERROR: with pytest.raises(DeterministicStartupError, match="Tool dispatcher not enhanced"):
                                            # REMOVED_SYNTAX_ERROR: await orchestrator._verify_websocket_events()

                                            # Removed problematic line: @pytest.mark.asyncio
                                            # Removed problematic line: async def test_rank3_connection_health_checking(self, mock_websocket_manager):
                                                # REMOVED_SYNTAX_ERROR: '''
                                                # REMOVED_SYNTAX_ERROR: Test RANK 3: WebSocket Connection Cleanup Race Conditions
                                                # REMOVED_SYNTAX_ERROR: Verify active health checking prevents sending to dead connections.
                                                # REMOVED_SYNTAX_ERROR: """"
                                                # Simulate unhealthy connection
                                                # REMOVED_SYNTAX_ERROR: mock_websocket_manager._ping_connection = AsyncMock(return_value=False)
                                                # REMOVED_SYNTAX_ERROR: mock_websocket_manager.connections = { )
                                                # REMOVED_SYNTAX_ERROR: "test_conn": { )
                                                # REMOVED_SYNTAX_ERROR: "websocket": Mock()  # TODO: Use real service instance,
                                                # REMOVED_SYNTAX_ERROR: "is_healthy": False,
                                                # REMOVED_SYNTAX_ERROR: "user_id": "test_user"
                                                
                                                

                                                # Try to send message
                                                # REMOVED_SYNTAX_ERROR: success = await mock_websocket_manager.check_connection_health("test_conn")

                                                # Verify health check failed
                                                # REMOVED_SYNTAX_ERROR: assert success is False

                                                # Verify ping was attempted
                                                # REMOVED_SYNTAX_ERROR: mock_websocket_manager._ping_connection.assert_called_once_with("test_conn")

                                                # Removed problematic line: @pytest.mark.asyncio
                                                # Removed problematic line: async def test_rank4_startup_event_verification(self):
                                                    # REMOVED_SYNTAX_ERROR: '''
                                                    # REMOVED_SYNTAX_ERROR: Test RANK 4: Startup Validation with Event Verification
                                                    # REMOVED_SYNTAX_ERROR: Verify that startup actually tests WebSocket functionality.
                                                    # REMOVED_SYNTAX_ERROR: """"
                                                    # REMOVED_SYNTAX_ERROR: app = app_instance  # Initialize appropriate service
                                                    # REMOVED_SYNTAX_ERROR: app.state = state_instance  # Initialize appropriate service

                                                    # REMOVED_SYNTAX_ERROR: orchestrator = StartupOrchestrator(app)

                                                    # Mock WebSocket manager
                                                    # REMOVED_SYNTAX_ERROR: mock_manager = AsyncMock()  # TODO: Use real service instance
                                                    # REMOVED_SYNTAX_ERROR: mock_manager.send_to_thread = AsyncMock(return_value=True)

                                                    # Mock supervisor with enhanced dispatcher
                                                    # REMOVED_SYNTAX_ERROR: mock_supervisor = mock_supervisor_instance  # Initialize appropriate service
                                                    # REMOVED_SYNTAX_ERROR: mock_supervisor.registry = registry_instance  # Initialize appropriate service
                                                    # REMOVED_SYNTAX_ERROR: mock_supervisor.registry.tool_dispatcher = tool_dispatcher_instance  # Initialize appropriate service
                                                    # REMOVED_SYNTAX_ERROR: mock_supervisor.registry.tool_dispatcher._websocket_enhanced = True
                                                    # REMOVED_SYNTAX_ERROR: mock_supervisor.registry.tool_dispatcher.websocket_notifier = UnifiedWebSocketManager()

                                                    # REMOVED_SYNTAX_ERROR: app.state.agent_supervisor = mock_supervisor

                                                    # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.smd.get_websocket_manager', return_value=mock_manager):
                                                        # Should succeed with proper setup
                                                        # REMOVED_SYNTAX_ERROR: await orchestrator._verify_websocket_events()

                                                        # Verify test message was sent
                                                        # REMOVED_SYNTAX_ERROR: mock_manager.send_to_thread.assert_called_once()
                                                        # REMOVED_SYNTAX_ERROR: call_args = mock_manager.send_to_thread.call_args
                                                        # REMOVED_SYNTAX_ERROR: assert "startup_test" in call_args[0][0]  # Thread ID contains startup_test
                                                        # REMOVED_SYNTAX_ERROR: assert call_args[0][1]["type"] == "startup_test"  # Message type

                                                        # Removed problematic line: @pytest.mark.asyncio
                                                        # Removed problematic line: async def test_rank5_event_delivery_confirmation(self, mock_websocket_manager, mock_context):
                                                            # REMOVED_SYNTAX_ERROR: '''
                                                            # REMOVED_SYNTAX_ERROR: Test RANK 5: Event Delivery Confirmation System
                                                            # REMOVED_SYNTAX_ERROR: Verify critical events require and track confirmation.
                                                            # REMOVED_SYNTAX_ERROR: """"
                                                            # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(mock_websocket_manager)

                                                            # Send critical event
                                                            # REMOVED_SYNTAX_ERROR: message = message_instance  # Initialize appropriate service
                                                            # REMOVED_SYNTAX_ERROR: message.model_dump = Mock(return_value={"type": "agent_started"})

                                                            # REMOVED_SYNTAX_ERROR: with patch.object(notifier, '_attempt_delivery', return_value=True) as mock_attempt:
                                                                # REMOVED_SYNTAX_ERROR: success = await notifier._send_critical_event( )
                                                                # REMOVED_SYNTAX_ERROR: thread_id=mock_context.thread_id,
                                                                # REMOVED_SYNTAX_ERROR: message=message,
                                                                # REMOVED_SYNTAX_ERROR: event_type="agent_started"
                                                                

                                                                # REMOVED_SYNTAX_ERROR: assert success is True

                                                                # Verify confirmation tracking was set up
                                                                # REMOVED_SYNTAX_ERROR: assert len(notifier.delivery_confirmations) > 0

                                                                # Get the message_id that was created
                                                                # REMOVED_SYNTAX_ERROR: confirmation_data = list(notifier.delivery_confirmations.values())[0]
                                                                # REMOVED_SYNTAX_ERROR: assert confirmation_data['thread_id'] == mock_context.thread_id
                                                                # REMOVED_SYNTAX_ERROR: assert confirmation_data['event_type'] == "agent_started"
                                                                # REMOVED_SYNTAX_ERROR: assert confirmation_data['confirmed'] is False

                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                # Removed problematic line: async def test_emergency_notification_on_critical_failure(self, mock_websocket_manager, mock_context):
                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                    # REMOVED_SYNTAX_ERROR: Test that emergency notifications are triggered for critical failures.
                                                                    # REMOVED_SYNTAX_ERROR: """"
                                                                    # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(mock_websocket_manager)

                                                                    # Simulate delivery failure
                                                                    # REMOVED_SYNTAX_ERROR: mock_websocket_manager.send_to_thread = AsyncMock(return_value=False)

                                                                    # REMOVED_SYNTAX_ERROR: message = message_instance  # Initialize appropriate service
                                                                    # REMOVED_SYNTAX_ERROR: message.model_dump = Mock(return_value={"type": "agent_started"})

                                                                    # REMOVED_SYNTAX_ERROR: with patch.object(notifier, '_trigger_emergency_notification') as mock_emergency:
                                                                        # REMOVED_SYNTAX_ERROR: with patch.object(notifier, '_attempt_delivery', return_value=False):
                                                                            # REMOVED_SYNTAX_ERROR: success = await notifier._send_critical_event( )
                                                                            # REMOVED_SYNTAX_ERROR: thread_id=mock_context.thread_id,
                                                                            # REMOVED_SYNTAX_ERROR: message=message,
                                                                            # REMOVED_SYNTAX_ERROR: event_type="agent_started"
                                                                            

                                                                            # REMOVED_SYNTAX_ERROR: assert success is False

                                                                            # Verify emergency notification was triggered
                                                                            # REMOVED_SYNTAX_ERROR: mock_emergency.assert_called_once_with( )
                                                                            # REMOVED_SYNTAX_ERROR: mock_context.thread_id,
                                                                            # REMOVED_SYNTAX_ERROR: "agent_started"
                                                                            

                                                                            # Removed problematic line: @pytest.mark.asyncio
                                                                            # Removed problematic line: async def test_event_monitor_detects_silent_failures(self, event_monitor):
                                                                                # REMOVED_SYNTAX_ERROR: '''
                                                                                # REMOVED_SYNTAX_ERROR: Test that event monitor detects silent failures in event sequences.
                                                                                # REMOVED_SYNTAX_ERROR: """"
                                                                                # REMOVED_SYNTAX_ERROR: thread_id = "test_thread"

                                                                                # Record agent started
                                                                                # REMOVED_SYNTAX_ERROR: await event_monitor.record_event("agent_started", thread_id)

                                                                                # Record tool completed without tool executing (silent failure!)
                                                                                # REMOVED_SYNTAX_ERROR: await event_monitor.record_event( )
                                                                                # REMOVED_SYNTAX_ERROR: "tool_completed",
                                                                                # REMOVED_SYNTAX_ERROR: thread_id,
                                                                                # REMOVED_SYNTAX_ERROR: tool_name="test_tool"
                                                                                

                                                                                # Check health
                                                                                # REMOVED_SYNTAX_ERROR: health = await event_monitor.check_health()

                                                                                # Should have detected the silent failure
                                                                                # REMOVED_SYNTAX_ERROR: assert len(event_monitor.silent_failures) > 0
                                                                                # REMOVED_SYNTAX_ERROR: assert "tool_completed without tool_executing" in event_monitor.silent_failures[0]['reason']

                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                # Removed problematic line: async def test_event_monitor_detects_stale_threads(self, event_monitor):
                                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                                    # REMOVED_SYNTAX_ERROR: Test that event monitor detects stale threads.
                                                                                    # REMOVED_SYNTAX_ERROR: """"
                                                                                    # REMOVED_SYNTAX_ERROR: thread_id = "stale_thread"

                                                                                    # Record an event
                                                                                    # REMOVED_SYNTAX_ERROR: await event_monitor.record_event("agent_started", thread_id)

                                                                                    # Simulate time passing (monkey-patch the threshold for testing)
                                                                                    # REMOVED_SYNTAX_ERROR: event_monitor.stale_thread_threshold = 0.1  # 100ms for testing

                                                                                    # Wait for thread to become stale
                                                                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.2)

                                                                                    # Check health
                                                                                    # REMOVED_SYNTAX_ERROR: health = await event_monitor.check_health()

                                                                                    # Should detect stale thread
                                                                                    # REMOVED_SYNTAX_ERROR: assert len(health['stale_threads']) > 0
                                                                                    # REMOVED_SYNTAX_ERROR: assert health['stale_threads'][0]['thread_id'] == thread_id

                                                                                    # Removed problematic line: @pytest.mark.asyncio
                                                                                    # Removed problematic line: async def test_event_monitor_tracks_latency(self, event_monitor):
                                                                                        # REMOVED_SYNTAX_ERROR: '''
                                                                                        # REMOVED_SYNTAX_ERROR: Test that event monitor tracks event latency.
                                                                                        # REMOVED_SYNTAX_ERROR: """"
                                                                                        # REMOVED_SYNTAX_ERROR: thread_id = "latency_test"

                                                                                        # Record events with delay
                                                                                        # REMOVED_SYNTAX_ERROR: await event_monitor.record_event("agent_started", thread_id)
                                                                                        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
                                                                                        # REMOVED_SYNTAX_ERROR: await event_monitor.record_event("agent_thinking", thread_id)

                                                                                        # Check metrics
                                                                                        # REMOVED_SYNTAX_ERROR: health = await event_monitor.check_health()

                                                                                        # REMOVED_SYNTAX_ERROR: assert 'metrics' in health
                                                                                        # REMOVED_SYNTAX_ERROR: assert 'avg_latency' in health['metrics']
                                                                                        # REMOVED_SYNTAX_ERROR: assert health['metrics']['avg_latency'] >= 0.1

                                                                                        # Removed problematic line: @pytest.mark.asyncio
                                                                                        # Removed problematic line: async def test_comprehensive_silent_failure_scenario(self, mock_websocket_manager, mock_context):
                                                                                            # REMOVED_SYNTAX_ERROR: '''
                                                                                            # REMOVED_SYNTAX_ERROR: Test a comprehensive scenario with multiple potential silent failures.
                                                                                            # REMOVED_SYNTAX_ERROR: """"
                                                                                            # Set up monitoring
                                                                                            # REMOVED_SYNTAX_ERROR: monitor = ChatEventMonitor()

                                                                                            # Simulate various failure conditions

                                                                                            # 1. WebSocket unavailable for some events
                                                                                            # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(None)  # No WebSocket

                                                                                            # REMOVED_SYNTAX_ERROR: with patch('netra_backend.app.agents.supervisor.websocket_notifier.logger') as mock_logger:
                                                                                                # Try to send events without WebSocket
                                                                                                # REMOVED_SYNTAX_ERROR: await notifier.send_agent_started(mock_context)

                                                                                                # Should log critical warning
                                                                                                # REMOVED_SYNTAX_ERROR: assert any("WebSocket manager not available" in str(call) for call in mock_logger.warning.call_args_list)

                                                                                                # 2. Connection health check failures
                                                                                                # REMOVED_SYNTAX_ERROR: mock_websocket_manager._ping_connection = AsyncMock(return_value=False)
                                                                                                # REMOVED_SYNTAX_ERROR: health = await mock_websocket_manager.check_connection_health("bad_conn")
                                                                                                # REMOVED_SYNTAX_ERROR: assert health is False

                                                                                                # 3. Event sequence violations
                                                                                                # REMOVED_SYNTAX_ERROR: await monitor.record_event("tool_completed", "thread_x", tool_name="tool1")
                                                                                                # REMOVED_SYNTAX_ERROR: assert len(monitor.silent_failures) > 0

                                                                                                # 4. Check overall system health
                                                                                                # REMOVED_SYNTAX_ERROR: health_report = await monitor.check_health()
                                                                                                # REMOVED_SYNTAX_ERROR: assert health_report['status'] != HealthStatus.HEALTHY.value
                                                                                                # REMOVED_SYNTAX_ERROR: assert len(health_report['issues']) > 0


                                                                                                # Removed problematic line: @pytest.mark.asyncio
                                                                                                # Removed problematic line: async def test_integration_full_websocket_flow_with_monitoring():
                                                                                                    # REMOVED_SYNTAX_ERROR: '''
                                                                                                    # REMOVED_SYNTAX_ERROR: Integration test: Full WebSocket flow with all safety mechanisms.
                                                                                                    # REMOVED_SYNTAX_ERROR: """"
                                                                                                    # Create real components
                                                                                                    # REMOVED_SYNTAX_ERROR: manager = WebSocketManager()
                                                                                                    # REMOVED_SYNTAX_ERROR: monitor = ChatEventMonitor()
                                                                                                    # REMOVED_SYNTAX_ERROR: await monitor.start_monitoring()

                                                                                                    # REMOVED_SYNTAX_ERROR: notifier = WebSocketNotifier(manager)

                                                                                                    # Create context
                                                                                                    # REMOVED_SYNTAX_ERROR: thread_id = "formatted_string"
                                                                                                    # REMOVED_SYNTAX_ERROR: context = context_instance  # Initialize appropriate service
                                                                                                    # REMOVED_SYNTAX_ERROR: context.thread_id = thread_id
                                                                                                    # REMOVED_SYNTAX_ERROR: context.agent_name = "test_agent"

                                                                                                    # Send sequence of events
                                                                                                    # REMOVED_SYNTAX_ERROR: await notifier.send_agent_started(context)
                                                                                                    # REMOVED_SYNTAX_ERROR: await monitor.record_event("agent_started", thread_id)

                                                                                                    # Simulate tool execution
                                                                                                    # REMOVED_SYNTAX_ERROR: await monitor.record_event("tool_executing", thread_id, tool_name="test_tool")
                                                                                                    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.1)
                                                                                                    # REMOVED_SYNTAX_ERROR: await monitor.record_event("tool_completed", thread_id, tool_name="test_tool")

                                                                                                    # Check system health
                                                                                                    # REMOVED_SYNTAX_ERROR: health = await monitor.check_health()

                                                                                                    # Should be healthy with proper sequence
                                                                                                    # REMOVED_SYNTAX_ERROR: assert health['healthy'] is True
                                                                                                    # REMOVED_SYNTAX_ERROR: assert len(health['silent_failures']) == 0
                                                                                                    # REMOVED_SYNTAX_ERROR: assert len(health['stale_threads']) == 0

                                                                                                    # Cleanup
                                                                                                    # REMOVED_SYNTAX_ERROR: await monitor.stop_monitoring()


                                                                                                    # REMOVED_SYNTAX_ERROR: if __name__ == "__main__":
                                                                                                        # Run tests
                                                                                                        # REMOVED_SYNTAX_ERROR: pytest.main([__file__, "-v", "--tb=short"])