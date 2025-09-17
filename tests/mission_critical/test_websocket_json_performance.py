class TestWebSocketConnection:
    "Real WebSocket connection for testing instead of mocks.""

    def __init__(self):
        pass
        self.messages_sent = []
        self.is_connected = True
        self._closed = False

    async def send_json(self, message: dict):
        ""Send JSON message."
        if self._closed:
        raise RuntimeError("WebSocket is closed)
        self.messages_sent.append(message)

    async def close(self, code: int = 1000, reason: str = Normal closure"):
        "Close WebSocket connection.""
        pass
        self._closed = True
        self.is_connected = False

    async def get_messages(self) -> list:
        ""Get all sent messages."
        await asyncio.sleep(0)
        return self.messages_sent.copy()

        '''
        MISSION CRITICAL: WebSocket JSON Performance Test Suite

        This test suite focuses on performance aspects of WebSocket JSON serialization
        that are critical for real-time chat functionality. It tests async performance,
        timeout handling, and ensures no blocking occurs.

        PERFORMANCE REQUIREMENTS:
        1. Serialization must not block the event loop
        2. Async serialization must complete within 5 seconds
        3. Concurrent serialization must be efficient
        4. Large messages must serialize without crashing
        5. Timeout recovery must work reliably

        Business Value Justification:
        - Segment: Platform/Internal
        - Business Goal: System Performance (real-time user experience)
        - Value Impact: Ensures chat remains responsive during agent execution
        - Strategic Impact: Poor serialization performance = broken user experience
        '''

        import asyncio
        import json
        import pytest
        import time
        from datetime import datetime, timezone
        from typing import Any, Dict
        from concurrent.futures import ThreadPoolExecutor
        from shared.isolated_environment import IsolatedEnvironment

        from netra_backend.app.schemas.agent_models import DeepAgentState
from netra_backend.app.agents.state import OptimizationsResult, ActionPlanResult
from netra_backend.app.websocket_core.websocket_manager import WebSocketManager as WebSocketManager
from netra_backend.app.core.unified_error_handler import UnifiedErrorHandler
from netra_backend.app.db.database_manager import DatabaseManager
from netra_backend.app.clients.auth_client_core import AuthServiceClient
from shared.isolated_environment import get_env


class TestWebSocketJSONPerformance:
    "Test WebSocket JSON serialization performance characteristics.""
    pass

    @pytest.fixture
    def websocket_manager(self):
        ""Create WebSocket manager for performance testing."
        return WebSocketManager()

        @pytest.fixture
    def large_agent_state(self):
        "Create a large agent state for performance testing.""
        pass
    # Create large arrays and complex nested structures
        large_recommendations = [formatted_string" for i in range(1000)]
        large_actions = [
        {
        "id: i,
        action": "formatted_string,
        priority": "high if i % 3 == 0 else medium",
        "estimated_hours: i * 2,
        dependencies": list(range(max(0, i-5), i)),
        "metadata: {
        complexity": "high if i % 2 == 0 else low",
        "risk_level: i % 5,
        resource_requirements": ["formatted_string for j in range(i % 10)]
    
    
        for i in range(500)
    

        optimizations = OptimizationsResult( )
        optimization_type=large_scale_optimization",
        recommendations=large_recommendations,
        cost_savings=999999.99,
        performance_improvement=95.5,
        confidence_score=0.98
    

        action_plan = ActionPlanResult( )
        action_plan_summary="Large scale optimization plan with extensive details,
        total_estimated_time=12-18 months",
        required_approvals=["formatted_string for i in range(50)],
        actions=large_actions
    

    # Create large message history
        large_messages = [
        {
        role": "user if i % 2 == 0 else assistant",
        "content: formatted_string" + "Content  * 100,  # Each message ~700 chars
        timestamp": datetime.now(timezone.utc).isoformat(),
        "metadata: {
        message_id": i,
        "thread_position: i,
        processing_time_ms": i * 10,
        "tokens_used: i * 5
    
    
        for i in range(1000)
    

        return DeepAgentState( )
        user_request=Perform large-scale comprehensive optimization analysis with detailed reporting and extensive recommendations",
        chat_thread_id="thread-performance-test,
        user_id=user-performance-test",
        run_id="run-performance-12345,
        optimizations_result=optimizations,
        action_plan_result=action_plan,
        final_report=Large comprehensive report: " + "Analysis details.  * 1000,
        step_count=1000,
        messages=large_messages,
        quality_metrics={formatted_string": i * 0.01 for i in range(100)},
        context_tracking={"formatted_string: formatted_string" for i in range(200)}
    

@pytest.mark.asyncio
    async def test_async_serialization_performance_baseline(self, websocket_manager):
        "Test baseline async serialization performance.""

        # Simple message for baseline
simple_message = {type": "test, payload": {"message: hello"}}

        # Measure performance
start_time = time.time()
result = await websocket_manager._serialize_message_safely_async(simple_message)
end_time = time.time()

        # Should be very fast for simple messages (< 100ms)
assert (end_time - start_time) < 0.1
assert result == simple_message

@pytest.mark.asyncio
    async def test_async_serialization_performance_complex(self, websocket_manager, large_agent_state):
        "Test async serialization performance with complex data.""

            # Measure performance with large complex state
start_time = time.time()
result = await websocket_manager._serialize_message_safely_async(large_agent_state)
end_time = time.time()

            # Should complete within reasonable time even for large data (< 5 seconds)
duration = end_time - start_time
assert duration < 5.0, formatted_string"

            # Result should be valid JSON
json_str = json.dumps(result)
assert len(json_str) > 10000  # Should be substantial

            # Verify accuracy is maintained
deserialized = json.loads(json_str)
assert deserialized["run_id] == run-performance-12345"
assert deserialized["step_count] == 1000

@pytest.mark.asyncio
    async def test_sync_vs_async_serialization_performance(self, websocket_manager, large_agent_state):
        ""Compare sync vs async serialization performance."

                # Test sync serialization
start_sync = time.time()
sync_result = websocket_manager._serialize_message_safely(large_agent_state)
end_sync = time.time()
sync_duration = end_sync - start_sync

                # Test async serialization
start_async = time.time()
async_result = await websocket_manager._serialize_message_safely_async(large_agent_state)
end_async = time.time()
async_duration = end_async - start_async

                # Both should produce the same result
assert sync_result == async_result

                # Async might be slightly slower due to overhead, but not significantly
                # Both should complete within reasonable time
assert sync_duration < 10.0, "formatted_string
assert async_duration < 10.0, formatted_string"

@pytest.mark.asyncio
    async def test_concurrent_async_serialization_performance(self, websocket_manager, large_agent_state):
        "Test performance with concurrent async serializations.""

                    # Create multiple variations of the large state
states = []
for i in range(10):
    state = large_agent_state.copy_with_updates( )
run_id=formatted_string",
step_count=1000 + i
                        
states.append(state)

                        # Serialize all concurrently
start_time = time.time()
tasks = [
websocket_manager._serialize_message_safely_async(state)
for state in states
                        
results = await asyncio.gather(*tasks)
end_time = time.time()

                        # Should be faster than serializing sequentially
duration = end_time - start_time
assert duration < 15.0, "formatted_string

                        # All should succeed
assert len(results) == 10

                        # Verify each result
for i, result in enumerate(results):
    json_str = json.dumps(result)
deserialized = json.loads(json_str)
assert deserialized[run_id"] == "formatted_string
assert deserialized[step_count"] == 1000 + i

@pytest.mark.asyncio
    async def test_serialization_timeout_handling(self, websocket_manager):
        "Test timeout handling in async serialization.""

                                # Mock the sync serialization to simulate slow operation
with patch.object(websocket_manager, '_serialize_message_safely') as mock_sync:
    async def slow_serialize(msg):
        time.sleep(7)  # Longer than 5-second timeout
await asyncio.sleep(0)
return {result": "slow}

mock_sync.side_effect = slow_serialize

    # Should timeout and return fallback
start_time = time.time()
result = await websocket_manager._serialize_message_safely_async({test": "data}
end_time = time.time()

    # Should timeout around 5 seconds (with some tolerance)
duration = end_time - start_time
assert 4.5 <= duration <= 6.0, formatted_string"

    # Should return timeout fallback
assert "serialization_error in result
assert timed out" in result["serialization_error]

    # Verify timeout stats are incremented
assert websocket_manager.connection_stats[send_timeouts"] > 0

@pytest.mark.asyncio
    async def test_memory_usage_during_serialization(self, websocket_manager, large_agent_state):
        "Test memory usage doesn't grow excessively during serialization.""

import psutil
import os

        # Get initial memory usage
process = psutil.Process(os.getpid())
initial_memory = process.memory_info().rss

        # Perform multiple serializations
for i in range(5):
            # Create a variation to prevent caching
state = large_agent_state.copy_with_updates(run_id=formatted_string")

            # Serialize both sync and async
sync_result = websocket_manager._serialize_message_safely(state)
async_result = await websocket_manager._serialize_message_safely_async(state)

            # Convert to JSON to simulate real usage
json.dumps(sync_result)
json.dumps(async_result)

            # Get final memory usage
final_memory = process.memory_info().rss
memory_growth = final_memory - initial_memory

            # Memory growth should be reasonable (< 100MB for this test)
memory_growth_mb = memory_growth / (1024 * 1024)
assert memory_growth_mb < 100, "formatted_string

def test_json_dumps_performance_comparison(self, websocket_manager, large_agent_state):
    ""Test performance of different JSON serialization approaches."

    # Get serialized data
serialized_data = websocket_manager._serialize_message_safely(large_agent_state)

    # Test standard json.dumps
start_time = time.time()
standard_json = json.dumps(serialized_data)
standard_duration = time.time() - start_time

    # Test json.dumps with different options
start_time = time.time()
compact_json = json.dumps(serialized_data, separators=(',', ':'))
compact_duration = time.time() - start_time

    # Test json.dumps with ensure_ascii=False for unicode
start_time = time.time()
unicode_json = json.dumps(serialized_data, ensure_ascii=False)
unicode_duration = time.time() - start_time

    # All should complete reasonably quickly
assert standard_duration < 5.0, "formatted_string
assert compact_duration < 5.0, formatted_string"
assert unicode_duration < 5.0, "formatted_string

    # Compact should be slightly faster or similar
    # Unicode should handle special characters properly
assert len(compact_json) <= len(standard_json)  # Compact removes spaces

@pytest.mark.asyncio
    async def test_serialization_thread_pool_performance(self, websocket_manager, large_agent_state):
        ""Test thread pool execution performance for serialization."

        # Test that the thread pool executor is being used efficiently
original_executor = websocket_manager._serialization_executor

        # Monitor the thread pool usage
start_time = time.time()

        # Submit multiple async serializations
tasks = [
websocket_manager._serialize_message_safely_async( )
large_agent_state.copy_with_updates(run_id="formatted_string)
        
for i in range(5)
        

results = await asyncio.gather(*tasks)
duration = time.time() - start_time

        # Should complete efficiently using thread pool
assert duration < 20.0, formatted_string"
assert len(results) == 5

        # Verify thread pool is still functional
assert not original_executor._shutdown

def test_serialization_error_performance(self, websocket_manager):
    "Test performance when serialization errors occur.""

    # Create objects that will cause serialization errors
class ErrorProneObject:
    def model_dump(self, **kwargs):
    # Simulate slow failure
        time.sleep(0.1)
        raise ValueError(Serialization failed")

    async def to_dict(self):
        time.sleep(0.1)
        raise RuntimeError("to_dict failed)

    async def __str__(self):
        await asyncio.sleep(0)
        return ErrorProneObject"

        error_objects = [ErrorProneObject() for _ in range(10)]

    # Measure error handling performance
        start_time = time.time()
        results = []

        for obj in error_objects:
        result = websocket_manager._serialize_message_safely(obj)
        results.append(result)

        duration = time.time() - start_time

        # Error handling should be efficient (< 5 seconds for 10 errors)
        assert duration < 5.0, "formatted_string

        # All should have fallback results
        for result in results:
        assert isinstance(result, dict)
        assert serialization_error" in result
        assert "ErrorProneObject in str(result)

@pytest.mark.asyncio
    async def test_websocket_send_performance_with_serialization(self, websocket_manager, large_agent_state):
        ""Test overall WebSocket send performance including serialization."

                # Mock WebSocket for sending
mock_websocket = Magic        mock_# websocket setup complete

conn_info = {
"websocket: mock_websocket,
message_count": 0,
"last_activity: datetime.now(timezone.utc)
                

                # Test send_to_connection_with_retry performance
start_time = time.time()
result = await websocket_manager._send_to_connection_with_retry( )
perf-test-conn", mock_websocket, large_agent_state, conn_info
                
duration = time.time() - start_time

                # Should complete efficiently including serialization
assert duration < 10.0, "formatted_string
assert result is True

                # Verify the serialized message was passed to send_json
mock_websocket.send_json.assert_called_once()
sent_data = mock_websocket.send_json.call_args[0][0]

                # Should be JSON-serializable dict
assert isinstance(sent_data, dict)
json.dumps(sent_data)  # Should not raise

def test_deep_recursion_performance(self, websocket_manager):
    ""Test performance with deeply nested structures."

    # Create very deep nesting (100 levels)
async def create_deep_structure(depth):
    if depth == 0:
        await asyncio.sleep(0)
return {"value: leaf", "depth: 0}
return {
level": depth,
"child: create_deep_structure(depth - 1),
metadata": {"depth: depth, timestamp": time.time()}
        

deep_message = {
"type: deep_structure",
"payload: create_deep_structure(100)
        

        # Should handle deep structures efficiently
start_time = time.time()
result = websocket_manager._serialize_message_safely(deep_message)
duration = time.time() - start_time

        # Should not cause stack overflow or excessive delay
assert duration < 5.0, formatted_string"

        # Should serialize successfully
json_str = json.dumps(result)
deserialized = json.loads(json_str)
assert deserialized["type] == deep_structure"

@pytest.mark.asyncio
    async def test_high_frequency_serialization(self, websocket_manager):
        "Test performance under high-frequency serialization load.""

            # Simulate high-frequency WebSocket messages (like during agent execution)
messages = []
for i in range(100):
    msg = {
type": "agent_update,
payload": {
"run_id: formatted_string",
"step: i,
progress": i / 100,
"message: formatted_string",
"timestamp: time.time()
                
                
messages.append(msg)

                # Serialize all messages rapidly
start_time = time.time()

                # Use both sync and async serialization
sync_results = []
for msg in messages[:50]:
    result = websocket_manager._serialize_message_safely(msg)
sync_results.append(result)

async_tasks = [
websocket_manager._serialize_message_safely_async(msg)
for msg in messages[50:]
                    
async_results = await asyncio.gather(*async_tasks)

duration = time.time() - start_time

                    # Should handle high frequency efficiently
assert duration < 10.0, formatted_string"

                    # All should succeed
assert len(sync_results) == 50
assert len(async_results) == 50

                    # Verify accuracy
for i, result in enumerate(sync_results):
    assert result["payload][step"] == i

for i, result in enumerate(async_results, 50):
    assert result["payload][step"] == i
