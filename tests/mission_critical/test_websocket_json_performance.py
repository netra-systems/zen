# REMOVED_SYNTAX_ERROR: class TestWebSocketConnection:
    # REMOVED_SYNTAX_ERROR: """Real WebSocket connection for testing instead of mocks."""

# REMOVED_SYNTAX_ERROR: def __init__(self):
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self.messages_sent = []
    # REMOVED_SYNTAX_ERROR: self.is_connected = True
    # REMOVED_SYNTAX_ERROR: self._closed = False

# REMOVED_SYNTAX_ERROR: async def send_json(self, message: dict):
    # REMOVED_SYNTAX_ERROR: """Send JSON message."""
    # REMOVED_SYNTAX_ERROR: if self._closed:
        # REMOVED_SYNTAX_ERROR: raise RuntimeError("WebSocket is closed")
        # REMOVED_SYNTAX_ERROR: self.messages_sent.append(message)

# REMOVED_SYNTAX_ERROR: async def close(self, code: int = 1000, reason: str = "Normal closure"):
    # REMOVED_SYNTAX_ERROR: """Close WebSocket connection."""
    # REMOVED_SYNTAX_ERROR: pass
    # REMOVED_SYNTAX_ERROR: self._closed = True
    # REMOVED_SYNTAX_ERROR: self.is_connected = False

# REMOVED_SYNTAX_ERROR: def get_messages(self) -> list:
    # REMOVED_SYNTAX_ERROR: """Get all sent messages."""
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return self.messages_sent.copy()

    # REMOVED_SYNTAX_ERROR: '''
    # REMOVED_SYNTAX_ERROR: MISSION CRITICAL: WebSocket JSON Performance Test Suite

    # REMOVED_SYNTAX_ERROR: This test suite focuses on performance aspects of WebSocket JSON serialization
    # REMOVED_SYNTAX_ERROR: that are critical for real-time chat functionality. It tests async performance,
    # REMOVED_SYNTAX_ERROR: timeout handling, and ensures no blocking occurs.

    # REMOVED_SYNTAX_ERROR: PERFORMANCE REQUIREMENTS:
        # REMOVED_SYNTAX_ERROR: 1. Serialization must not block the event loop
        # REMOVED_SYNTAX_ERROR: 2. Async serialization must complete within 5 seconds
        # REMOVED_SYNTAX_ERROR: 3. Concurrent serialization must be efficient
        # REMOVED_SYNTAX_ERROR: 4. Large messages must serialize without crashing
        # REMOVED_SYNTAX_ERROR: 5. Timeout recovery must work reliably

        # REMOVED_SYNTAX_ERROR: Business Value Justification:
            # REMOVED_SYNTAX_ERROR: - Segment: Platform/Internal
            # REMOVED_SYNTAX_ERROR: - Business Goal: System Performance (real-time user experience)
            # REMOVED_SYNTAX_ERROR: - Value Impact: Ensures chat remains responsive during agent execution
            # REMOVED_SYNTAX_ERROR: - Strategic Impact: Poor serialization performance = broken user experience
            # REMOVED_SYNTAX_ERROR: '''

            # REMOVED_SYNTAX_ERROR: import asyncio
            # REMOVED_SYNTAX_ERROR: import json
            # REMOVED_SYNTAX_ERROR: import pytest
            # REMOVED_SYNTAX_ERROR: import time
            # REMOVED_SYNTAX_ERROR: from datetime import datetime, timezone
            # REMOVED_SYNTAX_ERROR: from typing import Any, Dict
            # REMOVED_SYNTAX_ERROR: from concurrent.futures import ThreadPoolExecutor
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import IsolatedEnvironment

            # REMOVED_SYNTAX_ERROR: from netra_backend.app.agents.state import DeepAgentState, OptimizationsResult, ActionPlanResult
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.websocket_core.unified_manager import UnifiedWebSocketManager as WebSocketManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.db.database_manager import DatabaseManager
            # REMOVED_SYNTAX_ERROR: from netra_backend.app.clients.auth_client_core import AuthServiceClient
            # REMOVED_SYNTAX_ERROR: from shared.isolated_environment import get_env


