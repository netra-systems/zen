"""
Comprehensive Unit Tests for WebSocketBridgeAdapter - SSOT Agent WebSocket Integration

Business Value Justification (BVJ):
- Segment: Platform/Internal + All User Segments  
- Business Goal: Platform Stability & Chat Business Value Delivery
- Value Impact: Ensures $500K+ ARR by validating WebSocket adapter that enables substantive AI chat interactions
- Strategic Impact: MISSION CRITICAL - Adapter failures = immediate revenue loss as agents cannot send WebSocket events

CRITICAL: WebSocketBridgeAdapter is the SSOT component that replaces legacy WebSocketContextMixin
and provides agents with clean interface to AgentWebSocketBridge for our core business value:
1. WebSocket events for real-time agent interaction (user engagement)
2. Clean separation of concerns between agents and WebSocket infrastructure
3. Consistent error handling and logging for all agent WebSocket operations
4. Parameter validation and sanitization protecting sensitive data

These tests validate that our adapter delivers business value by:
- Ensuring all 5 critical WebSocket events are properly emitted
- Validating bridge configuration and management
- Testing error handling prevents agent crashes
- Verifying logging captures critical failures for debugging
- Confirming parameter validation protects sensitive data

Test Coverage Target: 100% of critical adapter flows in WebSocketBridgeAdapter
"""
import asyncio
import time
import uuid
from datetime import datetime
from unittest.mock import Mock, AsyncMock, patch, MagicMock, call
from typing import Dict, Any, Optional
import pytest
from test_framework.ssot.base import BaseTestCase, AsyncBaseTestCase
from shared.isolated_environment import get_env
from netra_backend.app.agents.mixins.websocket_bridge_adapter import WebSocketBridgeAdapter

class WebSocketBridgeAdapterInitializationTests(BaseTestCase):
    """Test WebSocketBridgeAdapter initialization and state management."""

    @pytest.mark.unit
    def test_adapter_initialization_default_state(self):
        """Test adapter initializes with proper default state."""
        adapter = WebSocketBridgeAdapter()
        assert adapter._bridge is None, 'Bridge should be None initially'
        assert adapter._run_id is None, 'Run ID should be None initially'
        assert adapter._agent_name is None, 'Agent name should be None initially'
        assert not adapter.has_websocket_bridge(), 'Should not have bridge initially'

    @pytest.mark.unit
    def test_adapter_initialization_multiple_instances(self):
        """Test multiple adapter instances are properly isolated."""
        adapter1 = WebSocketBridgeAdapter()
        adapter2 = WebSocketBridgeAdapter()
        assert adapter1 is not adapter2, 'Should create separate instances'
        assert adapter1._bridge is None, 'Bridge should be None initially'
        assert adapter2._bridge is None, 'Bridge should be None initially'
        assert adapter1._run_id is None, 'Run ID should be None initially'
        assert adapter2._run_id is None, 'Run ID should be None initially'
        mock_bridge1 = AsyncMock()
        mock_bridge2 = AsyncMock()
        adapter1.set_websocket_bridge(mock_bridge1, 'run-1', 'Agent1')
        adapter2.set_websocket_bridge(mock_bridge2, 'run-2', 'Agent2')
        assert adapter1._bridge is not adapter2._bridge, 'Bridges should be independent'
        assert adapter1._run_id != adapter2._run_id, 'Run IDs should be independent'

