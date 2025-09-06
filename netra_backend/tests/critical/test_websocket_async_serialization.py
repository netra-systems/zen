# REMOVED_SYNTAX_ERROR: '''
# REMOVED_SYNTAX_ERROR: CRITICAL: WebSocket Async Serialization Test Suite
# REMOVED_SYNTAX_ERROR: Tests for Issue #4: Complex Synchronous Serialization Blocking Event Loop

# REMOVED_SYNTAX_ERROR: This comprehensive test suite validates:
    # REMOVED_SYNTAX_ERROR: 1. Serialization performance under load
    # REMOVED_SYNTAX_ERROR: 2. Non-blocking async behavior
    # REMOVED_SYNTAX_ERROR: 3. Concurrent message handling
    # REMOVED_SYNTAX_ERROR: 4. Timeout and retry mechanisms
    # REMOVED_SYNTAX_ERROR: 5. Memory efficiency during serialization
    # REMOVED_SYNTAX_ERROR: """"

    # REMOVED_SYNTAX_ERROR: import asyncio
    # REMOVED_SYNTAX_ERROR: import time
    # REMOVED_SYNTAX_ERROR: import json
    # REMOVED_SYNTAX_ERROR: import pytest
    # REMOVED_SYNTAX_ERROR: from typing import Dict, Any, List
    # REMOVED_SYNTAX_ERROR: import gc
    # REMOVED_SYNTAX_ERROR: import psutil
    # REMOVED_SYNTAX_ERROR: import os
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.agent_registry import AgentRegistry
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.supervisor.user_execution_engine import UserExecutionEngine
    # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

    # REMOVED_SYNTAX_ERROR: from unittest.mock import AsyncMock, Mock

    # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core import WebSocketManager
    # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import DeepAgentState
    # REMOVED_SYNTAX_ERROR: from fastapi import WebSocket


