"""
Integration Tests for WebSocket Event Validation Framework

Business Value: Ensures validation framework integrates seamlessly with existing components
without breaking functionality while providing 100% event validation coverage.
"""

import asyncio
import pytest
import time
import uuid
from typing import Dict, List, Any
from unittest.mock import Mock, AsyncMock, patch, MagicMock

from netra_backend.app.websocket_core.validation_integration import (
    WebSocketValidationWrapper,
    create_websocket_manager_validator,
    create_websocket_notifier_validator,
    create_tool_execution_validator,
    enhance_component_with_validation,
    validation_decorator,
    validation_context,
    enable_global_validation,
    get_validation_statistics
)

from netra_backend.app.websocket_core.event_validation_framework import (
    EventValidationLevel,
    ValidationResult,
    ValidatedEvent
)


class TestWebSocketValidationWrapper:
    """Test the base WebSocketValidationWrapper functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock component to wrap
        self.mock_component = Mock()
        self.mock_component.some_method = AsyncMock(return_value=True)
        self.mock_component.sync_method = Mock(return_value="result")
        
        self.wrapper = WebSocketValidationWrapper(self.mock_component, EventValidationLevel.MODERATE)
    
    def test_wrapper_delegates_attributes(self):
        """Test wrapper delegates attributes to wrapped component."""
        # Access attributes from wrapped component
        assert self.wrapper.some_method == self.mock_component.some_method
        assert self.wrapper.sync_method == self.mock_component.sync_method
    
    @pytest.mark.asyncio
    async def test_validate_and_send_success(self):
        """Test successful validation and method execution."""
        event_data = {
            'type': 'agent_started',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'timestamp': time.time()
            },
            'thread_id': 'thread-123',
            'timestamp': time.time()
        }
        
        context = {'thread_id': 'thread-123', 'run_id': 'run-123'}
        
        result = await self.wrapper._validate_and_send(
            self.mock_component.some_method,
            event_data,
            context,
            'arg1', 'arg2'
        )
        
        # Should call original method
        self.mock_component.some_method.assert_called_once_with('arg1', 'arg2')
        assert result is True
        
        # Check validation stats
        assert self.wrapper.validation_stats['total_events'] == 1
        assert self.wrapper.validation_stats['validated_events'] == 1
    
    @pytest.mark.asyncio
    async def test_validate_and_send_with_validation_disabled(self):
        """Test wrapper bypasses validation when disabled."""
        self.wrapper.validation_enabled = False
        
        event_data = {'type': 'test_event'}
        result = await self.wrapper._validate_and_send(
            self.mock_component.some_method,
            event_data,
            {},
            'arg1'
        )
        
        # Should still call original method
        self.mock_component.some_method.assert_called_once_with('arg1')
        assert result is True
        
        # Check stats show bypass
        assert self.wrapper.validation_stats['bypassed_events'] == 1
    
    @pytest.mark.asyncio 
    async def test_validate_and_send_with_validation_errors(self):
        """Test wrapper handles validation errors gracefully."""
        # Create event with validation issues
        event_data = {
            'type': 'agent_thinking',
            'payload': {
                'thought': '',  # Empty thought should cause validation error
                'agent_name': 'test_agent',
                'timestamp': time.time()
            },
            'thread_id': 'thread-123',
            'timestamp': time.time()
        }
        
        context = {'thread_id': 'thread-123'}
        
        result = await self.wrapper._validate_and_send(
            self.mock_component.some_method,
            event_data,
            context,
            'arg1'
        )
        
        # Should still call original method (fallback behavior)
        self.mock_component.some_method.assert_called_once_with('arg1')
        assert result is True
        
        # Check validation stats recorded the validation
        assert self.wrapper.validation_stats['validated_events'] >= 1


class TestWebSocketManagerValidator:
    """Test WebSocket manager validation integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock WebSocket manager
        self.mock_manager = Mock()
        self.mock_manager.send_to_thread = AsyncMock(return_value=True)
        self.mock_manager.broadcast = AsyncMock(return_value=True)
        
        self.validated_manager = create_websocket_manager_validator(
            self.mock_manager, EventValidationLevel.MODERATE
        )
    
    @pytest.mark.asyncio
    async def test_send_to_thread_with_validation(self):
        """Test send_to_thread with event validation."""
        message = {
            'type': 'agent_started',
            'payload': {
                'agent_name': 'test_agent',
                'run_id': 'run-123',
                'timestamp': time.time()
            }
        }
        
        result = await self.validated_manager.send_to_thread('thread-123', message)
        
        # Should call original method
        self.mock_manager.send_to_thread.assert_called_once()
        assert result is True
        
        # Check validation occurred
        assert self.validated_manager.validation_stats['total_events'] >= 1
    
    @pytest.mark.asyncio
    async def test_send_to_thread_with_string_message(self):
        """Test send_to_thread handles string messages."""
        result = await self.validated_manager.send_to_thread('thread-123', 'test message')
        
        # Should convert string to dict and call original method
        self.mock_manager.send_to_thread.assert_called_once()
        assert result is True
    
    @pytest.mark.asyncio
    async def test_broadcast_with_validation(self):
        """Test broadcast with event validation."""
        message = {
            'type': 'broadcast',
            'content': 'Test broadcast message'
        }
        
        result = await self.validated_manager.broadcast(message, 'general')
        
        # Should call original method
        self.mock_manager.broadcast.assert_called_once()
        assert result is True