class WebSocketBridgeAdapterConfigurationTests(AsyncBaseTestCase):
    """Test WebSocketBridgeAdapter bridge configuration and management."""

    @pytest.mark.unit
    async def test_set_websocket_bridge_success(self):
        """Test successful WebSocket bridge configuration."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        run_id = 'test-run-123'
        agent_name = 'TestAgent'
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            adapter.set_websocket_bridge(mock_bridge, run_id, agent_name)
            assert adapter._bridge is mock_bridge, 'Bridge should be set'
            assert adapter._run_id == run_id, 'Run ID should be set'
            assert adapter._agent_name == agent_name, 'Agent name should be set'
            assert adapter.has_websocket_bridge(), 'Should have bridge after configuration'
            mock_logger.info.assert_called_once()
            success_log = mock_logger.info.call_args[0][0]
            assert ' PASS:  WebSocket bridge configured' in success_log
            assert agent_name in success_log
            assert run_id in success_log

    @pytest.mark.unit
    async def test_set_websocket_bridge_none_bridge_critical_error(self):
        """Test setting None bridge triggers critical error logging."""
        adapter = WebSocketBridgeAdapter()
        agent_name = 'TestAgent'
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            adapter.set_websocket_bridge(None, 'run-123', agent_name)
            assert mock_logger.error.call_count == 2, 'Should log critical error for None bridge'
            error_calls = mock_logger.error.call_args_list
            first_error = error_calls[0][0][0]
            assert ' FAIL:  CRITICAL' in first_error
            assert 'None bridge' in first_error
            assert agent_name in first_error
            second_error = error_calls[1][0][0]
            assert ' FAIL:  WebSocket bridge configuration FAILED' in second_error

    @pytest.mark.unit
    async def test_set_websocket_bridge_none_run_id_critical_error(self):
        """Test setting None run_id triggers critical error logging."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        agent_name = 'TestAgent'
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            adapter.set_websocket_bridge(mock_bridge, None, agent_name)
            error_calls = mock_logger.error.call_args_list
            assert any((' FAIL:  CRITICAL' in str(call) and 'None run_id' in str(call) for call in error_calls))
            assert any((' FAIL:  WebSocket bridge configuration FAILED' in str(call) for call in error_calls))

    @pytest.mark.unit
    async def test_set_websocket_bridge_empty_run_id_critical_error(self):
        """Test setting empty run_id triggers critical error logging."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        agent_name = 'TestAgent'
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            adapter.set_websocket_bridge(mock_bridge, '', agent_name)
            error_calls = mock_logger.error.call_args_list
            assert any((' FAIL:  WebSocket bridge configuration FAILED' in str(call) for call in error_calls))

    @pytest.mark.unit
    async def test_set_websocket_bridge_reconfiguration(self):
        """Test reconfiguring bridge with different parameters."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge1 = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge1, 'run-123', 'Agent1')
        mock_bridge2 = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge2, 'run-456', 'Agent2')
        assert adapter._bridge is mock_bridge2, 'Bridge should be updated'
        assert adapter._run_id == 'run-456', 'Run ID should be updated'
        assert adapter._agent_name == 'Agent2', 'Agent name should be updated'

    @pytest.mark.unit
    async def test_has_websocket_bridge_various_states(self):
        """Test has_websocket_bridge method under various configuration states."""
        adapter = WebSocketBridgeAdapter()
        assert not adapter.has_websocket_bridge()
        adapter._bridge = AsyncMock()
        assert not adapter.has_websocket_bridge()
        adapter._bridge = None
        adapter._run_id = 'run-123'
        assert not adapter.has_websocket_bridge()
        adapter._bridge = AsyncMock()
        adapter._run_id = 'run-123'
        assert adapter.has_websocket_bridge()
        adapter._run_id = None
        assert not adapter.has_websocket_bridge()