# REMOVED_SYNTAX_ERROR: class TestWebSocketAsyncSerialization:
    # REMOVED_SYNTAX_ERROR: """Critical tests for WebSocket serialization performance and async behavior."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def manager(self):
    # REMOVED_SYNTAX_ERROR: """Create a WebSocket manager instance."""
    # REMOVED_SYNTAX_ERROR: return WebSocketManager()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def real_websocket(self):
    # REMOVED_SYNTAX_ERROR: """Create a mock WebSocket with async send_json."""
    # REMOVED_SYNTAX_ERROR: ws = AsyncMock(spec=WebSocket)
    # REMOVED_SYNTAX_ERROR: ws.send_json = AsyncMock()  # TODO: Use real service instance
    # REMOVED_SYNTAX_ERROR: return ws

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def complex_message(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a complex message that requires heavy serialization."""
    # Create a deeply nested structure that will take time to serialize
    # REMOVED_SYNTAX_ERROR: message = { )
    # REMOVED_SYNTAX_ERROR: "type": "agent_update",
    # REMOVED_SYNTAX_ERROR: "data": {}
    

    # Build a large nested structure
    # REMOVED_SYNTAX_ERROR: current = message["data"]
    # REMOVED_SYNTAX_ERROR: for i in range(100):  # 100 levels deep
    # REMOVED_SYNTAX_ERROR: current["formatted_string"level_{i]"]["nested"]

    # REMOVED_SYNTAX_ERROR: return message

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def large_agent_state(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Create a large DeepAgentState that requires complex serialization."""
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Test request",
    # REMOVED_SYNTAX_ERROR: chat_thread_id="test-thread",
    # REMOVED_SYNTAX_ERROR: user_id="test-user",
    # REMOVED_SYNTAX_ERROR: step_count=0
    

    # Add large amounts of data to various fields
    # REMOVED_SYNTAX_ERROR: state.conversation_history = [ )
    # REMOVED_SYNTAX_ERROR: {"role": "user", "content": "x" * 10000} for _ in range(100)
    
    # REMOVED_SYNTAX_ERROR: state.tool_outputs = [ )
    # REMOVED_SYNTAX_ERROR: {"tool": "formatted_string", "output": "y" * 5000} for i in range(50)
    
    # REMOVED_SYNTAX_ERROR: state.intermediate_results = { )
    # REMOVED_SYNTAX_ERROR: "formatted_string": {"data": "z" * 8000} for i in range(30)
    

    # REMOVED_SYNTAX_ERROR: return state

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_serialization_blocks_event_loop(self, manager, mock_websocket, complex_message):
        # REMOVED_SYNTAX_ERROR: """Test that synchronous serialization blocks the event loop."""
        # This test will FAIL with current implementation

        # Connect a mock websocket
        # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user("test-user", mock_websocket, "test-thread")

        # Track event loop blocking
        # REMOVED_SYNTAX_ERROR: loop_blocked = False
        # REMOVED_SYNTAX_ERROR: block_duration = 0

# REMOVED_SYNTAX_ERROR: async def monitor_loop():
    # REMOVED_SYNTAX_ERROR: """Monitor if the event loop is responsive."""
    # REMOVED_SYNTAX_ERROR: nonlocal loop_blocked, block_duration
    # REMOVED_SYNTAX_ERROR: start = time.perf_counter()
    # REMOVED_SYNTAX_ERROR: while True:
        # REMOVED_SYNTAX_ERROR: check_start = time.perf_counter()
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.001)  # Should complete in ~1ms
        # REMOVED_SYNTAX_ERROR: check_duration = time.perf_counter() - check_start

        # If sleep took more than 10ms, loop was blocked
        # REMOVED_SYNTAX_ERROR: if check_duration > 0.01:
            # REMOVED_SYNTAX_ERROR: loop_blocked = True
            # REMOVED_SYNTAX_ERROR: block_duration = max(block_duration, check_duration)

            # REMOVED_SYNTAX_ERROR: if time.perf_counter() - start > 1:  # Monitor for 1 second
            # REMOVED_SYNTAX_ERROR: break

            # Start monitoring
            # REMOVED_SYNTAX_ERROR: monitor_task = asyncio.create_task(monitor_loop())

            # Send the complex message (will trigger serialization)
            # REMOVED_SYNTAX_ERROR: await manager.send_to_thread("test-thread", complex_message)

            # Wait for monitoring to complete
            # REMOVED_SYNTAX_ERROR: await monitor_task

            # With async implementation, the loop should NOT be blocked significantly
            # Allow some minor blocking but it should be minimal (< 50ms)
            # REMOVED_SYNTAX_ERROR: assert block_duration < 0.05, "formatted_string"

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_concurrent_message_serialization_performance(self, manager, mock_websocket, large_agent_state):
                # REMOVED_SYNTAX_ERROR: """Test that multiple messages can be serialized concurrently without blocking."""
                # This test will FAIL with current implementation

                # Connect multiple websockets
                # REMOVED_SYNTAX_ERROR: connections = []
                # REMOVED_SYNTAX_ERROR: for i in range(10):
                    # REMOVED_SYNTAX_ERROR: ws = AsyncMock(spec=WebSocket)
                    # REMOVED_SYNTAX_ERROR: ws.send_json = AsyncMock()  # TODO: Use real service instance
                    # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user("formatted_string", ws, "formatted_string")
                    # REMOVED_SYNTAX_ERROR: connections.append((conn_id, ws, "formatted_string"))

                    # Measure serialization time for concurrent sends
                    # REMOVED_SYNTAX_ERROR: start_time = time.perf_counter()

                    # Send messages concurrently to all threads
                    # REMOVED_SYNTAX_ERROR: tasks = [ )
                    # REMOVED_SYNTAX_ERROR: manager.send_to_thread(thread_id, large_agent_state)
                    # REMOVED_SYNTAX_ERROR: for _, _, thread_id in connections
                    

                    # REMOVED_SYNTAX_ERROR: await asyncio.gather(*tasks)

                    # REMOVED_SYNTAX_ERROR: total_time = time.perf_counter() - start_time

                    # With async serialization, this should complete quickly (< 1 second)
                    # Current sync implementation will take much longer
                    # REMOVED_SYNTAX_ERROR: assert total_time < 1.0, "formatted_string"

                    # Removed problematic line: @pytest.mark.asyncio
                    # Removed problematic line: async def test_serialization_timeout_handling(self, manager, mock_websocket):
                        # REMOVED_SYNTAX_ERROR: """Test that serialization has proper timeout handling."""
                        # This test will FAIL with current implementation (no timeout)

                        # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user("test-user", mock_websocket, "test-thread")

                        # Create a message that will cause serialization to hang
