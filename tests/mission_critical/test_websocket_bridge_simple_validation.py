from shared.isolated_environment import get_env
#!/usr/bin/env python
"""MISSION CRITICAL: Simple WebSocket Bridge Thread Resolution Validation

CRITICAL BUSINESS CONTEXT:
- Thread ID resolution is THE FOUNDATION of WebSocket event routing
- If this fails, 90% of chat functionality breaks - users see loading forever
- This test validates core thread resolution functionality

Simple validation tests without complex fixtures.
"""

import asyncio
import os
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set up isolated test environment
os.environ['WEBSOCKET_TEST_ISOLATED'] = 'true' 
os.environ['SKIP_REAL_SERVICES'] = 'true'
os.environ['TEST_COLLECTION_MODE'] = '1'
os.environ['SKIP_DOCKER_SETUP'] = 'true'
os.environ['LOG_LEVEL'] = 'ERROR'  # Suppress debug logs to avoid Unicode issues

import pytest
from unittest.mock import MagicMock

from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge, IntegrationState


def test_thread_resolution_patterns():
    """Test basic thread ID resolution patterns without complex setup."""
    
    # Create a bridge instance and bypass full initialization
    bridge = AgentWebSocketBridge()
    bridge._websocket_manager = MagicMock()
    bridge._orchestrator = None  # Force fallback to pattern matching
    bridge._thread_registry = None  # Force fallback to pattern matching
    bridge.state = IntegrationState.ACTIVE
    
    # Test cases for pattern-based resolution
    test_cases = [
        # Direct thread patterns (FIXED - now direct usage runs before pattern extraction)
        ("thread_12345", "thread_12345"),  # Simple case works
        ("thread_abc123", "thread_abc123"),  # Simple case works  
        ("thread_user_session_789", "thread_user_session_789"),  # FIXED: Now returns full thread_id due to correct priority
        
        # Embedded patterns (these work correctly)
        ("run_thread_67890", "thread_67890"),
        ("user_123_thread_456_session", "thread_456"),
        ("agent_execution_thread_789_v1", "thread_789"),
        ("prefix_thread_abc123_suffix", "thread_abc123"),
        
        # Edge cases
        ("thread_", None),  # FIXED: Incomplete pattern now correctly returns None due to validation
        ("thread__invalid", None),  # Double underscore - invalid format
        ("thread_123_", None),  # Trailing underscore - invalid format
        ("no_pattern_here", None),  # No pattern
        ("", None),  # Empty string
    ]
    
    async def run_test():
        for run_id, expected in test_cases:
            try:
                result = await bridge._resolve_thread_id_from_run_id(run_id)
                if expected is None:
                    assert result is None, f"Expected None for '{run_id}', got '{result}'"
                else:
                    assert result == expected, f"Expected '{expected}' for '{run_id}', got '{result}'"
                print(f"PASS Pattern test: '{run_id}' -> '{result}' (expected: '{expected}')")
            except Exception as e:
                print(f"FAIL Pattern test failed for '{run_id}': {e}")
                raise
    
    # Run the test
    asyncio.run(run_test())
    print("PASS All thread resolution pattern tests passed!")


def test_websocket_event_routing_simulation():
    """Test WebSocket event routing simulation."""
    
    class MockWebSocketManager:
        def __init__(self):
            self.sent_messages = []
        
        async def send_to_thread(self, thread_id: str, message: dict) -> bool:
            self.sent_messages.append((thread_id, message))
            return True
    
    # Setup
    mock_ws_manager = MockWebSocketManager()
    bridge = AgentWebSocketBridge()
    bridge._websocket_manager = mock_ws_manager
    bridge._orchestrator = None
    bridge._thread_registry = None
    bridge.state = IntegrationState.ACTIVE
    
    async def run_test():
        # Test successful event routing
        run_id = "test_thread_12345"
        expected_thread_id = "thread_12345"
        
        success = await bridge.notify_agent_started(run_id, "TestAgent", {"test": "data"})
        assert success, "Event should be sent successfully"
        
        # Verify routing
        assert len(mock_ws_manager.sent_messages) == 1, "Should have sent one message"
        sent_thread_id, sent_message = mock_ws_manager.sent_messages[0]
        assert sent_thread_id == expected_thread_id, f"Should route to '{expected_thread_id}', got '{sent_thread_id}'"
        assert sent_message['run_id'] == run_id, "Message should have correct run_id"
        assert sent_message['type'] == 'agent_started', "Message should have correct type"
        print(f"✅ Event routing test: {run_id} -> {sent_thread_id}")
        
        # Test failure case - unresolvable run_id
        mock_ws_manager.sent_messages.clear()
        unresolvable_run_id = "no_pattern_here"
        
        success = await bridge.notify_agent_started(unresolvable_run_id, "TestAgent")
        assert not success, "Event should fail for unresolvable run_id"
        assert len(mock_ws_manager.sent_messages) == 0, "No messages should be sent for unresolvable run_id"
        print(f"✅ Failure test: {unresolvable_run_id} correctly failed")
    
    # Run the test
    asyncio.run(run_test())
    print("✅ All WebSocket event routing tests passed!")