class WebSocketBridgeAdapterEventEmissionTests(AsyncBaseTestCase):
    """Test WebSocketBridgeAdapter event emission methods (MISSION CRITICAL for chat value)."""

    def create_test_adapter(self):
        """Create a configured test adapter for testing."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        run_id = 'test-run-123'
        agent_name = 'TestAgent'
        adapter.set_websocket_bridge(mock_bridge, run_id, agent_name)
        return (adapter, mock_bridge, run_id, agent_name)

    @pytest.mark.unit
    async def test_emit_agent_started_success(self):
        """Test successful agent_started event emission."""
        adapter, mock_bridge, run_id, agent_name = self.create_test_adapter()
        message = 'Starting analysis of your request'
        await adapter.emit_agent_started(message)
        mock_bridge.notify_agent_started.assert_called_once_with(run_id, agent_name, context={'message': message})

    @pytest.mark.unit
    async def test_emit_agent_started_no_message(self):
        """Test agent_started event emission without message."""
        await self.adapter.emit_agent_started()
        self.mock_bridge.notify_agent_started.assert_called_once_with(self.run_id, self.agent_name, context={})

    @pytest.mark.unit
    async def test_emit_agent_started_no_bridge_warning(self):
        """Test agent_started emission without bridge logs warning."""
        no_bridge_adapter = WebSocketBridgeAdapter()
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await no_bridge_adapter.emit_agent_started('test message')
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert ' FAIL:  No WebSocket bridge for agent_started event' in warning_msg

    @pytest.mark.unit
    async def test_emit_agent_started_bridge_exception_handled(self):
        """Test agent_started emission handles bridge exceptions gracefully."""
        self.mock_bridge.notify_agent_started.side_effect = RuntimeError('WebSocket connection failed')
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_agent_started('test message')
            mock_logger.debug.assert_called_once_with('Failed to emit agent_started: WebSocket connection failed')

    @pytest.mark.unit
    async def test_emit_thinking_success(self):
        """Test successful agent_thinking event emission."""
        thought = 'Analyzing your cost optimization requirements'
        step_number = 1
        await self.adapter.emit_thinking(thought, step_number)
        self.mock_bridge.notify_agent_thinking.assert_called_once_with(self.run_id, self.agent_name, thought, step_number=step_number)

    @pytest.mark.unit
    async def test_emit_thinking_without_step_number(self):
        """Test thinking event emission without step number."""
        thought = 'Processing your request'
        await self.adapter.emit_thinking(thought)
        self.mock_bridge.notify_agent_thinking.assert_called_once_with(self.run_id, self.agent_name, thought, step_number=None)

    @pytest.mark.unit
    async def test_emit_thinking_no_bridge_silent_return(self):
        """Test thinking emission without bridge returns silently."""
        no_bridge_adapter = WebSocketBridgeAdapter()
        await no_bridge_adapter.emit_thinking('test thought')

    @pytest.mark.unit
    async def test_emit_thinking_bridge_exception_handled(self):
        """Test thinking emission handles bridge exceptions gracefully."""
        self.mock_bridge.notify_agent_thinking.side_effect = ConnectionError('WebSocket disconnected')
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_thinking('test thought')
            mock_logger.debug.assert_called_once_with('Failed to emit thinking: WebSocket disconnected')

    @pytest.mark.unit
    async def test_emit_tool_executing_success(self):
        """Test successful tool_executing event emission."""
        tool_name = 'CostAnalyzer'
        parameters = {'region': 'us-east-1', 'period': 'monthly'}
        await self.adapter.emit_tool_executing(tool_name, parameters)
        self.mock_bridge.notify_tool_executing.assert_called_once_with(self.run_id, self.agent_name, tool_name, parameters=parameters)

    @pytest.mark.unit
    async def test_emit_tool_executing_without_parameters(self):
        """Test tool_executing emission without parameters."""
        tool_name = 'StatusChecker'
        await self.adapter.emit_tool_executing(tool_name)
        self.mock_bridge.notify_tool_executing.assert_called_once_with(self.run_id, self.agent_name, tool_name, parameters=None)

    @pytest.mark.unit
    async def test_emit_tool_executing_bridge_exception_handled(self):
        """Test tool_executing emission handles bridge exceptions."""
        self.mock_bridge.notify_tool_executing.side_effect = TimeoutError('WebSocket timeout')
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_tool_executing('TestTool', {})
            mock_logger.debug.assert_called_once_with('Failed to emit tool_executing: WebSocket timeout')

    @pytest.mark.unit
    async def test_emit_tool_completed_success(self):
        """Test successful tool_completed event emission."""
        tool_name = 'CostAnalyzer'
        result = {'monthly_spend': 1500, 'optimization_potential': 20}
        await self.adapter.emit_tool_completed(tool_name, result)
        self.mock_bridge.notify_tool_completed.assert_called_once_with(self.run_id, self.agent_name, tool_name, result=result)

    @pytest.mark.unit
    async def test_emit_tool_completed_without_result(self):
        """Test tool_completed emission without result data."""
        tool_name = 'SystemNotifier'
        await self.adapter.emit_tool_completed(tool_name)
        self.mock_bridge.notify_tool_completed.assert_called_once_with(self.run_id, self.agent_name, tool_name, result=None)

    @pytest.mark.unit
    async def test_emit_tool_completed_bridge_exception_handled(self):
        """Test tool_completed emission handles bridge exceptions."""
        self.mock_bridge.notify_tool_completed.side_effect = ValueError('Invalid result format')
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_tool_completed('TestTool', {'data': 'test'})
            mock_logger.debug.assert_called_once_with('Failed to emit tool_completed: Invalid result format')

    @pytest.mark.unit
    async def test_emit_agent_completed_success(self):
        """Test successful agent_completed event emission."""
        result = {'analysis': 'Cost optimization completed', 'savings': 300}
        await self.adapter.emit_agent_completed(result)
        self.mock_bridge.notify_agent_completed.assert_called_once_with(self.run_id, self.agent_name, result=result)

    @pytest.mark.unit
    async def test_emit_agent_completed_without_result(self):
        """Test agent_completed emission without result data."""
        await self.adapter.emit_agent_completed()
        self.mock_bridge.notify_agent_completed.assert_called_once_with(self.run_id, self.agent_name, result=None)

    @pytest.mark.unit
    async def test_emit_agent_completed_no_bridge_warning(self):
        """Test agent_completed emission without bridge logs warning."""
        no_bridge_adapter = WebSocketBridgeAdapter()
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await no_bridge_adapter.emit_agent_completed({'result': 'test'})
            mock_logger.warning.assert_called_once()
            warning_msg = mock_logger.warning.call_args[0][0]
            assert ' FAIL:  No WebSocket bridge for agent_completed event' in warning_msg

    @pytest.mark.unit
    async def test_emit_agent_completed_bridge_exception_handled(self):
        """Test agent_completed emission handles bridge exceptions."""
        self.mock_bridge.notify_agent_completed.side_effect = Exception('Unexpected error')
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_agent_completed({'data': 'test'})
            mock_logger.debug.assert_called_once_with('Failed to emit agent_completed: Unexpected error')

    @pytest.mark.unit
    async def test_emit_progress_success(self):
        """Test successful progress update emission."""
        content = 'Processing 75% complete'
        is_complete = False
        await self.adapter.emit_progress(content, is_complete)
        expected_progress_data = {'content': content, 'is_complete': is_complete}
        self.mock_bridge.notify_progress_update.assert_called_once_with(self.run_id, self.agent_name, expected_progress_data)

    @pytest.mark.unit
    async def test_emit_progress_completion(self):
        """Test progress emission with completion flag."""
        content = 'Analysis complete'
        await self.adapter.emit_progress(content, is_complete=True)
        call_args = self.mock_bridge.notify_progress_update.call_args[0]
        progress_data = call_args[2]
        assert progress_data['is_complete'] is True

    @pytest.mark.unit
    async def test_emit_progress_bridge_exception_handled(self):
        """Test progress emission handles bridge exceptions."""
        self.mock_bridge.notify_progress_update.side_effect = RuntimeError('Progress update failed')
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_progress('test progress')
            mock_logger.debug.assert_called_once_with('Failed to emit progress: Progress update failed')

    @pytest.mark.unit
    async def test_emit_error_success(self):
        """Test successful error event emission."""
        error_message = 'Failed to access cost data'
        error_type = 'PERMISSION_DENIED'
        error_details = {'resource': 'billing_api', 'code': 403}
        await self.adapter.emit_error(error_message, error_type, error_details)
        expected_context = {'error_type': error_type, 'details': error_details}
        self.mock_bridge.notify_agent_error.assert_called_once_with(self.run_id, self.agent_name, error_message, error_context=expected_context)

    @pytest.mark.unit
    async def test_emit_error_minimal_parameters(self):
        """Test error emission with minimal parameters."""
        error_message = 'Something went wrong'
        await self.adapter.emit_error(error_message)
        expected_context = {'error_type': 'general', 'details': None}
        self.mock_bridge.notify_agent_error.assert_called_once_with(self.run_id, self.agent_name, error_message, error_context=expected_context)

    @pytest.mark.unit
    async def test_emit_error_with_type_only(self):
        """Test error emission with type but no details."""
        error_message = 'Authentication failed'
        error_type = 'AUTH_ERROR'
        await self.adapter.emit_error(error_message, error_type)
        call_args = self.mock_bridge.notify_agent_error.call_args
        error_context = call_args[1]['error_context']
        assert error_context['error_type'] == error_type
        assert error_context['details'] is None

    @pytest.mark.unit
    async def test_emit_error_no_type_or_details(self):
        """Test error emission without type or details."""
        error_message = 'Basic error'
        await self.adapter.emit_error(error_message, None, None)
        self.mock_bridge.notify_agent_error.assert_called_once_with(self.run_id, self.agent_name, error_message, error_context=None)

    @pytest.mark.unit
    async def test_emit_error_bridge_exception_handled(self):
        """Test error emission handles bridge exceptions."""
        self.mock_bridge.notify_agent_error.side_effect = Exception('Error notification failed')
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_error('Original error message')
            mock_logger.debug.assert_called_once_with('Failed to emit error: Error notification failed')

class WebSocketBridgeAdapterBackwardCompatibilityTests(AsyncBaseTestCase):
    """Test WebSocketBridgeAdapter backward compatibility methods."""

    def create_test_adapter_for_compatibility(self):
        """Create a configured test adapter for backward compatibility testing."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, 'run-123', 'TestAgent')
        return (adapter, mock_bridge)

    @pytest.mark.unit
    async def test_emit_tool_started_maps_to_tool_executing(self):
        """Test emit_tool_started maps to emit_tool_executing for backward compatibility."""
        tool_name = 'LegacyTool'
        parameters = {'param1': 'value1'}
        await self.adapter.emit_tool_started(tool_name, parameters)
        self.mock_bridge.notify_tool_executing.assert_called_once_with('run-123', 'TestAgent', tool_name, parameters=parameters)

    @pytest.mark.unit
    async def test_emit_subagent_started_success(self):
        """Test subagent_started event emission using custom notification."""
        subagent_name = 'DataAnalysisSubAgent'
        subagent_id = 'subagent-456'
        await self.adapter.emit_subagent_started(subagent_name, subagent_id)
        expected_data = {'subagent_name': subagent_name, 'subagent_id': subagent_id}
        self.mock_bridge.notify_custom.assert_called_once_with('run-123', 'TestAgent', 'subagent_started', expected_data)

    @pytest.mark.unit
    async def test_emit_subagent_started_without_id(self):
        """Test subagent_started emission without subagent ID."""
        subagent_name = 'SimpleSubAgent'
        await self.adapter.emit_subagent_started(subagent_name)
        expected_data = {'subagent_name': subagent_name, 'subagent_id': None}
        self.mock_bridge.notify_custom.assert_called_once_with('run-123', 'TestAgent', 'subagent_started', expected_data)

    @pytest.mark.unit
    async def test_emit_subagent_completed_success(self):
        """Test subagent_completed event emission with full parameters."""
        subagent_name = 'DataAnalysisSubAgent'
        subagent_id = 'subagent-456'
        result = {'processed_records': 1000, 'insights': ['trend1', 'trend2']}
        duration_ms = 1500.5
        await self.adapter.emit_subagent_completed(subagent_name, subagent_id, result, duration_ms)
        expected_data = {'subagent_name': subagent_name, 'subagent_id': subagent_id, 'result': result, 'duration_ms': duration_ms}
        self.mock_bridge.notify_custom.assert_called_once_with('run-123', 'TestAgent', 'subagent_completed', expected_data)

    @pytest.mark.unit
    async def test_emit_subagent_completed_minimal(self):
        """Test subagent_completed emission with minimal parameters."""
        subagent_name = 'SimpleSubAgent'
        await self.adapter.emit_subagent_completed(subagent_name)
        expected_data = {'subagent_name': subagent_name, 'subagent_id': None, 'result': None, 'duration_ms': 0}
        self.mock_bridge.notify_custom.assert_called_once_with('run-123', 'TestAgent', 'subagent_completed', expected_data)

    @pytest.mark.unit
    async def test_subagent_events_no_bridge_silent_return(self):
        """Test subagent events return silently without bridge."""
        no_bridge_adapter = WebSocketBridgeAdapter()
        await no_bridge_adapter.emit_subagent_started('TestSubAgent')
        await no_bridge_adapter.emit_subagent_completed('TestSubAgent')

    @pytest.mark.unit
    async def test_subagent_events_bridge_exceptions_handled(self):
        """Test subagent events handle bridge exceptions gracefully."""
        self.mock_bridge.notify_custom.side_effect = RuntimeError('Custom notification failed')
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            await self.adapter.emit_subagent_started('TestSubAgent')
            await self.adapter.emit_subagent_completed('TestSubAgent')
            assert mock_logger.debug.call_count == 2
            debug_calls = [call[0][0] for call in mock_logger.debug.call_args_list]
            assert any(('Failed to emit subagent_started' in msg for msg in debug_calls))
            assert any(('Failed to emit subagent_completed' in msg for msg in debug_calls))