class TestWebSocketNotifierValidator:
    """Test WebSocket notifier validation integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock WebSocket notifier
        self.mock_notifier = Mock()
        self.mock_notifier.send_agent_started = AsyncMock()
        self.mock_notifier.send_agent_thinking = AsyncMock()
        self.mock_notifier.send_tool_executing = AsyncMock()
        self.mock_notifier.send_tool_completed = AsyncMock()
        self.mock_notifier.send_agent_completed = AsyncMock()
        
        self.validated_notifier = create_websocket_notifier_validator(
            self.mock_notifier, EventValidationLevel.MODERATE
        )
        
        # Create mock context
        self.mock_context = Mock()
        self.mock_context.agent_name = 'test_agent'
        self.mock_context.run_id = 'run-123'
        self.mock_context.thread_id = 'thread-123'
    
    @pytest.mark.asyncio
    async def test_send_agent_started_with_validation(self):
        """Test agent started event validation."""
        await self.validated_notifier.send_agent_started(self.mock_context)
        
        # Should call original method
        self.mock_notifier.send_agent_started.assert_called_once_with(self.mock_context)
        
        # Check validation occurred
        assert self.validated_notifier.validation_stats['total_events'] >= 1
    
    @pytest.mark.asyncio
    async def test_send_agent_thinking_with_validation(self):
        """Test agent thinking event validation."""
        await self.validated_notifier.send_agent_thinking(self.mock_context, "Processing request")
        
        # Should call original method
        self.mock_notifier.send_agent_thinking.assert_called_once_with(
            self.mock_context, "Processing request"
        )
        
        # Check validation occurred
        assert self.validated_notifier.validation_stats['total_events'] >= 1
    
    @pytest.mark.asyncio
    async def test_send_tool_executing_with_validation(self):
        """Test tool executing event validation."""
        await self.validated_notifier.send_tool_executing(self.mock_context, "web_search")
        
        # Should call original method
        self.mock_notifier.send_tool_executing.assert_called_once_with(
            self.mock_context, "web_search"
        )
        
        # Check validation occurred
        assert self.validated_notifier.validation_stats['total_events'] >= 1
    
    @pytest.mark.asyncio
    async def test_send_tool_completed_with_validation(self):
        """Test tool completed event validation."""
        result = {'status': 'success', 'data': 'results'}
        
        await self.validated_notifier.send_tool_completed(self.mock_context, "web_search", result)
        
        # Should call original method
        self.mock_notifier.send_tool_completed.assert_called_once_with(
            self.mock_context, "web_search", result
        )
        
        # Check validation occurred
        assert self.validated_notifier.validation_stats['total_events'] >= 1
    
    @pytest.mark.asyncio
    async def test_send_agent_completed_with_validation(self):
        """Test agent completed event validation."""
        result = {'answer': 'Task completed'}
        
        await self.validated_notifier.send_agent_completed(self.mock_context, result, 5000)
        
        # Should call original method
        self.mock_notifier.send_agent_completed.assert_called_once_with(
            self.mock_context, result, 5000
        )
        
        # Check validation occurred
        assert self.validated_notifier.validation_stats['total_events'] >= 1


class TestToolExecutionValidator:
    """Test tool execution engine validation integration."""
    
    def setup_method(self):
        """Set up test fixtures."""
        # Create mock tool execution engine
        self.mock_engine = Mock()
        self.mock_engine.execute_tool = AsyncMock(return_value={'result': 'success'})
        self.mock_engine.websocket_bridge = Mock()  # Has WebSocket capabilities
        
        self.validated_engine = create_tool_execution_validator(
            self.mock_engine, EventValidationLevel.MODERATE
        )
        
        # Create mock tool input and context
        self.mock_tool_input = Mock()
        self.mock_tool_input.tool_name = 'web_search'
        
        self.mock_context = Mock()
        self.mock_context.thread_id = 'thread-123'
        self.mock_context.run_id = 'run-456'
        self.mock_context.agent_name = 'test_agent'
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_validation(self):
        """Test tool execution with event validation."""
        result = await self.validated_engine.execute_tool(
            self.mock_tool_input, self.mock_context
        )
        
        # Should call original method
        self.mock_engine.execute_tool.assert_called_once_with(
            self.mock_tool_input, self.mock_context
        )
        
        assert result == {'result': 'success'}
        
        # Check validation occurred (tool_executing and tool_completed events)
        assert self.validated_engine.validation_stats['total_events'] >= 2
    
    @pytest.mark.asyncio
    async def test_execute_tool_with_exception_validation(self):
        """Test tool execution validation handles exceptions."""
        # Make the tool execution fail
        self.mock_engine.execute_tool.side_effect = Exception("Tool failed")
        
        with pytest.raises(Exception, match="Tool failed"):
            await self.validated_engine.execute_tool(
                self.mock_tool_input, self.mock_context
            )
        
        # Should still validate events even when tool fails
        assert self.validated_engine.validation_stats['total_events'] >= 1


class TestEnhanceComponentWithValidation:
    """Test the generic component enhancement function."""
    
    @pytest.mark.asyncio
    async def test_enhance_websocket_manager(self):
        """Test enhancing WebSocket manager component."""
        mock_manager = Mock()
        mock_manager.__class__.__name__ = 'WebSocketManager'
        mock_manager.send_to_thread = AsyncMock(return_value=True)
        
        enhanced = await enhance_component_with_validation(
            mock_manager, 'WebSocketManager', EventValidationLevel.MODERATE
        )
        
        assert hasattr(enhanced, 'validation_framework')
        assert hasattr(enhanced, 'validation_stats')
    
    @pytest.mark.asyncio
    async def test_enhance_websocket_notifier(self):
        """Test enhancing WebSocket notifier component."""
        mock_notifier = Mock()
        mock_notifier.__class__.__name__ = 'WebSocketNotifier'
        mock_notifier.send_agent_started = AsyncMock()
        
        enhanced = await enhance_component_with_validation(
            mock_notifier, 'WebSocketNotifier', EventValidationLevel.STRICT
        )
        
        assert hasattr(enhanced, 'validation_framework')
        assert enhanced.validation_level == EventValidationLevel.STRICT
    
    @pytest.mark.asyncio
    async def test_enhance_unknown_component(self):
        """Test enhancing unknown component type."""
        mock_component = Mock()
        mock_component.__class__.__name__ = 'UnknownComponent'
        
        enhanced = await enhance_component_with_validation(
            mock_component, 'UnknownComponent', EventValidationLevel.PERMISSIVE
        )
        
        # Should use generic wrapper
        assert isinstance(enhanced, WebSocketValidationWrapper)


class TestValidationDecorator:
    """Test the validation decorator functionality."""
    
    def test_async_function_decoration(self):
        """Test decorator on async functions."""
        @validation_decorator('test_event', EventValidationLevel.MODERATE)
        async def async_test_function(arg1, arg2):
            return f"result: {arg1}, {arg2}"
        
        # Function should be decorated
        assert hasattr(async_test_function, '__wrapped__')
        assert async_test_function.__name__ == 'async_test_function'
    
    def test_sync_function_decoration(self):
        """Test decorator on sync functions."""
        @validation_decorator('test_event', EventValidationLevel.MODERATE)
        def sync_test_function(arg1, arg2):
            return f"result: {arg1}, {arg2}"
        
        # Function should be decorated
        assert hasattr(sync_test_function, '__wrapped__')
        assert sync_test_function.__name__ == 'sync_test_function'
    
    @pytest.mark.asyncio
    async def test_decorated_async_function_execution(self):
        """Test decorated async function executes correctly."""
        call_count = 0
        
        @validation_decorator('test_event', EventValidationLevel.MODERATE)
        async def async_test_function(arg1):
            nonlocal call_count
            call_count += 1
            return f"result: {arg1}"
        
        result = await async_test_function('test')
        
        assert result == "result: test"
        assert call_count == 1


class TestValidationContext:
    """Test the validation context manager."""
    
    @pytest.mark.asyncio
    async def test_validation_context_manager(self):
        """Test validation context manager functionality."""
        thread_id = 'test-thread-123'
        run_id = 'run-456'
        
        async with validation_context(thread_id, run_id) as ctx:
            assert ctx['thread_id'] == thread_id
            assert ctx['run_id'] == run_id
            assert 'sequence' in ctx
            assert 'validate_event' in ctx
            
            # Test validation within context
            event = {
                'type': 'agent_started',
                'payload': {
                    'agent_name': 'test_agent',
                    'run_id': run_id,
                    'timestamp': time.time()
                },
                'thread_id': thread_id,
                'timestamp': time.time()
            }
            
            validated_event = await ctx['validate_event'](event)
            assert isinstance(validated_event, ValidatedEvent)


class TestGlobalValidationFunctions:
    """Test global validation control functions."""
    
    def test_enable_global_validation(self):
        """Test enabling global validation."""
        framework = enable_global_validation(EventValidationLevel.STRICT)
        
        assert framework is not None
        assert framework.validation_level == EventValidationLevel.STRICT
    
    def test_get_validation_statistics(self):
        """Test getting validation statistics."""
        # Enable validation first
        enable_global_validation(EventValidationLevel.MODERATE)
        
        stats = get_validation_statistics()
        
        assert 'performance_metrics' in stats
        assert 'circuit_breaker' in stats
        assert 'sequences' in stats
        assert 'validation_level' in stats
        
        # Check structure of performance metrics
        perf_metrics = stats['performance_metrics']
        assert 'total_events' in perf_metrics
        assert 'successful_events' in perf_metrics
        assert 'failed_events' in perf_metrics
        assert 'average_latency_ms' in perf_metrics


class TestIntegrationWithRealComponents:
    """Integration tests with mock versions of real components."""
    
    def setup_method(self):
        """Set up realistic mock components."""
        # Mock WebSocket manager with realistic interface
        self.mock_websocket_manager = Mock()
        self.mock_websocket_manager.send_to_thread = AsyncMock(return_value=True)
        self.mock_websocket_manager.broadcast = AsyncMock(return_value=True)
        self.mock_websocket_manager.connect_user = AsyncMock()
        self.mock_websocket_manager.disconnect_user = AsyncMock()
        
        # Mock execution context with realistic attributes
        self.mock_context = Mock()
        self.mock_context.agent_name = 'actions_agent'
        self.mock_context.run_id = str(uuid.uuid4())
        self.mock_context.thread_id = str(uuid.uuid4())
        self.mock_context.user_id = 'user-123'
    
    @pytest.mark.asyncio
    async def test_end_to_end_validation_flow(self):
        """Test complete end-to-end validation flow."""
        # Enable global validation
        framework = enable_global_validation(EventValidationLevel.MODERATE)
        
        # Create validated WebSocket manager
        validated_manager = create_websocket_manager_validator(
            self.mock_websocket_manager, EventValidationLevel.MODERATE
        )
        
        # Simulate complete agent execution flow
        events = [
            {
                'type': 'agent_started',
                'payload': {
                    'agent_name': self.mock_context.agent_name,
                    'run_id': self.mock_context.run_id,
                    'timestamp': time.time()
                },
                'thread_id': self.mock_context.thread_id,
                'timestamp': time.time()
            },
            {
                'type': 'agent_thinking',
                'payload': {
                    'thought': 'Processing user request for analysis',
                    'agent_name': self.mock_context.agent_name,
                    'timestamp': time.time()
                },
                'thread_id': self.mock_context.thread_id,
                'timestamp': time.time()
            },
            {
                'type': 'tool_executing',
                'payload': {
                    'tool_name': 'web_search',
                    'agent_name': self.mock_context.agent_name,
                    'timestamp': time.time()
                },
                'thread_id': self.mock_context.thread_id,
                'timestamp': time.time()
            },
            {
                'type': 'tool_completed',
                'payload': {
                    'tool_name': 'web_search',
                    'agent_name': self.mock_context.agent_name,
                    'result': {'data': 'search results'},
                    'success': True,
                    'timestamp': time.time()
                },
                'thread_id': self.mock_context.thread_id,
                'timestamp': time.time()
            },
            {
                'type': 'agent_completed',
                'payload': {
                    'agent_name': self.mock_context.agent_name,
                    'run_id': self.mock_context.run_id,
                    'result': {'answer': 'Analysis completed'},
                    'duration_ms': 5000,
                    'timestamp': time.time()
                },
                'thread_id': self.mock_context.thread_id,
                'timestamp': time.time()
            }
        ]
        
        # Send all events through validated manager
        for event in events:
            result = await validated_manager.send_to_thread(
                self.mock_context.thread_id, event
            )
            assert result is True
            time.sleep(0.01)  # Small delay between events
        
        # Check validation statistics
        stats = get_validation_statistics()
        assert stats['performance_metrics']['total_events'] >= 5
        
        # Check sequence completion
        sequence_status = framework.get_sequence_status(self.mock_context.thread_id)
        assert sequence_status is not None
        assert sequence_status['sequence_complete'] is True
        
        # Verify all original methods were called
        assert self.mock_websocket_manager.send_to_thread.call_count >= 5
    
    @pytest.mark.asyncio 
    async def test_validation_with_component_failures(self):
        """Test validation handles component failures gracefully."""
        # Make WebSocket manager fail occasionally
        self.mock_websocket_manager.send_to_thread.side_effect = [
            True,  # First call succeeds
            Exception("WebSocket connection lost"),  # Second call fails
            True,  # Third call succeeds
            True   # Fourth call succeeds
        ]
        
        validated_manager = create_websocket_manager_validator(
            self.mock_websocket_manager, EventValidationLevel.MODERATE
        )
        
        events = [
            {'type': 'agent_started', 'thread_id': 'thread-1'},
            {'type': 'agent_thinking', 'thread_id': 'thread-1'},
            {'type': 'tool_executing', 'thread_id': 'thread-1'},
            {'type': 'agent_completed', 'thread_id': 'thread-1'}
        ]
        
        results = []
        for event in events:
            try:
                result = await validated_manager.send_to_thread('thread-1', event)
                results.append(result)
            except Exception as e:
                results.append(e)
        
        # Should have mix of successes and failures
        assert len(results) == 4
        assert any(r is True for r in results)  # Some successes
        assert any(isinstance(r, Exception) for r in results)  # Some failures
        
        # Validation should still track events
        assert validated_manager.validation_stats['total_events'] >= 4


if __name__ == '__main__':
    pytest.main([__file__, '-v'])