def test_concurrent_resolution():
    """Test concurrent thread resolution doesn't interfere."""
    
    bridge = AgentWebSocketBridge()
    bridge._websocket_manager = MagicMock()
    bridge._orchestrator = None
    bridge._thread_registry = None
    bridge.state = IntegrationState.ACTIVE
    
    async def resolve_thread(run_id: str) -> str:
        return await bridge._resolve_thread_id_from_run_id(run_id)
    
    async def run_test():
        # Create concurrent resolution tasks
        tasks = []
        expected_results = {}
        
        for i in range(50):
            run_id = f"concurrent_thread_{i}"
            expected = f"thread_{i}"
            expected_results[run_id] = expected
            tasks.append(resolve_thread(run_id))
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify results
        for i, result in enumerate(results):
            run_id = f"concurrent_thread_{i}"
            expected = expected_results[run_id]
            assert result == expected, f"Concurrent resolution failed for {run_id}: expected {expected}, got {result}"
        
        print(f"✅ Concurrent resolution test: {len(tasks)} concurrent resolutions succeeded")
    
    # Run the test
    asyncio.run(run_test())
    print("✅ All concurrent resolution tests passed!")


def test_error_handling():
    """Test error handling for edge cases."""
    
    bridge = AgentWebSocketBridge()
    bridge._websocket_manager = MagicMock()
    bridge._orchestrator = None
    bridge._thread_registry = None
    bridge.state = IntegrationState.ACTIVE
    
    # Test malformed inputs
    malformed_cases = [
        "",  # Empty string
        "   ",  # Whitespace only
        "thread_",  # Incomplete pattern
        "THREAD_UPPERCASE_123",  # Wrong case
        "multiple_thread_123_thread_456_patterns",  # Multiple patterns (should take first)
        "thread_" + "x" * 1000,  # Very long string
        "no_valid_pattern_here",  # No pattern at all
    ]
    
    async def run_test():
        for run_id in malformed_cases:
            try:
                result = await bridge._resolve_thread_id_from_run_id(run_id)
                
                # Should either return a valid result or None, never crash
                if result is not None:
                    assert isinstance(result, str), f"Result should be string or None, got {type(result)}"
                    if result.startswith("thread_"):
                        print(f"✅ Error handling test: '{run_id}' -> '{result}' (extracted)")
                    else:
                        print(f"✅ Error handling test: '{run_id}' -> '{result}' (direct)")
                else:
                    print(f"✅ Error handling test: '{run_id}' -> None (no pattern)")
                
            except Exception as e:
                print(f"❌ Error handling test failed for '{run_id}': {e}")
                raise
    
    # Run the test
    asyncio.run(run_test())
    print("✅ All error handling tests passed!")


def test_performance_basic():
    """Basic performance test."""
    
    import time
    
    bridge = AgentWebSocketBridge()
    bridge._websocket_manager = MagicMock()
    bridge._orchestrator = None
    bridge._thread_registry = None
    bridge.state = IntegrationState.ACTIVE
    
    async def run_test():
        # Generate test cases
        test_cases = [f"perf_thread_{i}" for i in range(1000)]
        
        # Measure resolution performance
        start_time = time.time()
        
        tasks = [bridge._resolve_thread_id_from_run_id(run_id) for run_id in test_cases]
        results = await asyncio.gather(*tasks)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Validate results
        for i, result in enumerate(results):
            expected = f"thread_{i}"
            assert result == expected, f"Performance test failed for case {i}: expected {expected}, got {result}"
        
        # Performance assertions
        avg_time_per_resolution = (execution_time / len(test_cases)) * 1000  # Convert to ms
        assert execution_time < 2.0, f"Performance test took too long: {execution_time:.2f}s"
        assert avg_time_per_resolution < 2.0, f"Average resolution time too slow: {avg_time_per_resolution:.2f}ms"
        
        print(f"✅ Performance test: {len(test_cases)} resolutions in {execution_time:.2f}s ({avg_time_per_resolution:.3f}ms avg)")
    
    # Run the test
    asyncio.run(run_test())
    print("✅ All performance tests passed!")


if __name__ == "__main__":
    print("Starting WebSocket Bridge Thread Resolution Validation Tests")
    print("=" * 70)
    
    try:
        # Run all tests
        test_thread_resolution_patterns()
        print()
        
        test_websocket_event_routing_simulation()
        print()
        
        test_concurrent_resolution()
        print()
        
        test_error_handling()
        print()
        
        test_performance_basic()
        print()
        
        print("=" * 70)
        print("ALL WEBSOCKET BRIDGE THREAD RESOLUTION TESTS PASSED!")
        print("Core value delivery mechanism is protected and working correctly.")
        
    except Exception as e:
        print("=" * 70)
        print(f"TEST FAILURE: {e}")
        print("CRITICAL: WebSocket bridge thread resolution is broken!")
        sys.exit(1)
