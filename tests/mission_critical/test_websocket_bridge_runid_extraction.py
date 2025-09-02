#!/usr/bin/env python
"""MISSION CRITICAL: WebSocket Bridge Run ID to Thread ID Extraction Tests

CRITICAL BUSINESS CONTEXT:
- Run_id to thread_id extraction is ESSENTIAL for proper WebSocket routing
- If this fails, WebSocket events go to the wrong chat threads
- This directly impacts 90% of chat functionality and user experience

This test specifically validates:
1. Run_id to thread_id extraction patterns
2. Fallback extraction methods
3. Edge cases and error handling
4. Pattern matching for various run_id formats

THESE TESTS MUST BE COMPREHENSIVE AND CATCH ANY REGRESSION.
"""

import asyncio
import os
import sys
import uuid
from typing import Optional
from unittest.mock import AsyncMock, MagicMock, patch

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import pytest

# Set up isolated test environment
os.environ['WEBSOCKET_TEST_ISOLATED'] = 'true'
os.environ['SKIP_REAL_SERVICES'] = 'true'
os.environ['TEST_COLLECTION_MODE'] = '1'

# Import the WebSocket bridge
from netra_backend.app.services.agent_websocket_bridge import AgentWebSocketBridge


class MockWebSocketManager:
    """Mock WebSocket manager for testing."""
    
    def __init__(self):
        self.sent_messages = []
    
    async def send_to_thread(self, thread_id: str, message: dict) -> bool:
        self.sent_messages.append((thread_id, message))
        return True


class MockOrchestrator:
    """Mock orchestrator for testing thread_id resolution."""
    
    def __init__(self):
        self.thread_mapping = {}
    
    def set_thread_mapping(self, run_id: str, thread_id: str):
        """Set a mapping for testing."""
        self.thread_mapping[run_id] = thread_id
    
    async def get_thread_id_for_run(self, run_id: str) -> Optional[str]:
        """Mock implementation for testing."""
        return self.thread_mapping.get(run_id)


@pytest.fixture
def mock_websocket_manager():
    """Mock WebSocket manager fixture."""
    return MockWebSocketManager()


@pytest.fixture
def mock_orchestrator():
    """Mock orchestrator fixture."""
    return MockOrchestrator()


@pytest.fixture
async def websocket_bridge(mock_websocket_manager, mock_orchestrator):
    """WebSocket bridge with mocked dependencies."""
    with patch.multiple(
        'netra_backend.app.services.agent_websocket_bridge',
        get_websocket_manager=MagicMock(return_value=mock_websocket_manager),
        get_agent_execution_registry=MagicMock(return_value=mock_orchestrator)
    ):
        bridge = AgentWebSocketBridge()
        await bridge.ensure_integration()
        yield bridge