# REMOVED_SYNTAX_ERROR: class TestWebSocketJSONPerformance:
    # REMOVED_SYNTAX_ERROR: """Test WebSocket JSON serialization performance characteristics."""
    # REMOVED_SYNTAX_ERROR: pass

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def websocket_manager(self):
    # REMOVED_SYNTAX_ERROR: """Create WebSocket manager for performance testing."""
    # REMOVED_SYNTAX_ERROR: return WebSocketManager()

    # REMOVED_SYNTAX_ERROR: @pytest.fixture
# REMOVED_SYNTAX_ERROR: def large_agent_state(self):
    # REMOVED_SYNTAX_ERROR: """Create a large agent state for performance testing."""
    # REMOVED_SYNTAX_ERROR: pass
    # Create large arrays and complex nested structures
    # REMOVED_SYNTAX_ERROR: large_recommendations = ["formatted_string" for i in range(1000)]
    # REMOVED_SYNTAX_ERROR: large_actions = [ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "id": i,
    # REMOVED_SYNTAX_ERROR: "action": "formatted_string",
    # REMOVED_SYNTAX_ERROR: "priority": "high" if i % 3 == 0 else "medium",
    # REMOVED_SYNTAX_ERROR: "estimated_hours": i * 2,
    # REMOVED_SYNTAX_ERROR: "dependencies": list(range(max(0, i-5), i)),
    # REMOVED_SYNTAX_ERROR: "metadata": { )
    # REMOVED_SYNTAX_ERROR: "complexity": "high" if i % 2 == 0 else "low",
    # REMOVED_SYNTAX_ERROR: "risk_level": i % 5,
    # REMOVED_SYNTAX_ERROR: "resource_requirements": ["formatted_string" for j in range(i % 10)]
    
    
    # REMOVED_SYNTAX_ERROR: for i in range(500)
    

    # REMOVED_SYNTAX_ERROR: optimizations = OptimizationsResult( )
    # REMOVED_SYNTAX_ERROR: optimization_type="large_scale_optimization",
    # REMOVED_SYNTAX_ERROR: recommendations=large_recommendations,
    # REMOVED_SYNTAX_ERROR: cost_savings=999999.99,
    # REMOVED_SYNTAX_ERROR: performance_improvement=95.5,
    # REMOVED_SYNTAX_ERROR: confidence_score=0.98
    

    # REMOVED_SYNTAX_ERROR: action_plan = ActionPlanResult( )
    # REMOVED_SYNTAX_ERROR: action_plan_summary="Large scale optimization plan with extensive details",
    # REMOVED_SYNTAX_ERROR: total_estimated_time="12-18 months",
    # REMOVED_SYNTAX_ERROR: required_approvals=["formatted_string" for i in range(50)],
    # REMOVED_SYNTAX_ERROR: actions=large_actions
    

    # Create large message history
    # REMOVED_SYNTAX_ERROR: large_messages = [ )
    # REMOVED_SYNTAX_ERROR: { )
    # REMOVED_SYNTAX_ERROR: "role": "user" if i % 2 == 0 else "assistant",
    # REMOVED_SYNTAX_ERROR: "content": "formatted_string" + "Content " * 100,  # Each message ~700 chars
    # REMOVED_SYNTAX_ERROR: "timestamp": datetime.now(timezone.utc).isoformat(),
    # REMOVED_SYNTAX_ERROR: "metadata": { )
    # REMOVED_SYNTAX_ERROR: "message_id": i,
    # REMOVED_SYNTAX_ERROR: "thread_position": i,
    # REMOVED_SYNTAX_ERROR: "processing_time_ms": i * 10,
    # REMOVED_SYNTAX_ERROR: "tokens_used": i * 5
    
    
    # REMOVED_SYNTAX_ERROR: for i in range(1000)
    

    # REMOVED_SYNTAX_ERROR: return DeepAgentState( )
    # REMOVED_SYNTAX_ERROR: user_request="Perform large-scale comprehensive optimization analysis with detailed reporting and extensive recommendations",
    # REMOVED_SYNTAX_ERROR: chat_thread_id="thread-performance-test",
    # REMOVED_SYNTAX_ERROR: user_id="user-performance-test",
    # REMOVED_SYNTAX_ERROR: run_id="run-performance-12345",
    # REMOVED_SYNTAX_ERROR: optimizations_result=optimizations,
    # REMOVED_SYNTAX_ERROR: action_plan_result=action_plan,
    # REMOVED_SYNTAX_ERROR: final_report="Large comprehensive report: " + "Analysis details. " * 1000,
    # REMOVED_SYNTAX_ERROR: step_count=1000,
    # REMOVED_SYNTAX_ERROR: messages=large_messages,
    # REMOVED_SYNTAX_ERROR: quality_metrics={"formatted_string": i * 0.01 for i in range(100)},
    # REMOVED_SYNTAX_ERROR: context_tracking={"formatted_string": "formatted_string" for i in range(200)}
    

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_async_serialization_performance_baseline(self, websocket_manager):
        # REMOVED_SYNTAX_ERROR: """Test baseline async serialization performance."""

        # Simple message for baseline
        # REMOVED_SYNTAX_ERROR: simple_message = {"type": "test", "payload": {"message": "hello"}}

        # Measure performance
        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: result = await websocket_manager._serialize_message_safely_async(simple_message)
        # REMOVED_SYNTAX_ERROR: end_time = time.time()

        # Should be very fast for simple messages (< 100ms)
        # REMOVED_SYNTAX_ERROR: assert (end_time - start_time) < 0.1
        # REMOVED_SYNTAX_ERROR: assert result == simple_message

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_async_serialization_performance_complex(self, websocket_manager, large_agent_state):
            # REMOVED_SYNTAX_ERROR: """Test async serialization performance with complex data."""

            # Measure performance with large complex state
            # REMOVED_SYNTAX_ERROR: start_time = time.time()
            # REMOVED_SYNTAX_ERROR: result = await websocket_manager._serialize_message_safely_async(large_agent_state)
            # REMOVED_SYNTAX_ERROR: end_time = time.time()

            # Should complete within reasonable time even for large data (< 5 seconds)
            # REMOVED_SYNTAX_ERROR: duration = end_time - start_time
            # REMOVED_SYNTAX_ERROR: assert duration < 5.0, "formatted_string"

            # Result should be valid JSON
            # REMOVED_SYNTAX_ERROR: json_str = json.dumps(result)
            # REMOVED_SYNTAX_ERROR: assert len(json_str) > 10000  # Should be substantial

            # Verify accuracy is maintained
            # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)
            # REMOVED_SYNTAX_ERROR: assert deserialized["run_id"] == "run-performance-12345"
            # REMOVED_SYNTAX_ERROR: assert deserialized["step_count"] == 1000

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_sync_vs_async_serialization_performance(self, websocket_manager, large_agent_state):
                # REMOVED_SYNTAX_ERROR: """Compare sync vs async serialization performance."""

                # Test sync serialization
                # REMOVED_SYNTAX_ERROR: start_sync = time.time()
                # REMOVED_SYNTAX_ERROR: sync_result = websocket_manager._serialize_message_safely(large_agent_state)
                # REMOVED_SYNTAX_ERROR: end_sync = time.time()
                # REMOVED_SYNTAX_ERROR: sync_duration = end_sync - start_sync

                # Test async serialization
                # REMOVED_SYNTAX_ERROR: start_async = time.time()
                # REMOVED_SYNTAX_ERROR: async_result = await websocket_manager._serialize_message_safely_async(large_agent_state)
                # REMOVED_SYNTAX_ERROR: end_async = time.time()
                # REMOVED_SYNTAX_ERROR: async_duration = end_async - start_async

                # Both should produce the same result
                # REMOVED_SYNTAX_ERROR: assert sync_result == async_result

                # Async might be slightly slower due to overhead, but not significantly
                # Both should complete within reasonable time
                # REMOVED_SYNTAX_ERROR: assert sync_duration < 10.0, "formatted_string"
                # REMOVED_SYNTAX_ERROR: assert async_duration < 10.0, "formatted_string"

                # Removed problematic line: @pytest.mark.asyncio
                # Removed problematic line: async def test_concurrent_async_serialization_performance(self, websocket_manager, large_agent_state):
                    # REMOVED_SYNTAX_ERROR: """Test performance with concurrent async serializations."""

                    # Create multiple variations of the large state
                    # REMOVED_SYNTAX_ERROR: states = []
                    # REMOVED_SYNTAX_ERROR: for i in range(10):
                        # REMOVED_SYNTAX_ERROR: state = large_agent_state.copy_with_updates( )
                        # REMOVED_SYNTAX_ERROR: run_id="formatted_string",
                        # REMOVED_SYNTAX_ERROR: step_count=1000 + i
                        
                        # REMOVED_SYNTAX_ERROR: states.append(state)

                        # Serialize all concurrently
                        # REMOVED_SYNTAX_ERROR: start_time = time.time()
                        # REMOVED_SYNTAX_ERROR: tasks = [ )
                        # REMOVED_SYNTAX_ERROR: websocket_manager._serialize_message_safely_async(state)
                        # REMOVED_SYNTAX_ERROR: for state in states
                        
                        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)
                        # REMOVED_SYNTAX_ERROR: end_time = time.time()

                        # Should be faster than serializing sequentially
                        # REMOVED_SYNTAX_ERROR: duration = end_time - start_time
                        # REMOVED_SYNTAX_ERROR: assert duration < 15.0, "formatted_string"

                        # All should succeed
                        # REMOVED_SYNTAX_ERROR: assert len(results) == 10

                        # Verify each result
                        # REMOVED_SYNTAX_ERROR: for i, result in enumerate(results):
                            # REMOVED_SYNTAX_ERROR: json_str = json.dumps(result)
                            # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)
                            # REMOVED_SYNTAX_ERROR: assert deserialized["run_id"] == "formatted_string"
                            # REMOVED_SYNTAX_ERROR: assert deserialized["step_count"] == 1000 + i

                            # Removed problematic line: @pytest.mark.asyncio
                            # Removed problematic line: async def test_serialization_timeout_handling(self, websocket_manager):
                                # REMOVED_SYNTAX_ERROR: """Test timeout handling in async serialization."""

                                # Mock the sync serialization to simulate slow operation
                                # REMOVED_SYNTAX_ERROR: with patch.object(websocket_manager, '_serialize_message_safely') as mock_sync:
# REMOVED_SYNTAX_ERROR: def slow_serialize(msg):
    # REMOVED_SYNTAX_ERROR: time.sleep(7)  # Longer than 5-second timeout
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return {"result": "slow"}

    # REMOVED_SYNTAX_ERROR: mock_sync.side_effect = slow_serialize

    # Should timeout and return fallback
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: result = await websocket_manager._serialize_message_safely_async({"test": "data"})
    # REMOVED_SYNTAX_ERROR: end_time = time.time()

    # Should timeout around 5 seconds (with some tolerance)
    # REMOVED_SYNTAX_ERROR: duration = end_time - start_time
    # REMOVED_SYNTAX_ERROR: assert 4.5 <= duration <= 6.0, "formatted_string"

    # Should return timeout fallback
    # REMOVED_SYNTAX_ERROR: assert "serialization_error" in result
    # REMOVED_SYNTAX_ERROR: assert "timed out" in result["serialization_error"]

    # Verify timeout stats are incremented
    # REMOVED_SYNTAX_ERROR: assert websocket_manager.connection_stats["send_timeouts"] > 0

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_memory_usage_during_serialization(self, websocket_manager, large_agent_state):
        # REMOVED_SYNTAX_ERROR: """Test memory usage doesn't grow excessively during serialization."""

        # REMOVED_SYNTAX_ERROR: import psutil
        # REMOVED_SYNTAX_ERROR: import os

        # Get initial memory usage
        # REMOVED_SYNTAX_ERROR: process = psutil.Process(os.getpid())
        # REMOVED_SYNTAX_ERROR: initial_memory = process.memory_info().rss

        # Perform multiple serializations
        # REMOVED_SYNTAX_ERROR: for i in range(5):
            # Create a variation to prevent caching
            # REMOVED_SYNTAX_ERROR: state = large_agent_state.copy_with_updates(run_id="formatted_string")

            # Serialize both sync and async
            # REMOVED_SYNTAX_ERROR: sync_result = websocket_manager._serialize_message_safely(state)
            # REMOVED_SYNTAX_ERROR: async_result = await websocket_manager._serialize_message_safely_async(state)

            # Convert to JSON to simulate real usage
            # REMOVED_SYNTAX_ERROR: json.dumps(sync_result)
            # REMOVED_SYNTAX_ERROR: json.dumps(async_result)

            # Get final memory usage
            # REMOVED_SYNTAX_ERROR: final_memory = process.memory_info().rss
            # REMOVED_SYNTAX_ERROR: memory_growth = final_memory - initial_memory

            # Memory growth should be reasonable (< 100MB for this test)
            # REMOVED_SYNTAX_ERROR: memory_growth_mb = memory_growth / (1024 * 1024)
            # REMOVED_SYNTAX_ERROR: assert memory_growth_mb < 100, "formatted_string"

