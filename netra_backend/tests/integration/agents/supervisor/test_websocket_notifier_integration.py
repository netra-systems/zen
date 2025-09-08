"""
Integration Tests for WebSocketNotifier (DEPRECATED)

Tests WebSocketNotifier with real WebSocket connections and event validation.
These tests ensure the deprecated component works properly during migration period.

Business Value: Validates real-time user feedback works under realistic conditions
"""

import asyncio
import pytest
import warnings
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

from netra_backend.app.agents.supervisor.websocket_notifier import WebSocketNotifier
from netra_backend.app.agents.supervisor.execution_context import AgentExecutionContext
from test_framework.ssot.websocket import create_test_websocket_manager


class TestWebSocketNotifierIntegration:
    """Integration tests for WebSocketNotifier with real WebSocket components."""

    @pytest.fixture
    async def test_websocket_manager(self):
        """Create test WebSocket manager for integration testing."""
        return await create_test_websocket_manager()

    @pytest.fixture
    def websocket_notifier(self, test_websocket_manager):
        """WebSocketNotifier with real WebSocket manager."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")  # Suppress deprecation warnings for tests
            return WebSocketNotifier(test_websocket_manager)

    @pytest.fixture
    def sample_context(self):
        """Sample agent execution context for integration tests."""
        return AgentExecutionContext(
            agent_name="integration_test_agent",
            run_id=uuid4(),
            thread_id=f"integration-thread-{uuid4()}",
            user_id="integration-test-user",
            correlation_id=f"integration-correlation-{uuid4()}"
        )

    @pytest.mark.asyncio
    async def test_real_websocket_event_delivery(self, websocket_notifier, sample_context, test_websocket_manager):
        """Test event delivery through real WebSocket manager."""
        # Setup message capture
        sent_messages = []
        
        async def capture_messages(thread_id, message):
            sent_messages.append({'thread_id': thread_id, 'message': message})
            return True
        
        test_websocket_manager.send_to_thread.side_effect = capture_messages
        
        # Send various events
        await websocket_notifier.send_agent_started(sample_context)
        await websocket_notifier.send_agent_thinking(
            sample_context, 
            "Analyzing integration test scenario",
            step_number=1,
            progress_percentage=25.0
        )
        await websocket_notifier.send_tool_executing(
            sample_context,
            "integration_test_tool",
            tool_purpose="Validate WebSocket integration"
        )
        await websocket_notifier.send_tool_completed(
            sample_context,
            "integration_test_tool",
            {"status": "success", "processed_items": 42}
        )
        await websocket_notifier.send_agent_completed(
            sample_context,
            {"result": "Integration test completed"},
            1500
        )
        
        # Verify all messages were captured
        assert len(sent_messages) == 5
        
        # Verify message types and thread targeting
        message_types = [msg['message']['type'] for msg in sent_messages]
        expected_types = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        assert message_types == expected_types
        
        # Verify all messages targeted correct thread
        thread_ids = [msg['thread_id'] for msg in sent_messages]
        assert all(tid == sample_context.thread_id for tid in thread_ids)

    @pytest.mark.asyncio
    async def test_websocket_connection_failure_resilience(self, sample_context):
        """Test resilience when WebSocket connection fails."""
        # Create failing WebSocket manager
        failing_manager = AsyncMock()
        failing_manager.send_to_thread.side_effect = Exception("Connection failed")
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            notifier = WebSocketNotifier(failing_manager)
        
        # Events should not raise exceptions despite WebSocket failures
        await notifier.send_agent_started(sample_context)
        await notifier.send_agent_thinking(sample_context, "test thought")
        await notifier.send_tool_executing(sample_context, "test_tool")
        await notifier.send_agent_completed(sample_context)
        
        # Verify attempts were made
        assert failing_manager.send_to_thread.call_count >= 4

    @pytest.mark.asyncio
    async def test_concurrent_event_delivery(self, websocket_notifier, test_websocket_manager):
        """Test concurrent event delivery to multiple threads."""
        sent_messages = []
        
        async def capture_concurrent_messages(thread_id, message):
            await asyncio.sleep(0.01)  # Simulate network delay
            sent_messages.append({'thread_id': thread_id, 'message': message, 'type': message.get('type')})
            return True
        
        test_websocket_manager.send_to_thread.side_effect = capture_concurrent_messages
        
        # Create multiple contexts for concurrent testing
        contexts = []
        for i in range(5):
            context = AgentExecutionContext(
                agent_name=f"concurrent_agent_{i}",
                run_id=uuid4(),
                thread_id=f"concurrent-thread-{i}",
                user_id=f"concurrent-user-{i}",
                correlation_id=f"concurrent-correlation-{i}"
            )
            contexts.append(context)
        
        # Send events concurrently
        tasks = []
        for i, context in enumerate(contexts):
            tasks.extend([
                websocket_notifier.send_agent_started(context),
                websocket_notifier.send_agent_thinking(context, f"Concurrent thought {i}"),
                websocket_notifier.send_agent_completed(context, {"result": f"Concurrent result {i}"}, 100)
            ])
        
        await asyncio.gather(*tasks)
        
        # Verify all messages were delivered
        assert len(sent_messages) == 15  # 5 contexts * 3 events each
        
        # Verify thread isolation
        thread_message_counts = {}
        for msg in sent_messages:
            thread_id = msg['thread_id']
            thread_message_counts[thread_id] = thread_message_counts.get(thread_id, 0) + 1
        
        # Each thread should have exactly 3 messages
        assert all(count == 3 for count in thread_message_counts.values())
        assert len(thread_message_counts) == 5  # 5 different threads

    @pytest.mark.asyncio
    async def test_event_ordering_guarantee(self, websocket_notifier, sample_context, test_websocket_manager):
        """Test that events are delivered in the correct order."""
        delivered_messages = []
        
        async def track_message_order(thread_id, message):
            delivered_messages.append({
                'type': message.get('type'),
                'timestamp': message.get('payload', {}).get('timestamp'),
                'thread_id': thread_id
            })
            return True
        
        test_websocket_manager.send_to_thread.side_effect = track_message_order
        
        # Send events in specific order with small delays
        await websocket_notifier.send_agent_started(sample_context)
        await asyncio.sleep(0.001)
        
        await websocket_notifier.send_agent_thinking(sample_context, "Step 1")
        await asyncio.sleep(0.001)
        
        await websocket_notifier.send_tool_executing(sample_context, "tool1")
        await asyncio.sleep(0.001)
        
        await websocket_notifier.send_tool_completed(sample_context, "tool1", {"result": "success"})
        await asyncio.sleep(0.001)
        
        await websocket_notifier.send_agent_completed(sample_context)
        
        # Verify order
        expected_order = ['agent_started', 'agent_thinking', 'tool_executing', 'tool_completed', 'agent_completed']
        actual_order = [msg['type'] for msg in delivered_messages]
        assert actual_order == expected_order
        
        # Verify timestamps are increasing (events sent in order)
        timestamps = [msg['timestamp'] for msg in delivered_messages if msg['timestamp']]
        assert all(timestamps[i] <= timestamps[i+1] for i in range(len(timestamps)-1))

    @pytest.mark.asyncio
    async def test_critical_event_retry_integration(self, sample_context):
        """Test critical event retry mechanism with real async behavior."""
        retry_attempts = []
        success_on_attempt = 3  # Succeed on 3rd attempt
        
        async def track_retry_attempts(thread_id, message):
            attempt = len(retry_attempts) + 1
            retry_attempts.append({
                'attempt': attempt,
                'thread_id': thread_id,
                'message_type': message.get('type'),
                'timestamp': asyncio.get_event_loop().time()
            })
            
            # Fail first few attempts, succeed later
            return attempt >= success_on_attempt
        
        failing_manager = AsyncMock()
        failing_manager.send_to_thread.side_effect = track_retry_attempts
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            notifier = WebSocketNotifier(failing_manager)
        
        # Send critical event (agent_started)
        await notifier.send_agent_started(sample_context)
        
        # Allow time for retries
        await asyncio.sleep(0.5)
        
        # Verify multiple attempts were made
        assert len(retry_attempts) >= success_on_attempt
        
        # Verify retry timing (should have delays between attempts)
        if len(retry_attempts) > 1:
            time_between_attempts = retry_attempts[1]['timestamp'] - retry_attempts[0]['timestamp']
            assert time_between_attempts >= 0.05  # At least some delay

    @pytest.mark.asyncio
    async def test_event_queue_processing_integration(self, sample_context):
        """Test event queue processing with realistic failure scenarios."""
        processed_events = []
        failure_count = 0
        
        async def intermittent_failures(thread_id, message):
            nonlocal failure_count
            failure_count += 1
            
            # Fail every other attempt initially
            if failure_count <= 4 and failure_count % 2 == 1:
                return False  # Simulate intermittent failures
            
            processed_events.append({
                'thread_id': thread_id,
                'type': message.get('type'),
                'attempt': failure_count
            })
            return True
        
        unreliable_manager = AsyncMock()
        unreliable_manager.send_to_thread.side_effect = intermittent_failures
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            notifier = WebSocketNotifier(unreliable_manager)
        
        # Send multiple critical events
        await notifier.send_agent_started(sample_context)
        await notifier.send_tool_executing(sample_context, "test_tool")
        
        # Wait for queue processing and retries
        await asyncio.sleep(0.3)
        
        # Verify events eventually succeeded
        assert len(processed_events) >= 2  # At least the 2 events sent
        
        # Verify some retry attempts were made
        assert failure_count > 2  # Should have had some failures

    @pytest.mark.asyncio
    async def test_performance_under_load(self, websocket_notifier, test_websocket_manager):
        """Test performance characteristics under load."""
        import time
        
        message_count = 0
        start_time = time.time()
        
        async def count_messages(thread_id, message):
            nonlocal message_count
            message_count += 1
            # Simulate small processing delay
            await asyncio.sleep(0.001)
            return True
        
        test_websocket_manager.send_to_thread.side_effect = count_messages
        
        # Create load test scenario
        num_agents = 20
        events_per_agent = 10
        
        contexts = []
        for i in range(num_agents):
            context = AgentExecutionContext(
                agent_name=f"load_test_agent_{i}",
                run_id=uuid4(),
                thread_id=f"load-thread-{i}",
                user_id=f"load-user-{i}"
            )
            contexts.append(context)
        
        # Generate load concurrently
        tasks = []
        for context in contexts:
            for event_num in range(events_per_agent):
                # Mix different event types
                if event_num % 4 == 0:
                    task = websocket_notifier.send_agent_started(context)
                elif event_num % 4 == 1:
                    task = websocket_notifier.send_agent_thinking(context, f"Thought {event_num}")
                elif event_num % 4 == 2:
                    task = websocket_notifier.send_tool_executing(context, f"tool_{event_num}")
                else:
                    task = websocket_notifier.send_agent_completed(context)
                
                tasks.append(task)
        
        # Execute all tasks concurrently
        await asyncio.gather(*tasks)
        
        # Wait for all processing to complete
        await asyncio.sleep(0.1)
        
        total_time = time.time() - start_time
        expected_events = num_agents * events_per_agent
        
        # Performance verification
        assert message_count >= expected_events * 0.9  # Allow some message loss under load
        assert total_time < 5.0  # Should complete within reasonable time
        
        # Calculate throughput
        throughput = message_count / total_time
        assert throughput > 50  # At least 50 messages per second

    @pytest.mark.asyncio
    async def test_websocket_manager_broadcast_fallback(self, sample_context):
        """Test broadcast fallback when thread-specific delivery fails."""
        broadcast_calls = []
        thread_calls = []
        
        async def track_thread_calls(thread_id, message):
            thread_calls.append({'thread_id': thread_id, 'message': message})
            return False  # Simulate failure
        
        async def track_broadcast_calls(message):
            broadcast_calls.append(message)
            return True
        
        fallback_manager = AsyncMock()
        fallback_manager.send_to_thread.side_effect = track_thread_calls
        fallback_manager.broadcast.side_effect = track_broadcast_calls
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            notifier = WebSocketNotifier(fallback_manager)
        
        # Send event with None thread_id to trigger broadcast
        await notifier.send_agent_failed(
            agent_id="test-agent",
            error="Test error",
            thread_id=None  # This should trigger broadcast
        )
        
        # Verify broadcast was used
        assert len(broadcast_calls) >= 1

    @pytest.mark.asyncio
    async def test_operation_lifecycle_tracking(self, websocket_notifier, sample_context):
        """Test complete operation lifecycle tracking."""
        # Start operation
        await websocket_notifier.send_agent_started(sample_context)
        
        # Verify operation is tracked
        assert sample_context.thread_id in websocket_notifier.active_operations
        operation = websocket_notifier.active_operations[sample_context.thread_id]
        assert operation['processing'] is True
        assert operation['agent_name'] == sample_context.agent_name
        
        # Send intermediate events
        await websocket_notifier.send_agent_thinking(sample_context, "Processing...")
        await websocket_notifier.send_tool_executing(sample_context, "analysis_tool")
        
        # Verify operation is still active
        assert websocket_notifier.active_operations[sample_context.thread_id]['processing'] is True
        
        # Complete operation
        await websocket_notifier.send_agent_completed(sample_context)
        
        # Verify operation is marked as complete
        assert websocket_notifier.active_operations[sample_context.thread_id]['processing'] is False
        
        # Wait for cleanup (should happen automatically)
        await asyncio.sleep(0.05)

    @pytest.mark.asyncio
    async def test_context_vs_parameter_integration(self, websocket_notifier, test_websocket_manager):
        """Test integration of context-based vs parameter-based method calls."""
        captured_messages = []
        
        async def capture_all_messages(thread_id, message):
            captured_messages.append({
                'thread_id': thread_id,
                'message_type': message.get('type'),
                'payload': message.get('payload', {})
            })
            return True
        
        test_websocket_manager.send_to_thread.side_effect = capture_all_messages
        
        sample_context = AgentExecutionContext(
            agent_name="context_test_agent",
            run_id=uuid4(),
            thread_id="context-thread"
        )
        
        # Context-based calls
        await websocket_notifier.send_agent_registered(
            context=sample_context,
            agent_metadata={"type": "test", "version": "1.0"}
        )
        
        # Parameter-based calls  
        await websocket_notifier.send_agent_registered(
            agent_id="param-agent-id",
            agent_type="parameter_agent", 
            thread_id="parameter-thread",
            agent_metadata={"source": "parameters"}
        )
        
        # Verify both approaches worked
        assert len(captured_messages) == 2
        
        # Context-based message
        context_msg = next(msg for msg in captured_messages if msg['thread_id'] == "context-thread")
        assert context_msg['message_type'] == 'agent_registered'
        assert 'agent_name' in context_msg['payload']
        
        # Parameter-based message
        param_msg = next(msg for msg in captured_messages if msg['thread_id'] == "parameter-thread")
        assert param_msg['message_type'] == 'agent_registered'
        assert 'agent_id' in param_msg['payload']

    @pytest.mark.asyncio
    async def test_error_recovery_integration(self, sample_context):
        """Test error recovery mechanisms in realistic scenarios."""
        recovery_log = []
        connection_restored = False
        
        async def simulate_connection_recovery(thread_id, message):
            nonlocal connection_restored
            recovery_log.append({
                'attempt': len(recovery_log) + 1,
                'thread_id': thread_id,
                'message_type': message.get('type')
            })
            
            # Simulate connection restored after 3 attempts
            if len(recovery_log) >= 3:
                connection_restored = True
                return True
            return False
        
        recovering_manager = AsyncMock()
        recovering_manager.send_to_thread.side_effect = simulate_connection_recovery
        
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            notifier = WebSocketNotifier(recovering_manager)
        
        # Send events during "outage"
        await notifier.send_agent_started(sample_context)
        await notifier.send_tool_executing(sample_context, "recovery_test_tool")
        
        # Wait for recovery attempts
        await asyncio.sleep(0.2)
        
        # Verify recovery was attempted
        assert len(recovery_log) >= 3
        assert connection_restored is True
        
        # Verify events were eventually delivered
        delivered_event_types = [log['message_type'] for log in recovery_log]
        assert 'agent_started' in delivered_event_types