class TestWebSocketBridgeRunIdExtraction:
    """Test run_id to thread_id extraction logic."""
    
    @pytest.mark.asyncio
    async def test_direct_thread_id_patterns(self, websocket_bridge):
        """Test extraction when run_id IS a thread_id."""
        
        test_cases = [
            ("thread_12345", "thread_12345"),
            ("thread_abc123", "thread_abc123"), 
            ("thread_user_session_789", "thread_user_session_789"),
        ]
        
        for run_id, expected in test_cases:
            result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
            assert result == expected, f"Expected '{expected}' for run_id '{run_id}', got '{result}'"
        
        print("✅ Direct thread_id patterns: PASSED")

    @pytest.mark.asyncio
    async def test_embedded_thread_id_patterns(self, websocket_bridge):
        """Test extraction when thread_id is embedded in run_id."""
        
        test_cases = [
            ("run_thread_12345", "thread_12345"),
            ("user_123_thread_456_session", "thread_456"),
            ("agent_execution_thread_789_v1", "thread_789"),
            ("prefix_thread_abc123_suffix", "thread_abc123"),
        ]
        
        for run_id, expected in test_cases:
            result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
            assert result == expected, f"Expected '{expected}' for run_id '{run_id}', got '{result}'"
        
        print("✅ Embedded thread_id patterns: PASSED")

    @pytest.mark.asyncio
    async def test_orchestrator_resolution(self, websocket_bridge, mock_orchestrator):
        """Test resolution via orchestrator when available."""
        
        # Set up orchestrator mapping
        run_id = "custom_run_12345"
        expected_thread_id = "thread_orchestrator_resolved"
        mock_orchestrator.set_thread_mapping(run_id, expected_thread_id)
        
        result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
        assert result == expected_thread_id, f"Expected orchestrator resolution to return '{expected_thread_id}', got '{result}'"
        
        print("✅ Orchestrator resolution: PASSED")

    @pytest.mark.asyncio
    async def test_fallback_patterns_when_no_orchestrator(self, websocket_bridge):
        """Test fallback extraction when orchestrator fails."""
        
        # Clear orchestrator to test fallback
        websocket_bridge._orchestrator = None
        
        test_cases = [
            ("something_thread_fallback", "thread_fallback"),
            ("thread_direct", "thread_direct"),
            ("no_thread_pattern", None),
        ]
        
        for run_id, expected in test_cases:
            result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
            if expected:
                assert result == expected, f"Expected fallback '{expected}' for run_id '{run_id}', got '{result}'"
            else:
                assert result is None, f"Expected None for run_id '{run_id}', got '{result}'"
        
        print("✅ Fallback patterns when no orchestrator: PASSED")

    @pytest.mark.asyncio
    async def test_edge_cases_and_error_handling(self, websocket_bridge):
        """Test edge cases and error handling."""
        
        test_cases = [
            ("", None),  # Empty string
            (None, None),  # None input (should not crash)
            ("thread_", None),  # Incomplete pattern
            ("_thread_123", "thread_123"),  # Leading underscore
            ("thread_123_thread_456", "thread_123"),  # Multiple patterns (should take first)
            ("THREAD_UPPERCASE", None),  # Case sensitivity
        ]
        
        for run_id, expected in test_cases:
            try:
                result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
                if expected:
                    assert result == expected, f"Expected '{expected}' for run_id '{run_id}', got '{result}'"
                else:
                    assert result is None, f"Expected None for run_id '{run_id}', got '{result}'"
            except Exception as e:
                # Should handle errors gracefully
                if run_id is None:
                    # None input might raise an exception, which is acceptable
                    assert "NoneType" in str(e) or "string" in str(e), f"Unexpected error for None input: {e}"
                else:
                    pytest.fail(f"Unexpected exception for run_id '{run_id}': {e}")
        
        print("✅ Edge cases and error handling: PASSED")

    @pytest.mark.asyncio
    async def test_complex_real_world_patterns(self, websocket_bridge):
        """Test complex real-world run_id patterns."""
        
        test_cases = [
            # Real patterns we might see in production
            ("user_12345_session_67890_thread_abc123_run_001", "thread_abc123"),
            ("api_v1_request_uuid4_thread_session_456", "thread_session"),
            ("agent_supervisor_thread_chat_789_execution_2", "thread_chat"),
            ("websocket_connection_thread_live_123_message_456", "thread_live"),
            ("batch_process_thread_background_999", "thread_background"),
        ]
        
        for run_id, expected in test_cases:
            result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
            assert result == expected, f"Expected '{expected}' for run_id '{run_id}', got '{result}'"
        
        print("✅ Complex real-world patterns: PASSED")

    @pytest.mark.asyncio
    async def test_performance_with_many_extractions(self, websocket_bridge):
        """Test performance of extraction with many calls."""
        
        import time
        
        # Generate test cases
        test_run_ids = []
        for i in range(1000):
            test_run_ids.append(f"performance_test_thread_{i}_{uuid.uuid4()}")
        
        # Measure extraction performance
        start_time = time.time()
        results = []
        
        for run_id in test_run_ids:
            result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
            results.append(result)
        
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Validate results
        assert len(results) == len(test_run_ids), "Should have result for each input"
        successful_extractions = sum(1 for result in results if result is not None)
        assert successful_extractions == len(test_run_ids), f"Expected all extractions to succeed, got {successful_extractions}/{len(test_run_ids)}"
        
        # Performance assertion (should be fast)
        assert execution_time < 10.0, f"Extraction took too long: {execution_time:.2f}s for {len(test_run_ids)} operations"
        
        avg_time_per_extraction = (execution_time / len(test_run_ids)) * 1000  # Convert to milliseconds
        print(f"✅ Performance test: {len(test_run_ids)} extractions in {execution_time:.2f}s ({avg_time_per_extraction:.3f}ms per extraction)")

    @pytest.mark.asyncio
    async def test_thread_id_validation_in_websocket_events(self, websocket_bridge, mock_websocket_manager):
        """Test that extracted thread_ids are actually used in WebSocket events."""
        
        # Test event emission with various run_id patterns
        test_cases = [
            ("thread_direct_123", "thread_direct_123"),
            ("run_thread_embedded_456", "thread_embedded"),
            ("user_session_thread_test_789", "thread_test"),
        ]
        
        for run_id, expected_thread_id in test_cases:
            # Clear previous messages
            mock_websocket_manager.sent_messages.clear()
            
            # Emit a test event
            await websocket_bridge.notify_agent_started(run_id, "TestAgent", "Starting test")
            
            # Verify message was sent to correct thread
            assert len(mock_websocket_manager.sent_messages) == 1, f"Expected 1 message for run_id '{run_id}'"
            
            sent_thread_id, sent_message = mock_websocket_manager.sent_messages[0]
            assert sent_thread_id == expected_thread_id, \
                f"Message sent to wrong thread: expected '{expected_thread_id}', got '{sent_thread_id}'"
            
            # Verify message content
            assert sent_message['run_id'] == run_id, f"Message has wrong run_id: {sent_message['run_id']}"
            assert sent_message['type'] == 'agent_started', f"Message has wrong type: {sent_message['type']}"
        
        print("✅ Thread ID validation in WebSocket events: PASSED")

    @pytest.mark.asyncio
    async def test_concurrent_thread_id_extractions(self, websocket_bridge):
        """Test concurrent thread_id extractions don't interfere."""
        
        # Create concurrent extraction tasks
        async def extract_thread_id(run_id: str) -> tuple:
            result = await websocket_bridge._resolve_thread_id_from_run_id(run_id)
            return run_id, result
        
        # Generate test data
        run_ids = [f"concurrent_test_thread_{i}_{uuid.uuid4()}" for i in range(50)]
        
        # Execute concurrently
        tasks = [extract_thread_id(run_id) for run_id in run_ids]
        results = await asyncio.gather(*tasks)
        
        # Validate results
        for run_id, extracted_thread_id in results:
            # Each should extract correctly based on pattern
            expected = f"thread_{run_id.split('_')[2]}"  # Get the number part
            assert expected in extracted_thread_id, \
                f"Concurrent extraction failed for {run_id}: expected '{expected}' in '{extracted_thread_id}'"
        
        print("✅ Concurrent thread ID extractions: PASSED")


if __name__ == "__main__":
    # Run the focused test suite
    pytest.main([
        __file__,
        "-v",
        "--tb=short",
        "--asyncio-mode=auto"
    ])