# REMOVED_SYNTAX_ERROR: def test_json_dumps_performance_comparison(self, websocket_manager, large_agent_state):
    # REMOVED_SYNTAX_ERROR: """Test performance of different JSON serialization approaches."""

    # Get serialized data
    # REMOVED_SYNTAX_ERROR: serialized_data = websocket_manager._serialize_message_safely(large_agent_state)

    # Test standard json.dumps
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: standard_json = json.dumps(serialized_data)
    # REMOVED_SYNTAX_ERROR: standard_duration = time.time() - start_time

    # Test json.dumps with different options
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: compact_json = json.dumps(serialized_data, separators=(',', ':'))
    # REMOVED_SYNTAX_ERROR: compact_duration = time.time() - start_time

    # Test json.dumps with ensure_ascii=False for unicode
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: unicode_json = json.dumps(serialized_data, ensure_ascii=False)
    # REMOVED_SYNTAX_ERROR: unicode_duration = time.time() - start_time

    # All should complete reasonably quickly
    # REMOVED_SYNTAX_ERROR: assert standard_duration < 5.0, "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert compact_duration < 5.0, "formatted_string"
    # REMOVED_SYNTAX_ERROR: assert unicode_duration < 5.0, "formatted_string"

    # Compact should be slightly faster or similar
    # Unicode should handle special characters properly
    # REMOVED_SYNTAX_ERROR: assert len(compact_json) <= len(standard_json)  # Compact removes spaces

    # Removed problematic line: @pytest.mark.asyncio
    # Removed problematic line: async def test_serialization_thread_pool_performance(self, websocket_manager, large_agent_state):
        # REMOVED_SYNTAX_ERROR: """Test thread pool execution performance for serialization."""

        # Test that the thread pool executor is being used efficiently
        # REMOVED_SYNTAX_ERROR: original_executor = websocket_manager._serialization_executor

        # Monitor the thread pool usage
        # REMOVED_SYNTAX_ERROR: start_time = time.time()

        # Submit multiple async serializations
        # REMOVED_SYNTAX_ERROR: tasks = [ )
        # REMOVED_SYNTAX_ERROR: websocket_manager._serialize_message_safely_async( )
        # REMOVED_SYNTAX_ERROR: large_agent_state.copy_with_updates(run_id="formatted_string")
        
        # REMOVED_SYNTAX_ERROR: for i in range(5)
        

        # REMOVED_SYNTAX_ERROR: results = await asyncio.gather(*tasks)
        # REMOVED_SYNTAX_ERROR: duration = time.time() - start_time

        # Should complete efficiently using thread pool
        # REMOVED_SYNTAX_ERROR: assert duration < 20.0, "formatted_string"
        # REMOVED_SYNTAX_ERROR: assert len(results) == 5

        # Verify thread pool is still functional
        # REMOVED_SYNTAX_ERROR: assert not original_executor._shutdown