# REMOVED_SYNTAX_ERROR: class HangingSerializer:
# REMOVED_SYNTAX_ERROR: def model_dump(self, **kwargs):
    # REMOVED_SYNTAX_ERROR: time.sleep(10)  # Simulate hanging serialization
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return {"data": "test"}

    # REMOVED_SYNTAX_ERROR: hanging_message = HangingSerializer()

    # Send should timeout, not hang forever
    # REMOVED_SYNTAX_ERROR: start = time.perf_counter()

    # REMOVED_SYNTAX_ERROR: with pytest.raises(asyncio.TimeoutError):
        # We expect this to timeout in 5 seconds
        # REMOVED_SYNTAX_ERROR: await asyncio.wait_for( )
        # REMOVED_SYNTAX_ERROR: manager.send_to_thread("test-thread", hanging_message),
        # REMOVED_SYNTAX_ERROR: timeout=5.0
        

        # REMOVED_SYNTAX_ERROR: duration = time.perf_counter() - start
        # REMOVED_SYNTAX_ERROR: assert duration < 6, "formatted_string"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_message_send_retry_mechanism(self, manager, mock_websocket):
            # REMOVED_SYNTAX_ERROR: """Test that message sending has retry logic with exponential backoff."""
            # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user("test-user", mock_websocket, "test-thread")

            # Make send_json fail initially, then succeed
            # REMOVED_SYNTAX_ERROR: call_count = 0

# REMOVED_SYNTAX_ERROR: async def mock_send_json(data, timeout=None):
    # REMOVED_SYNTAX_ERROR: nonlocal call_count
    # REMOVED_SYNTAX_ERROR: call_count += 1
    # REMOVED_SYNTAX_ERROR: if call_count < 3:
        # REMOVED_SYNTAX_ERROR: raise asyncio.TimeoutError("WebSocket send timeout")
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return None

        # REMOVED_SYNTAX_ERROR: mock_websocket.send_json = mock_send_json

        # Should retry and eventually succeed with the new implementation
        # REMOVED_SYNTAX_ERROR: result = await manager.send_to_thread("test-thread", {"type": "test"})

        # With retry logic, it should eventually succeed
        # REMOVED_SYNTAX_ERROR: assert result is True, "Message send should succeed after retries"
        # The retry mechanism should have made multiple attempts
        # REMOVED_SYNTAX_ERROR: assert call_count >= 2, "formatted_string"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_memory_efficiency_during_serialization(self, manager, mock_websocket, large_agent_state):
            # REMOVED_SYNTAX_ERROR: """Test that serialization doesn't cause excessive memory usage."""
            # Monitor memory usage during serialization

            # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user("test-user", mock_websocket, "test-thread")

            # Get baseline memory
            # REMOVED_SYNTAX_ERROR: gc.collect()
            # REMOVED_SYNTAX_ERROR: process = psutil.Process(os.getpid())
            # REMOVED_SYNTAX_ERROR: baseline_memory = process.memory_info().rss / 1024 / 1024  # MB

            # Send many large messages
            # REMOVED_SYNTAX_ERROR: for i in range(100):
                # REMOVED_SYNTAX_ERROR: large_agent_state.step_count = i
                # REMOVED_SYNTAX_ERROR: await manager.send_to_thread("test-thread", large_agent_state)

                # Check memory after sending
                # REMOVED_SYNTAX_ERROR: gc.collect()
                # REMOVED_SYNTAX_ERROR: final_memory = process.memory_info().rss / 1024 / 1024  # MB
                # REMOVED_SYNTAX_ERROR: memory_increase = final_memory - baseline_memory

                # Memory increase should be minimal (< 100MB)
                # REMOVED_SYNTAX_ERROR: assert memory_increase < 100, "formatted_string"

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_async_serialization_with_executor(self, manager, mock_websocket, complex_message):
                    # REMOVED_SYNTAX_ERROR: """Test that serialization can be offloaded to thread executor."""
                    # Test the actual async serialization implementation

                    # The manager should already have _serialize_message_safely_async implemented
                    # Let's verify it exists and works correctly
                    # REMOVED_SYNTAX_ERROR: assert hasattr(manager, '_serialize_message_safely_async'), "Manager should have async serialization method"
                    # REMOVED_SYNTAX_ERROR: assert hasattr(manager, '_serialization_executor'), "Manager should have serialization executor"

                    # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user("test-user", mock_websocket, "test-thread")

                    # Track if loop remains responsive
                    # REMOVED_SYNTAX_ERROR: loop_responsive = True

