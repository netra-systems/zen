"""Unit tests for WebSocketNotifier legacy patterns and edge cases.

Business Value Justification (BVJ):
- Segment: All (Free, Early, Mid, Enterprise)
- Business Goal: Ensure legacy WebSocket patterns handle edge cases gracefully
- Value Impact: Prevent WebSocket failures during agent execution
- Strategic Impact: Robust error handling maintains user experience during migration

These unit tests validate edge cases, error conditions, and legacy compatibility.
"""

import pytest
import asyncio
import uuid
import time
from unittest.mock import Mock, AsyncMock, patch
from collections import deque
from datetime import datetime, timezone

from netra_backend.app.services.agent_websocket_bridge import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext


class TestWebSocketNotifierLegacyUnit:
    """Unit tests for WebSocketNotifier edge cases and legacy patterns."""
    
    @pytest.fixture
    def mock_failing_websocket_manager(self):
        """Mock WebSocket manager that fails sporadically."""
        manager = AsyncMock()
        
        # Track call count for failure simulation
        call_count = 0
        
        async def sporadic_failure(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            # Fail every 3rd call
            if call_count % 3 == 0:
                raise Exception("Simulated WebSocket failure")
            return call_count % 2 == 1  # Return True/False alternately
        
        manager.send_to_thread.side_effect = sporadic_failure
        manager.broadcast.side_effect = sporadic_failure
        return manager
    
    @pytest.fixture
    def context_with_unicode(self):
        """Test context with unicode characters."""
        return AgentExecutionContext(
            agent_name="测试代理",  # Chinese characters
            run_id=str(uuid.uuid4()),
            thread_id="thread-🚀-测试",  # Mixed unicode
            user_id="user-ñame",  # Spanish characters
            correlation_id="corr-🔗-id"  # Emoji
        )
    
    @pytest.fixture
    def context_with_long_strings(self):
        """Test context with very long strings."""
        return AgentExecutionContext(
            agent_name="a" * 1000,  # Very long agent name
            run_id=str(uuid.uuid4()),
            thread_id="thread-" + "x" * 500,  # Long thread ID
            user_id="user-" + "y" * 200,  # Long user ID
            correlation_id="z" * 300  # Long correlation ID
        )
    
    async def test_websocket_notifier_with_none_manager(self):
        """Test WebSocketNotifier handles None manager gracefully."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(None, test_mode=True)
        
        try:
            # Verify initialization with None manager
            assert notifier.websocket_manager is None
            assert isinstance(notifier.event_queue, deque)
            assert isinstance(notifier.delivery_confirmations, dict)
            assert isinstance(notifier.active_operations, dict)
        finally:
            # Cleanup
            await notifier.shutdown()
    
    @pytest.mark.asyncio
    async def test_send_operations_with_none_manager(self, context_with_unicode):
        """Test all send operations handle None manager gracefully."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(None, test_mode=True)
        
        try:
            # All operations should complete without error
            await notifier.send_agent_started(context_with_unicode)
            await notifier.send_agent_thinking(
                context_with_unicode, 
                "Unicode思考: Processing 🎯 data"
            )
            await notifier.send_tool_executing(
                context_with_unicode, 
                "unicode_tool_🔧"
            )
            await notifier.send_agent_completed(
                context_with_unicode, 
                {"result": "Unicode成功 ✅"}
            )
            await notifier.send_agent_failed(
                context_with_unicode,
                error_message="Unicode错误 ❌"
            )
            
            # Operations tracking should still work
            assert context_with_unicode.thread_id in notifier.active_operations
        finally:
            # Cleanup
            await notifier.shutdown()
    
    @pytest.mark.asyncio
    async def test_unicode_message_handling(self, context_with_unicode):
        """Test handling of unicode characters in messages."""
        import warnings
        mock_manager = AsyncMock()
        mock_manager.send_to_thread.return_value = True
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_manager, test_mode=True)
        
        # Send unicode message
        await notifier.send_agent_thinking(
            context_with_unicode,
            thought="正在分析数据 📊 using AI 🤖",
            current_operation="unicode_processing_🌍"
        )
        
        # Verify call was made
        mock_manager.send_to_thread.assert_called_once()
        call_args = mock_manager.send_to_thread.call_args[0]
        
        # Verify unicode is preserved in payload
        message_data = call_args[1]
        payload = message_data['payload']
        assert payload['thought'] == "正在分析数据 📊 using AI 🤖"
        assert payload['current_operation'] == "unicode_processing_🌍"
        
        # Cleanup
        await notifier.shutdown()
    
    @pytest.mark.asyncio
    async def test_large_message_handling(self, context_with_long_strings):
        """Test handling of very large messages."""
        import warnings
        mock_manager = AsyncMock()
        mock_manager.send_to_thread.return_value = True
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_manager)
        
        # Send large message
        large_thought = "This is a very large thought: " + "x" * 5000
        large_result = {"data": "y" * 10000, "analysis": "z" * 3000}
        
        await notifier.send_agent_thinking(context_with_long_strings, large_thought)
        await notifier.send_agent_completed(context_with_long_strings, large_result)
        
        # Verify calls were made despite large payloads
        assert mock_manager.send_to_thread.call_count == 2
    
    @pytest.mark.asyncio
    async def test_concurrent_operations_on_same_thread(self, mock_failing_websocket_manager):
        """Test concurrent operations on the same thread ID."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_failing_websocket_manager)
        
        # Create multiple contexts with same thread ID
        thread_id = "shared-thread-123"
        contexts = [
            AgentExecutionContext(
                agent_name=f"agent_{i}",
                run_id=str(uuid.uuid4()),
                thread_id=thread_id,
                user_id=f"user_{i}"
            )
            for i in range(5)
        ]
        
        # Send concurrent notifications
        tasks = []
        for i, context in enumerate(contexts):
            tasks.append(notifier.send_agent_started(context))
            tasks.append(notifier.send_agent_thinking(context, f"Thought {i}"))
            tasks.append(notifier.send_agent_completed(context, f"Result {i}"))
        
        # Execute concurrently
        await asyncio.gather(*tasks, return_exceptions=True)
        
        # Verify thread tracking handles concurrent updates
        assert thread_id in notifier.active_operations
        operation = notifier.active_operations[thread_id]
        assert operation['event_count'] > 0
    
    def test_error_severity_edge_cases(self, mock_failing_websocket_manager):
        """Test error severity determination with edge cases."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_failing_websocket_manager)
        
        # Test with None values
        assert notifier._determine_error_severity(None, None) == "medium"
        assert notifier._determine_error_severity("", "") == "medium"
        
        # Test with empty strings
        assert notifier._determine_error_severity("", "error message") == "medium"
        assert notifier._determine_error_severity("error_type", "") == "medium"
        
        # Test case insensitive matching
        assert notifier._determine_error_severity("DATABASE", "CONNECTION FAILED") == "critical"
        assert notifier._determine_error_severity("Authentication", "Invalid Token") == "critical"
        
        # Test partial matching
        assert notifier._determine_error_severity("connection_timeout", "timeout occurred") == "high"
        assert notifier._determine_error_severity("rate_limited", "limit exceeded") == "high"
    
    def test_recovery_suggestions_edge_cases(self, mock_failing_websocket_manager):
        """Test recovery suggestion generation with edge cases."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_failing_websocket_manager)
        
        # Test with None/empty inputs
        suggestions = notifier._generate_default_recovery_suggestions(None, None)
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        suggestions = notifier._generate_default_recovery_suggestions("", "")
        assert isinstance(suggestions, list)
        assert len(suggestions) > 0
        
        # Test with unknown error types
        suggestions = notifier._generate_default_recovery_suggestions("unknown_error", "mysterious failure")
        assert isinstance(suggestions, list)
        assert any("try again" in s.lower() for s in suggestions)
    
    def test_user_friendly_message_edge_cases(self, mock_failing_websocket_manager):
        """Test user-friendly message generation with edge cases."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_failing_websocket_manager)
        
        # Test with None agent name
        message = notifier._generate_user_friendly_error_message("timeout", "timeout", None)
        assert "agent" in message.lower()  # Should still mention agent generically
        
        # Test with empty strings
        message = notifier._generate_user_friendly_error_message("", "", "")
        assert isinstance(message, str)
        assert len(message) > 0
        
        # Test with very long agent name
        long_agent_name = "very_long_agent_name_" + "x" * 100
        message = notifier._generate_user_friendly_error_message("timeout", "timeout", long_agent_name)
        assert isinstance(message, str)
        assert len(message) > 0
    
    def test_tool_context_hints_edge_cases(self, mock_failing_websocket_manager):
        """Test tool context hints with edge cases."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_failing_websocket_manager)
        
        # Test with None tool name
        hints = notifier._get_tool_context_hints(None)
        assert hints['category'] == 'general'
        assert hints['expected_duration'] == 'medium'
        
        # Test with empty tool name
        hints = notifier._get_tool_context_hints("")
        assert hints['category'] == 'general'
        
        # Test with numeric tool name
        hints = notifier._get_tool_context_hints("12345")
        assert hints['category'] == 'general'
        
        # Test with special characters
        hints = notifier._get_tool_context_hints("tool_$#@!")
        assert hints['category'] == 'general'
    
    @pytest.mark.asyncio
    async def test_queue_overflow_handling(self, mock_failing_websocket_manager):
        """Test handling of event queue overflow."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_failing_websocket_manager)
        
        # Set small queue size for testing
        notifier.max_queue_size = 5
        
        # Fill queue beyond capacity
        for i in range(10):
            event = {
                'type': f'test_event_{i}',
                'data': f'test_data_{i}',
                'timestamp': time.time()
            }
            notifier.event_queue.append(event)
        
        # Queue should be limited to max size
        assert len(notifier.event_queue) <= notifier.max_queue_size
    
    @pytest.mark.asyncio
    async def test_delivery_confirmation_cleanup(self, mock_failing_websocket_manager):
        """Test cleanup of old delivery confirmations."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_failing_websocket_manager)
        
        # Add old delivery confirmations
        old_timestamp = time.time() - 3600  # 1 hour ago
        recent_timestamp = time.time()
        
        notifier.delivery_confirmations['old_msg'] = old_timestamp
        notifier.delivery_confirmations['recent_msg'] = recent_timestamp
        
        # Trigger cleanup (would normally happen during stats collection)
        stats = await notifier.get_delivery_stats()
        
        # Old confirmations should still exist (cleanup is conservative)
        # This tests that the stats collection doesn't crash with old data
        assert isinstance(stats, dict)
        assert 'delivery_confirmations' in stats
    
    @pytest.mark.asyncio
    async def test_backlog_notification_frequency(self, mock_failing_websocket_manager):
        """Test backlog notification frequency limits."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_failing_websocket_manager)
        
        # Set short backlog interval for testing
        notifier.backlog_notification_interval = 0.1
        
        context = AgentExecutionContext(
            agent_name="test_agent",
            run_id=str(uuid.uuid4()),
            thread_id="test-thread",
            user_id="test-user"
        )
        
        # Send multiple events rapidly
        for i in range(5):
            await notifier.send_agent_thinking(context, f"Thought {i}")
            await asyncio.sleep(0.02)  # Short delay
        
        # Backlog notifications should be rate limited
        backlog_count = len(notifier.backlog_notifications)
        assert backlog_count <= 2  # Should not exceed reasonable limit
    
    def test_timestamp_consistency(self, mock_failing_websocket_manager):
        """Test timestamp consistency across operations."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_failing_websocket_manager)
        
        # Generate multiple timestamps
        timestamps = []
        for i in range(10):
            timestamp = notifier._get_timestamp()
            timestamps.append(timestamp)
            time.sleep(0.001)  # Small delay
        
        # Verify timestamps are increasing
        for i in range(1, len(timestamps)):
            assert timestamps[i] >= timestamps[i-1]
        
        # Verify timestamps are reasonable (within 1 second of now)
        current_time = datetime.now(timezone.utc).timestamp()
        for timestamp in timestamps:
            assert abs(timestamp - current_time) < 1.0
    
    @pytest.mark.asyncio
    async def test_operation_state_transitions(self, mock_failing_websocket_manager):
        """Test operation state transitions under various conditions."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_failing_websocket_manager)
        
        context = AgentExecutionContext(
            agent_name="state_test_agent",
            run_id=str(uuid.uuid4()),
            thread_id="state-test-thread",
            user_id="state-test-user"
        )
        
        # Initial state: no operation
        assert context.thread_id not in notifier.active_operations
        
        # Start operation
        await notifier.send_agent_started(context)
        assert context.thread_id in notifier.active_operations
        assert notifier.active_operations[context.thread_id]['processing'] is True
        
        # Update operation (thinking events)
        initial_count = notifier.active_operations[context.thread_id]['event_count']
        await notifier.send_agent_thinking(context, "Testing state")
        assert notifier.active_operations[context.thread_id]['event_count'] > initial_count
        
        # Complete operation
        await notifier.send_agent_completed(context, {"test": "result"})
        assert notifier.active_operations[context.thread_id]['processing'] is False
        
        # Error operation (should also mark as not processing)
        await notifier.send_agent_started(context)  # Restart
        assert notifier.active_operations[context.thread_id]['processing'] is True
        
        await notifier.send_agent_failed(context, error_message="Test error")
        # After error, operation should be marked complete
        assert context.thread_id in notifier.active_operations
    
    @pytest.mark.asyncio 
    async def test_memory_usage_under_load(self, mock_failing_websocket_manager):
        """Test memory usage doesn't grow excessively under load."""
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            notifier = AgentWebSocketBridge(mock_failing_websocket_manager)
        
        # Create many operations
        contexts = []
        for i in range(100):
            context = AgentExecutionContext(
                agent_name=f"load_agent_{i}",
                run_id=str(uuid.uuid4()),
                thread_id=f"load-thread-{i}",
                user_id=f"load-user-{i}"
            )
            contexts.append(context)
        
        # Send many events
        for context in contexts:
            await notifier.send_agent_started(context)
            await notifier.send_agent_thinking(context, "Load test thinking")
            await notifier.send_agent_completed(context, {"load": "test"})
        
        # Verify memory structures don't grow excessively
        assert len(notifier.active_operations) <= 100
        assert len(notifier.event_queue) <= notifier.max_queue_size
        
        # Cleanup should work
        await notifier.shutdown()
        assert len(notifier.active_operations) == 0
        assert len(notifier.event_queue) == 0