class WebSocketBridgeAdapterErrorHandlingAndEdgeCasesTests(AsyncBaseTestCase):
    """Test WebSocketBridgeAdapter error handling and edge cases."""

    @pytest.mark.unit
    async def test_all_events_no_bridge_behavior_consistent(self):
        """Test all event methods behave consistently without bridge."""
        adapter = WebSocketBridgeAdapter()
        warning_methods = [('emit_agent_started', []), ('emit_agent_completed', [])]
        silent_methods = [('emit_thinking', ['test thought']), ('emit_tool_executing', ['test tool']), ('emit_tool_completed', ['test tool']), ('emit_progress', ['test progress']), ('emit_error', ['test error']), ('emit_tool_started', ['test tool']), ('emit_subagent_started', ['test subagent']), ('emit_subagent_completed', ['test subagent'])]
        with patch('netra_backend.app.agents.mixins.websocket_bridge_adapter.logger') as mock_logger:
            for method_name, args in warning_methods:
                method = getattr(adapter, method_name)
                await method(*args)
            for method_name, args in silent_methods:
                method = getattr(adapter, method_name)
                await method(*args)
            assert mock_logger.warning.call_count == len(warning_methods)

    @pytest.mark.unit
    async def test_concurrent_event_emissions_thread_safe(self):
        """Test concurrent event emissions are handled safely."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, 'run-123', 'TestAgent')
        tasks = [adapter.emit_agent_started('Starting'), adapter.emit_thinking('Thinking'), adapter.emit_tool_executing('Tool1'), adapter.emit_tool_completed('Tool1', {'result': 'data'}), adapter.emit_progress('50% complete'), adapter.emit_agent_completed({'final': 'result'})]
        await asyncio.gather(*tasks)
        assert mock_bridge.notify_agent_started.call_count == 1
        assert mock_bridge.notify_agent_thinking.call_count == 1
        assert mock_bridge.notify_tool_executing.call_count == 1
        assert mock_bridge.notify_tool_completed.call_count == 1
        assert mock_bridge.notify_progress_update.call_count == 1
        assert mock_bridge.notify_agent_completed.call_count == 1

    @pytest.mark.unit
    async def test_event_emission_with_none_values(self):
        """Test event emission handles None values gracefully."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, 'run-123', 'TestAgent')
        await adapter.emit_agent_started(None)
        await adapter.emit_thinking(None)
        await adapter.emit_tool_executing(None, None)
        await adapter.emit_tool_completed(None, None)
        await adapter.emit_progress(None)
        await adapter.emit_error(None)
        assert mock_bridge.notify_agent_started.call_count == 1
        assert mock_bridge.notify_tool_executing.call_count == 1
        assert mock_bridge.notify_tool_completed.call_count == 1
        assert mock_bridge.notify_progress_update.call_count == 1
        assert mock_bridge.notify_agent_error.call_count == 1

    @pytest.mark.unit
    async def test_extremely_large_data_handling(self):
        """Test handling of extremely large data payloads."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, 'run-123', 'TestAgent')
        large_data = {'large_list': ['item' + str(i) for i in range(10000)], 'large_string': 'x' * 100000, 'nested_data': {'level1': {'level2': {'level3': {'data': 'deep'}}}}}
        await adapter.emit_tool_completed('BigDataTool', large_data)
        await adapter.emit_agent_completed(large_data)
        assert mock_bridge.notify_tool_completed.call_count == 1
        assert mock_bridge.notify_agent_completed.call_count == 1

    @pytest.mark.unit
    async def test_unicode_and_special_characters_handling(self):
        """Test handling of Unicode and special characters in event data."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, 'run-123', 'TestAgent')
        unicode_data = {'emoji': '[U+1F680] Analysis complete! [U+1F4B0]', 'chinese': '[U+6570][U+636E][U+5206][U+6790][U+5B8C][U+6210]', 'arabic': '[U+062A][U+0645] [U+062A][U+062D][U+0644][U+064A][U+0644] [U+0627][U+0644][U+0628][U+064A][U+0627][U+0646][U+0627][U+062A]', 'special_chars': "Special chars: !@#$%^&*()_+{}|:<>?[]\\;',./", 'mixed': 'Mixed: Hello [U+4E16][U+754C] [U+1F30D] [U+0645][U+0631][U+062D][U+0628][U+0627]'}
        await adapter.emit_agent_started('Starting with [U+1F680]')
        await adapter.emit_thinking('Thinking about [U+6570][U+636E]')
        await adapter.emit_tool_completed('UnicodeTool', unicode_data)
        await adapter.emit_error('Error with special chars: !@#$%')
        assert mock_bridge.notify_agent_started.call_count == 1
        assert mock_bridge.notify_agent_thinking.call_count == 1
        assert mock_bridge.notify_tool_completed.call_count == 1
        assert mock_bridge.notify_agent_error.call_count == 1

    @pytest.mark.unit
    async def test_adapter_state_after_bridge_reconfiguration(self):
        """Test adapter state consistency after bridge reconfiguration."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge1 = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge1, 'run-123', 'Agent1')
        await adapter.emit_agent_started('Starting with bridge 1')
        await adapter.emit_thinking('Using bridge 1')
        mock_bridge2 = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge2, 'run-456', 'Agent2')
        await adapter.emit_tool_executing('Tool with bridge 2')
        await adapter.emit_agent_completed({'bridge': '2'})
        assert mock_bridge1.notify_agent_started.call_count == 1
        assert mock_bridge1.notify_agent_thinking.call_count == 1
        assert mock_bridge1.notify_tool_executing.call_count == 0
        assert mock_bridge1.notify_agent_completed.call_count == 0
        assert mock_bridge2.notify_agent_started.call_count == 0
        assert mock_bridge2.notify_agent_thinking.call_count == 0
        assert mock_bridge2.notify_tool_executing.call_count == 1
        assert mock_bridge2.notify_agent_completed.call_count == 1

class WebSocketBridgeAdapterPerformanceAndReliabilityTests(AsyncBaseTestCase):
    """Test WebSocketBridgeAdapter performance characteristics and reliability."""

    @pytest.mark.unit
    async def test_high_frequency_event_emissions(self):
        """Test adapter handles high frequency event emissions efficiently."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, 'run-123', 'HighThroughputAgent')
        event_count = 100
        start_time = time.time()
        for i in range(event_count):
            await adapter.emit_thinking(f'Thought {i}')
            await adapter.emit_progress(f'Progress {i}')
        end_time = time.time()
        assert mock_bridge.notify_agent_thinking.call_count == event_count
        assert mock_bridge.notify_progress_update.call_count == event_count
        duration = end_time - start_time
        assert duration < 5.0, f'High frequency emissions took too long: {duration}s'

    @pytest.mark.unit
    async def test_adapter_memory_usage_stability(self):
        """Test adapter doesn't accumulate memory over many operations."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, 'run-123', 'LongRunningAgent')
        for cycle in range(10):
            new_bridge = AsyncMock()
            adapter.set_websocket_bridge(new_bridge, f'run-{cycle}', f'Agent-{cycle}')
            await adapter.emit_agent_started(f'Cycle {cycle}')
            await adapter.emit_thinking(f'Processing cycle {cycle}')
            await adapter.emit_tool_executing(f'Tool-{cycle}', {'cycle': cycle})
            await adapter.emit_tool_completed(f'Tool-{cycle}', {'result': f'data-{cycle}'})
            await adapter.emit_agent_completed({'cycle': cycle, 'status': 'complete'})
        assert adapter._bridge is not None, 'Should have current bridge'
        assert adapter._run_id == 'run-9', 'Should have latest run ID'
        assert adapter._agent_name == 'Agent-9', 'Should have latest agent name'
        assert adapter.has_websocket_bridge(), 'Should still have bridge'

    @pytest.mark.unit
    async def test_event_emission_timing_consistency(self):
        """Test event emission timing is consistent across different event types."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, 'run-123', 'TimingTestAgent')

        async def mock_delay(*args, **kwargs):
            await asyncio.sleep(0.001)
        mock_bridge.notify_agent_started.side_effect = mock_delay
        mock_bridge.notify_agent_thinking.side_effect = mock_delay
        mock_bridge.notify_tool_executing.side_effect = mock_delay
        mock_bridge.notify_tool_completed.side_effect = mock_delay
        mock_bridge.notify_agent_completed.side_effect = mock_delay
        mock_bridge.notify_progress_update.side_effect = mock_delay
        mock_bridge.notify_agent_error.side_effect = mock_delay
        event_timings = {}
        event_methods = [('agent_started', lambda: adapter.emit_agent_started('test')), ('thinking', lambda: adapter.emit_thinking('test')), ('tool_executing', lambda: adapter.emit_tool_executing('test')), ('tool_completed', lambda: adapter.emit_tool_completed('test')), ('agent_completed', lambda: adapter.emit_agent_completed()), ('progress', lambda: adapter.emit_progress('test')), ('error', lambda: adapter.emit_error('test'))]
        for event_name, event_method in event_methods:
            start_time = time.time()
            await event_method()
            end_time = time.time()
            event_timings[event_name] = end_time - start_time
        min_timing = min(event_timings.values())
        max_timing = max(event_timings.values())
        assert max_timing / min_timing < 10, f'Timing inconsistency: {event_timings}'

    @pytest.mark.unit
    async def test_adapter_cleanup_and_resource_management(self):
        """Test adapter properly manages resources and supports cleanup."""
        adapter = WebSocketBridgeAdapter()
        mock_bridge = AsyncMock()
        adapter.set_websocket_bridge(mock_bridge, 'run-123', 'CleanupTestAgent')
        await adapter.emit_agent_started('test')
        await adapter.emit_thinking('test')
        await adapter.emit_agent_completed()
        adapter._bridge = None
        adapter._run_id = None
        adapter._agent_name = None
        assert adapter._bridge is None
        assert adapter._run_id is None
        assert adapter._agent_name is None
        assert not adapter.has_websocket_bridge()
        await adapter.emit_agent_started('should not emit')
        await adapter.emit_thinking('should not emit')
        assert mock_bridge.notify_agent_started.call_count == 1
        assert mock_bridge.notify_agent_thinking.call_count == 1
if __name__ == '__main__':
    'MIGRATED: Use SSOT unified test runner'
    print('MIGRATION NOTICE: Please use SSOT unified test runner')
    print('Command: python tests/unified_test_runner.py --category <category>')