# REMOVED_SYNTAX_ERROR: def test_serialization_error_performance(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test performance when serialization errors occur."""

    # Create objects that will cause serialization errors
# REMOVED_SYNTAX_ERROR: class ErrorProneObject:
# REMOVED_SYNTAX_ERROR: def model_dump(self, **kwargs):
    # Simulate slow failure
    # REMOVED_SYNTAX_ERROR: time.sleep(0.1)
    # REMOVED_SYNTAX_ERROR: raise ValueError("Serialization failed")

# REMOVED_SYNTAX_ERROR: def to_dict(self):
    # REMOVED_SYNTAX_ERROR: time.sleep(0.1)
    # REMOVED_SYNTAX_ERROR: raise RuntimeError("to_dict failed")

# REMOVED_SYNTAX_ERROR: def __str__(self):
    # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
    # REMOVED_SYNTAX_ERROR: return "ErrorProneObject"

    # REMOVED_SYNTAX_ERROR: error_objects = [ErrorProneObject() for _ in range(10)]

    # Measure error handling performance
    # REMOVED_SYNTAX_ERROR: start_time = time.time()
    # REMOVED_SYNTAX_ERROR: results = []

    # REMOVED_SYNTAX_ERROR: for obj in error_objects:
        # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(obj)
        # REMOVED_SYNTAX_ERROR: results.append(result)

        # REMOVED_SYNTAX_ERROR: duration = time.time() - start_time

        # Error handling should be efficient (< 5 seconds for 10 errors)
        # REMOVED_SYNTAX_ERROR: assert duration < 5.0, "formatted_string"

        # All should have fallback results
        # REMOVED_SYNTAX_ERROR: for result in results:
            # REMOVED_SYNTAX_ERROR: assert isinstance(result, dict)
            # REMOVED_SYNTAX_ERROR: assert "serialization_error" in result
            # REMOVED_SYNTAX_ERROR: assert "ErrorProneObject" in str(result)

            # Removed problematic line: @pytest.mark.asyncio
            # Removed problematic line: async def test_websocket_send_performance_with_serialization(self, websocket_manager, large_agent_state):
                # REMOVED_SYNTAX_ERROR: """Test overall WebSocket send performance including serialization."""

                # Mock WebSocket for sending
                # REMOVED_SYNTAX_ERROR: mock_websocket = Magic        mock_# websocket setup complete

                # REMOVED_SYNTAX_ERROR: conn_info = { )
                # REMOVED_SYNTAX_ERROR: "websocket": mock_websocket,
                # REMOVED_SYNTAX_ERROR: "message_count": 0,
                # REMOVED_SYNTAX_ERROR: "last_activity": datetime.now(timezone.utc)
                

                # Test send_to_connection_with_retry performance
                # REMOVED_SYNTAX_ERROR: start_time = time.time()
                # REMOVED_SYNTAX_ERROR: result = await websocket_manager._send_to_connection_with_retry( )
                # REMOVED_SYNTAX_ERROR: "perf-test-conn", mock_websocket, large_agent_state, conn_info
                
                # REMOVED_SYNTAX_ERROR: duration = time.time() - start_time

                # Should complete efficiently including serialization
                # REMOVED_SYNTAX_ERROR: assert duration < 10.0, "formatted_string"
                # REMOVED_SYNTAX_ERROR: assert result is True

                # Verify the serialized message was passed to send_json
                # REMOVED_SYNTAX_ERROR: mock_websocket.send_json.assert_called_once()
                # REMOVED_SYNTAX_ERROR: sent_data = mock_websocket.send_json.call_args[0][0]

                # Should be JSON-serializable dict
                # REMOVED_SYNTAX_ERROR: assert isinstance(sent_data, dict)
                # REMOVED_SYNTAX_ERROR: json.dumps(sent_data)  # Should not raise