# REMOVED_SYNTAX_ERROR: async def check_responsiveness():
    # REMOVED_SYNTAX_ERROR: nonlocal loop_responsive
    # REMOVED_SYNTAX_ERROR: for _ in range(10):
        # REMOVED_SYNTAX_ERROR: start = time.perf_counter()
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0.001)
        # REMOVED_SYNTAX_ERROR: if time.perf_counter() - start > 0.01:
            # REMOVED_SYNTAX_ERROR: loop_responsive = False
            # REMOVED_SYNTAX_ERROR: break

            # Run responsiveness check while sending message
            # REMOVED_SYNTAX_ERROR: await asyncio.gather( )
            # REMOVED_SYNTAX_ERROR: check_responsiveness(),
            # REMOVED_SYNTAX_ERROR: manager.send_to_thread("test-thread", complex_message)
            

            # REMOVED_SYNTAX_ERROR: assert loop_responsive, "Event loop should remain responsive with async serialization"

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_circuit_breaker_for_failing_connections(self, manager):
                # REMOVED_SYNTAX_ERROR: """Test circuit breaker pattern for consistently failing connections."""
                # Create a websocket that always fails
                # REMOVED_SYNTAX_ERROR: failing_ws = AsyncMock(spec=WebSocket)
                # REMOVED_SYNTAX_ERROR: failing_ws.send_json = AsyncMock(side_effect=Exception("Connection failed"))

                # Use a unique thread to isolate this test
                # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user("failing-user", failing_ws, "failing-thread")

                # Try to send multiple messages
                # REMOVED_SYNTAX_ERROR: failures = 0
                # REMOVED_SYNTAX_ERROR: for i in range(10):
                    # REMOVED_SYNTAX_ERROR: result = await manager.send_to_thread("failing-thread", {"msg": i})
                    # REMOVED_SYNTAX_ERROR: if not result:
                        # REMOVED_SYNTAX_ERROR: failures += 1

                        # Circuit breaker should activate after threshold
                        # With the new implementation, connection should be removed
                        # REMOVED_SYNTAX_ERROR: assert conn_id in manager.failed_connections, "Connection should be marked as failed"

                        # Connection might still be in connections but marked as failed
                        # The key improvement is that it stops trying to send after threshold
                        # REMOVED_SYNTAX_ERROR: assert failures >= 5, "formatted_string"

                        # Removed problematic line: @pytest.mark.asyncio
                        # Removed problematic line: async def test_batch_serialization_optimization(self, manager, mock_websocket):
                            # REMOVED_SYNTAX_ERROR: """Test that multiple messages to same thread can be batched for efficiency."""
                            # This test validates an optimization for the async implementation

                            # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user("test-user", mock_websocket, "test-thread")

                            # Send multiple messages rapidly
                            # REMOVED_SYNTAX_ERROR: messages = [{"type": "update", "data": "formatted_string"

                            # Verify all messages were sent (potentially batched)
                            # REMOVED_SYNTAX_ERROR: call_count = mock_websocket.send_json.call_count
                            # REMOVED_SYNTAX_ERROR: assert call_count > 0, "Messages should have been sent"

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_graceful_degradation_under_load(self, manager):
                                # REMOVED_SYNTAX_ERROR: """Test that system degrades gracefully under extreme load."""
                                # Create many connections
                                # REMOVED_SYNTAX_ERROR: connections = []
                                # REMOVED_SYNTAX_ERROR: for i in range(100):
                                    # REMOVED_SYNTAX_ERROR: ws = AsyncMock(spec=WebSocket)
                                    # REMOVED_SYNTAX_ERROR: ws.send_json = AsyncMock()  # TODO: Use real service instance
                                    # Simulate some slow connections
                                    # REMOVED_SYNTAX_ERROR: if i % 10 == 0:
                                        # REMOVED_SYNTAX_ERROR: ws.send_json = AsyncMock(side_effect=lambda x: None asyncio.sleep(1))

                                        # REMOVED_SYNTAX_ERROR: conn_id = await manager.connect_user("formatted_string", ws, "formatted_string")
                                        # REMOVED_SYNTAX_ERROR: connections.append((conn_id, ws))

                                        # Send many messages concurrently
                                        # REMOVED_SYNTAX_ERROR: start = time.perf_counter()

                                        # REMOVED_SYNTAX_ERROR: tasks = []
                                        # REMOVED_SYNTAX_ERROR: for i in range(1000):
                                            # REMOVED_SYNTAX_ERROR: thread_id = "formatted_string"
                                            # REMOVED_SYNTAX_ERROR: message = {"type": "update", "index": i, "data": "x" * 1000}
                                            # REMOVED_SYNTAX_ERROR: tasks.append(manager.send_to_thread(thread_id, message))

                                            # Should complete without hanging or excessive delays
                                            # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks, return_exceptions=True)

                                            # REMOVED_SYNTAX_ERROR: duration = time.perf_counter() - start

                                            # Count successes and failures
                                            # REMOVED_SYNTAX_ERROR: successes = sum(1 for r in results if r is True or r is None)
                                            # REMOVED_SYNTAX_ERROR: failures = sum(1 for r in results if isinstance(r, Exception))

                                            # System should handle load gracefully
                                            # REMOVED_SYNTAX_ERROR: assert duration < 10, "formatted_string"
                                            # REMOVED_SYNTAX_ERROR: assert successes > failures, "formatted_string"

                                            # Memory should not explode
                                            # REMOVED_SYNTAX_ERROR: process = psutil.Process(os.getpid())
                                            # REMOVED_SYNTAX_ERROR: memory_mb = process.memory_info().rss / 1024 / 1024
                                            # REMOVED_SYNTAX_ERROR: assert memory_mb < 500, "formatted_string"