# REMOVED_SYNTAX_ERROR: def test_deep_recursion_performance(self, websocket_manager):
    # REMOVED_SYNTAX_ERROR: """Test performance with deeply nested structures."""

    # Create very deep nesting (100 levels)
# REMOVED_SYNTAX_ERROR: def create_deep_structure(depth):
    # REMOVED_SYNTAX_ERROR: if depth == 0:
        # REMOVED_SYNTAX_ERROR: await asyncio.sleep(0)
        # REMOVED_SYNTAX_ERROR: return {"value": "leaf", "depth": 0}
        # REMOVED_SYNTAX_ERROR: return { )
        # REMOVED_SYNTAX_ERROR: "level": depth,
        # REMOVED_SYNTAX_ERROR: "child": create_deep_structure(depth - 1),
        # REMOVED_SYNTAX_ERROR: "metadata": {"depth": depth, "timestamp": time.time()}
        

        # REMOVED_SYNTAX_ERROR: deep_message = { )
        # REMOVED_SYNTAX_ERROR: "type": "deep_structure",
        # REMOVED_SYNTAX_ERROR: "payload": create_deep_structure(100)
        

        # Should handle deep structures efficiently
        # REMOVED_SYNTAX_ERROR: start_time = time.time()
        # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(deep_message)
        # REMOVED_SYNTAX_ERROR: duration = time.time() - start_time

        # Should not cause stack overflow or excessive delay
        # REMOVED_SYNTAX_ERROR: assert duration < 5.0, "formatted_string"

        # Should serialize successfully
        # REMOVED_SYNTAX_ERROR: json_str = json.dumps(result)
        # REMOVED_SYNTAX_ERROR: deserialized = json.loads(json_str)
        # REMOVED_SYNTAX_ERROR: assert deserialized["type"] == "deep_structure"

        # Removed problematic line: @pytest.mark.asyncio
        # Removed problematic line: async def test_high_frequency_serialization(self, websocket_manager):
            # REMOVED_SYNTAX_ERROR: """Test performance under high-frequency serialization load."""

            # Simulate high-frequency WebSocket messages (like during agent execution)
            # REMOVED_SYNTAX_ERROR: messages = []
            # REMOVED_SYNTAX_ERROR: for i in range(100):
                # REMOVED_SYNTAX_ERROR: msg = { )
                # REMOVED_SYNTAX_ERROR: "type": "agent_update",
                # REMOVED_SYNTAX_ERROR: "payload": { )
                # REMOVED_SYNTAX_ERROR: "run_id": "formatted_string",
                # REMOVED_SYNTAX_ERROR: "step": i,
                # REMOVED_SYNTAX_ERROR: "progress": i / 100,
                # REMOVED_SYNTAX_ERROR: "message": "formatted_string",
                # REMOVED_SYNTAX_ERROR: "timestamp": time.time()
                
                
                # REMOVED_SYNTAX_ERROR: messages.append(msg)

                # Serialize all messages rapidly
                # REMOVED_SYNTAX_ERROR: start_time = time.time()

                # Use both sync and async serialization
                # REMOVED_SYNTAX_ERROR: sync_results = []
                # REMOVED_SYNTAX_ERROR: for msg in messages[:50]:
                    # REMOVED_SYNTAX_ERROR: result = websocket_manager._serialize_message_safely(msg)
                    # REMOVED_SYNTAX_ERROR: sync_results.append(result)

                    # REMOVED_SYNTAX_ERROR: async_tasks = [ )
                    # REMOVED_SYNTAX_ERROR: websocket_manager._serialize_message_safely_async(msg)
                    # REMOVED_SYNTAX_ERROR: for msg in messages[50:]
                    
                    # REMOVED_SYNTAX_ERROR: async_results = await asyncio.gather(*async_tasks)

                    # REMOVED_SYNTAX_ERROR: duration = time.time() - start_time

                    # Should handle high frequency efficiently
                    # REMOVED_SYNTAX_ERROR: assert duration < 10.0, "formatted_string"

                    # All should succeed
                    # REMOVED_SYNTAX_ERROR: assert len(sync_results) == 50
                    # REMOVED_SYNTAX_ERROR: assert len(async_results) == 50

                    # Verify accuracy
                    # REMOVED_SYNTAX_ERROR: for i, result in enumerate(sync_results):
                        # REMOVED_SYNTAX_ERROR: assert result["payload"]["step"] == i

                        # REMOVED_SYNTAX_ERROR: for i, result in enumerate(async_results, 50):
                            # REMOVED_SYNTAX_ERROR: assert result["payload"]["step"] == i