# REMOVED_SYNTAX_ERROR: class TestWebSocketSerializationCorrectness:
    # REMOVED_SYNTAX_ERROR: """Test correct serialization of various message types."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def manager(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return WebSocketManager()

# REMOVED_SYNTAX_ERROR: def test_serialize_none(self, manager):
    # REMOVED_SYNTAX_ERROR: """Test serialization of None values."""
    # REMOVED_SYNTAX_ERROR: result = manager._serialize_message_safely(None)
    # REMOVED_SYNTAX_ERROR: assert result == {}

# REMOVED_SYNTAX_ERROR: def test_serialize_dict(self, manager):
    # REMOVED_SYNTAX_ERROR: """Test serialization of dict messages."""
    # REMOVED_SYNTAX_ERROR: message = {"type": "test", "data": "value"}
    # REMOVED_SYNTAX_ERROR: result = manager._serialize_message_safely(message)
    # REMOVED_SYNTAX_ERROR: assert result == message

# REMOVED_SYNTAX_ERROR: def test_serialize_deep_agent_state(self, manager):
    # REMOVED_SYNTAX_ERROR: """Test serialization of DeepAgentState."""
    # REMOVED_SYNTAX_ERROR: state = DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="test",
    # REMOVED_SYNTAX_ERROR: chat_thread_id="thread-1",
    # REMOVED_SYNTAX_ERROR: user_id="user-1"
    

    # REMOVED_SYNTAX_ERROR: result = manager._serialize_message_safely(state)

    # REMOVED_SYNTAX_ERROR: assert isinstance(result, dict)
    # REMOVED_SYNTAX_ERROR: assert result.get("user_request") == "test"
    # REMOVED_SYNTAX_ERROR: assert result.get("chat_thread_id") == "thread-1"
    # REMOVED_SYNTAX_ERROR: assert result.get("user_id") == "user-1"

# REMOVED_SYNTAX_ERROR: def test_serialize_pydantic_model(self, manager):
    # REMOVED_SYNTAX_ERROR: """Test serialization of Pydantic models."""
    # REMOVED_SYNTAX_ERROR: from pydantic import BaseModel

# REMOVED_SYNTAX_ERROR: class TestModel(BaseModel):
    # REMOVED_SYNTAX_ERROR: field1: str = "test"
    # REMOVED_SYNTAX_ERROR: field2: int = 42

    # REMOVED_SYNTAX_ERROR: model = TestModel()
    # REMOVED_SYNTAX_ERROR: result = manager._serialize_message_safely(model)

    # REMOVED_SYNTAX_ERROR: assert result == {"field1": "test", "field2": 42}

# REMOVED_SYNTAX_ERROR: def test_serialize_with_to_dict(self, manager):
    # REMOVED_SYNTAX_ERROR: """Test serialization of objects with to_dict method."""
# REMOVED_SYNTAX_ERROR: class CustomObject:
# REMOVED_SYNTAX_ERROR: def to_dict(self):
    # REMOVED_SYNTAX_ERROR: return {"custom": "data"}

    # REMOVED_SYNTAX_ERROR: obj = CustomObject()
    # REMOVED_SYNTAX_ERROR: result = manager._serialize_message_safely(obj)

    # REMOVED_SYNTAX_ERROR: assert result == {"custom": "data"}

# REMOVED_SYNTAX_ERROR: def test_serialize_fallback_to_string(self, manager):
    # REMOVED_SYNTAX_ERROR: """Test fallback serialization to string."""
# REMOVED_SYNTAX_ERROR: class UnserializableObject:

    # REMOVED_SYNTAX_ERROR: obj = UnserializableObject()
    # REMOVED_SYNTAX_ERROR: result = manager._serialize_message_safely(obj)

    # REMOVED_SYNTAX_ERROR: assert "serialization_error" in result
    # REMOVED_SYNTAX_ERROR: assert result["type"] == "UnserializableObject"

# REMOVED_SYNTAX_ERROR: def test_serialize_complex_nested_structure(self, manager):
    # REMOVED_SYNTAX_ERROR: """Test serialization of complex nested structures."""
    # REMOVED_SYNTAX_ERROR: from datetime import datetime
    # REMOVED_SYNTAX_ERROR: from decimal import Decimal

    # REMOVED_SYNTAX_ERROR: complex_obj = { )
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now().isoformat(),
    # REMOVED_SYNTAX_ERROR: "decimal": str(Decimal("123.456")),
    # REMOVED_SYNTAX_ERROR: "nested": { )
    # REMOVED_SYNTAX_ERROR: "list": [1, 2, 3],
    # REMOVED_SYNTAX_ERROR: "dict": {"a": "b"},
    # REMOVED_SYNTAX_ERROR: "tuple": (4, 5, 6)
    
    

    # REMOVED_SYNTAX_ERROR: result = manager._serialize_message_safely(complex_obj)

    # Should handle without errors
    # REMOVED_SYNTAX_ERROR: assert isinstance(result, dict)
    # REMOVED_SYNTAX_ERROR: json.dumps(result)  # Should be JSON serializable


    # REMOVED_SYNTAX_ERROR: @pytest.mark.benchmark
# REMOVED_SYNTAX_ERROR: class TestWebSocketSerializationBenchmarks:
    # REMOVED_SYNTAX_ERROR: """Benchmark tests for serialization performance."""

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def manager(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: return WebSocketManager()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def messages_of_various_sizes(self):
    # REMOVED_SYNTAX_ERROR: """Use real service instance."""
    # TODO: Initialize real service
    # REMOVED_SYNTAX_ERROR: """Generate messages of various sizes for benchmarking."""
    # REMOVED_SYNTAX_ERROR: return [ )
    # REMOVED_SYNTAX_ERROR: {"size": "small", "data": {"msg": "test"}},
    # REMOVED_SYNTAX_ERROR: {"size": "medium", "data": {"msg": "x" * 1000, "items": list(range(100))}},
    # REMOVED_SYNTAX_ERROR: {"size": "large", "data": {"msg": "x" * 10000, "items": list(range(1000))}},
    # REMOVED_SYNTAX_ERROR: {"size": "xlarge", "data": {"formatted_string": "x" * 1000 for i in range(100)}}
    

# REMOVED_SYNTAX_ERROR: def test_serialization_performance(self, manager, messages_of_various_sizes, benchmark):
    # REMOVED_SYNTAX_ERROR: """Benchmark serialization performance for various message sizes."""
    # REMOVED_SYNTAX_ERROR: for message in messages_of_various_sizes:
        # REMOVED_SYNTAX_ERROR: size = message["size"]
        # REMOVED_SYNTAX_ERROR: data = message["data"]

        # Benchmark serialization
        # REMOVED_SYNTAX_ERROR: result = benchmark(manager._serialize_message_safely, data)

        # Ensure result is valid
        # REMOVED_SYNTAX_ERROR: assert isinstance(result, dict)
        # REMOVED_SYNTAX_ERROR: json.dumps(result)  # Should be JSON serializable

        # Performance assertions based on size
        # REMOVED_SYNTAX_ERROR: if size == "small":
            # REMOVED_SYNTAX_ERROR: assert benchmark.stats.mean < 0.001  # < 1ms for small messages
            # REMOVED_SYNTAX_ERROR: elif size == "medium":
                # REMOVED_SYNTAX_ERROR: assert benchmark.stats.mean < 0.01   # < 10ms for medium
                # REMOVED_SYNTAX_ERROR: elif size == "large":
                    # REMOVED_SYNTAX_ERROR: assert benchmark.stats.mean < 0.1    # < 100ms for large
                    # REMOVED_SYNTAX_ERROR: else:  # xlarge
                    # REMOVED_SYNTAX_ERROR: assert benchmark.stats.mean < 1.0    # < 1s for xlarge
                    # REMOVED_SYNTAX_ERROR: pass